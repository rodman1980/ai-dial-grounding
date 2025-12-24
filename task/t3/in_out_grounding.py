"""
Execution Map (quick):
- Initialize embeddings and LLM client
- Load or build Chroma vectorstore containing compact `user_id`+`about` docs
- For each query: update vectorstore diffs, run similarity search, ask LLM
    to extract hobbies -> user_id lists, then fetch full user records
- Return grouped users by hobby (output grounding step verifies IDs)

Flow notes:
- External I/O: User service (`UserClient`) and Chroma persisted store.
- Error paths: LLM parsing fallbacks to JSON parse; user fetch ignores missing ids.
"""

import asyncio
import time
from typing import Any, Dict, List

from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from langchain_chroma import Chroma
from pydantic import SecretStr

from task.user_client import UserClient
from task._constants import DIAL_URL, API_KEY


class ExtractionModel(BaseModel):
        """Pydantic model for LLM extraction output.

        The LLM is expected to return JSON matching this shape:
            {"matches": {"hobby": [user_id_ints]}}

        We keep `user_id` as ints here because the downstream user service
        client expects numeric ids. Parsing/validation happens via Pydantic.
        """
        matches: Dict[str, List[int]]


def format_user_document(user: dict[str, Any]) -> str:
    """Create a compact text document for embeddings.

    We intentionally include only `user_id` and a short `about` field to
    reduce embedding token usage and to minimize PII exposure in LLM prompts.
    """
    # Keep minimal text to reduce embedding costs and exposure
    about = user.get("about", "") or user.get("about_me", "") or ""
    return f"user_id: {user.get('id')}\nabout: {about}\n"


class InOutRAG:
    def __init__(self, embeddings: AzureOpenAIEmbeddings, llm_client: AzureChatOpenAI, persist_dir: str = "data/vectorstores/t3"):
        self.embeddings = embeddings
        self.llm_client = llm_client
        self.persist_dir = persist_dir
        self.vectorstore = None

    async def __aenter__(self):
        print("🔎 Initializing In-Out RAG (Chroma)...")
        start = time.time()
        # Load or create vectorstore (run blocking IO in thread)
        self.vectorstore = await asyncio.to_thread(self._load_or_create_vectorstore)
        print(f"   ✓ Vectorstore ready ({time.time() - start:.2f}s)")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # persisted by Chroma automatically via .persist(); nothing to do
        pass

    def _load_or_create_vectorstore(self):
        try:
            chroma = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)
            # If collection empty, create from users
            # Use the collection count to determine if we need a cold start.
            if not chroma._collection.count():
                raise RuntimeError("empty")
            return chroma
        except Exception:
            # Build from users
            user_client = UserClient()
            users = user_client.get_all_users()
            documents = [Document(page_content=format_user_document(u), metadata={"user_id": u.get("id")}) for u in users]
            chroma = Chroma(persist_directory=self.persist_dir, embedding_function=self.embeddings)
            chroma.add_documents(documents)
            # Different versions of the Chroma/langchain wrapper expose
            # persistence differently. Call `.persist()` when available,
            # otherwise ignore (some implementations persist automatically).
            try:
                chroma.persist()
            except AttributeError:
                try:
                    # lower-level client may provide persist
                    chroma._client.persist()
                except Exception:
                    # best-effort: if persistence is not supported, continue
                    pass
            return chroma

    async def _update_vectorstore_with_diffs(self):
        # Fetch latest users in thread
        user_client = UserClient()
        users = await asyncio.to_thread(user_client.get_all_users)
        current_ids = {u.get("id") for u in users}

        # Get ids in vectorstore
        # Chroma stores ids as strings; normalize both sides to sets of strings
        vs_ids = set(self.vectorstore._collection.get()['ids'])

        # Normalize types: vectorstore ids -> str, current ids -> str
        current_ids_str = set(map(str, current_ids))

        to_delete = vs_ids - current_ids_str
        to_add = current_ids_str - vs_ids

        if to_delete:
            self.vectorstore.delete(ids=list(to_delete))

        if to_add:
            # Convert back to original users by comparing stringified ids
            add_docs = [Document(page_content=format_user_document(u), metadata={"user_id": u.get("id")}) for u in users if str(u.get("id")) in to_add]
            self.vectorstore.add_documents(add_docs)

        # Persist changes if the API exposes a persist method. Be tolerant
        # to different library versions.
        try:
            self.vectorstore.persist()
        except AttributeError:
            try:
                self.vectorstore._client.persist()
            except Exception:
                pass

    async def retrieve_context(self, query: str, k: int = 50, score: float = 0.1) -> List[Document]:
        # Keep the vectorstore in sync before search
        await self._update_vectorstore_with_diffs()

        results = self.vectorstore.similarity_search(query, k=k)
        # Chroma may not return scores depending on version; wrap as Documents
        return results

    async def perform_entity_extraction(self, docs: List[Document]) -> Dict[str, List[int]]:
        # Build compact prompt for LLM
        texts = "\n\n".join([d.page_content for d in docs])
        # Instruct LLM to return a strict JSON structure mapping hobby -> [user_ids]
        prompt = f"Given the following user snippets with user_id, extract hobbies and map them to user ids in JSON as { '{"matches": {"hobby": [ids]}}' }:\n\n{texts}\n\nReturn only valid JSON matching schema."

        messages = [
            {"role": "system", "content": "Extract hobbies and return strict JSON matching the schema {matches: {hobby: [user_ids]}}."},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_client.invoke(messages)
        parser = PydanticOutputParser(pydantic_object=ExtractionModel)
        try:
            # Prefer validated pydantic parsing to ensure ids are ints
            parsed = parser.parse(response.content)
            return parsed.matches
        except Exception:
            # If parser fails, try to load as JSON
            import json

            try:
                data = json.loads(response.content)
                return data.get("matches", {})
            except Exception:
                return {}

    async def output_grounding_and_fetch_users(self, extraction: Dict[str, List[int]]) -> Dict[str, List[dict]]:
        user_client = UserClient()
        result: Dict[str, List[dict]] = {}
        for hobby, ids in extraction.items():
            users = []
            for uid in ids:
                try:
                    # Ensure uid is passed with the expected type (int or str)
                    uid_int = int(uid)
                    # `UserClient.get_user` may be async or sync depending on implementation.
                    # If it's an async function, await it directly; otherwise run it in a thread.
                    if asyncio.iscoroutinefunction(user_client.get_user):
                        user = await user_client.get_user(uid_int)
                    else:
                        user = await asyncio.to_thread(user_client.get_user, uid_int)
                    users.append(user)
                except Exception:
                    continue
            result[hobby] = users
        return result


async def main():
    print("\n" + "=" * 80)
    print("🚀 Input-Output Grounding (Chroma)")
    print("=" * 80)

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-3-small-1",
        azure_endpoint=DIAL_URL,
        api_key=SecretStr(API_KEY),
        api_version="",
        model="text-embedding-3-small-1",
        dimensions=384,
    )

    llm_client = AzureChatOpenAI(
        temperature=0.0,
        azure_deployment='gpt-4o',
        azure_endpoint=DIAL_URL,
        api_key=SecretStr(API_KEY),
        api_version="",
    )

    async with InOutRAG(embeddings, llm_client) as rag:
        print("Ready. Type 'quit' to exit.")
        while True:
            q = input('> ').strip()
            if q.lower() in ("quit", "exit"):
                break
            docs = await rag.retrieve_context(q)
            extraction = await rag.perform_entity_extraction(docs)
            grounded = await rag.output_grounding_and_fetch_users(extraction)
            print("Result:", grounded)


if __name__ == '__main__':
    asyncio.run(main())


#TODO: Info about app:
# HOBBIES SEARCHING WIZARD
# Searches users by hobbies and provides their full info in JSON format:
#   Input: `I need people who love to go to mountains`
#   Output:
#     ```json
#       "rock climbing": [{full user info JSON},...],
#       "hiking": [{full user info JSON},...],
#       "camping": [{full user info JSON},...]
#     ```
# ---
# 1. Since we are searching hobbies that persist in `about_me` section - we need to embed only user `id` and `about_me`!
#    It will allow us to reduce context window significantly.
# 2. Pay attention that every 5 minutes in User Service will be added new users and some will be deleted. We will at the
#    'cold start' add all users for current moment to vectorstor and with each user request we will update vectorstor on
#    the retrieval step, we will remove deleted users and add new - it will also resolve the issue with consistency
#    within this 2 services and will reduce costs (we don't need on each user request load vectorstor from scratch and pay for it).
# 3. We ask LLM make NEE (Named Entity Extraction) https://cloud.google.com/discover/what-is-entity-extraction?hl=en
#    and provide response in format:
#    {
#       "{hobby}": [{user_id}, 2, 4, 100...]
#    }
#    It allows us to save significant money on generation, reduce time on generation and eliminate possible
#    hallucinations (corrupted personal info or removed some parts of PII (Personal Identifiable Information)). After
#    generation we also need to make output grounding (fetch full info about user and in the same time check that all
#    presented IDs are correct).
# 4. In response we expect JSON with grouped users by their hobbies.
# ---
# This sample is based on the real solution where one Service provides our Wizard with user request, we fetch all
# required data and then returned back to 1st Service response in JSON format.
# ---
# Useful links:
# Chroma DB: https://docs.langchain.com/oss/python/integrations/vectorstores/index#chroma
# Document#id: https://docs.langchain.com/oss/python/langchain/knowledge-base#1-documents-and-document-loaders
# Chroma DB, async add documents: https://api.python.langchain.com/en/latest/vectorstores/langchain_chroma.vectorstores.Chroma.html#langchain_chroma.vectorstores.Chroma.aadd_documents
# Chroma DB, get all records: https://api.python.langchain.com/en/latest/vectorstores/langchain_chroma.vectorstores.Chroma.html#langchain_chroma.vectorstores.Chroma.get
# Chroma DB, delete records: https://api.python.langchain.com/en/latest/vectorstores/langchain_chroma.vectorstores.Chroma.html#langchain_chroma.vectorstores.Chroma.delete
# ---
# TASK:
# Implement such application as described on the `flow.png` with adaptive vector based grounding and 'lite' version of
# output grounding (verification that such user exist and fetch full user info)



