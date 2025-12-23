import asyncio
import time
from typing import Any
from langchain_community.vectorstores import FAISS
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from pydantic import SecretStr
from task._constants import DIAL_URL, API_KEY
from task.user_client import UserClient

# Before implementation, open the `vector_based_grounding.png` to see the flow of the app.

# Provide System prompt. Goal is to explain LLM that in the user message will be provided RAG context that is retrieved
# based on user question, and LLM needs to answer to user based on provided context
SYSTEM_PROMPT = """
You are a helpful assistant that answers user questions based strictly on the provided user data context.

INSTRUCTIONS:
1. Carefully read the user data context and the search query provided.
2. Use only the information from the context to answer the user's question.
3. If the answer cannot be found in the context, respond with "NO_MATCHES_FOUND".
4. Do not use any external knowledge or assumptions.
"""

# Should consist of retrieved context and user question
USER_PROMPT = """
## USER DATA:
{context}

## SEARCH QUERY:
{query}
"""


def format_user_document(user: dict[str, Any]) -> str:
    # Prepare context from user JSON as in `join_context` from no_grounding.py
    user_info = "\n".join([f"  {key}: {value}" for key, value in user.items()])
    return f"User:\n{user_info}"


class UserRAG:
    def __init__(self, embeddings: AzureOpenAIEmbeddings, llm_client: AzureChatOpenAI):
        self.llm_client = llm_client
        self.embeddings = embeddings
        self.vectorstore = None

    async def __aenter__(self):
        print("🔎 Loading all users...")
        start_time = time.time()
        
        # 1. Get all users (use UserClient)
        user_client = UserClient()
        users = user_client.get_all_users()
        print(f"   ✓ Fetched {len(users)} users ({time.time() - start_time:.2f}s)")

        # 2. Prepare array of Documents where page_content is `format_user_document(user)`
        print("📄 Preparing documents...")
        doc_start = time.time()
        documents = [Document(page_content=format_user_document(user)) for user in users]
        print(f"   ✓ Created {len(documents)} documents ({time.time() - doc_start:.2f}s)")

        # 3. Call `_create_vectorstore_with_batching` and set it as `vectorstore`
        print("🔧 Building vectorstore...")
        vs_start = time.time()
        self.vectorstore = await self._create_vectorstore_with_batching(documents)
        print(f"   ✓ Vectorstore ready ({time.time() - vs_start:.2f}s)")

        print(f"\n✅ Initialization complete! Total time: {time.time() - start_time:.2f}s\n")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def _create_vectorstore_with_batching(self, documents: list[Document], batch_size: int = 100):
        start_time = time.time()
        
        # 1. Split all `documents` into batches
        batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]
        print(f"   → Processing {len(documents)} documents in {len(batches)} batches...")

        # 2. Create tasks to generate FAISS vector stores from document batches
        tasks = [FAISS.afrom_documents(batch, self.embeddings) for batch in batches]

        # 3. Gather tasks with asyncio
        embed_start = time.time()
        vectorstores = await asyncio.gather(*tasks)
        print(f"   → Embedded all batches ({time.time() - embed_start:.2f}s)")

        # 4. Merge all vector stores into a final vectorstore
        merge_start = time.time()
        final_vectorstore = vectorstores[0]
        for idx, vectorstore in enumerate(vectorstores[1:], 1):
            final_vectorstore.merge_from(vectorstore)
        if len(vectorstores) > 1:
            print(f"   → Merged {len(vectorstores)} vectorstores ({time.time() - merge_start:.2f}s)")

        # 5. Return the final vectorstore
        return final_vectorstore

    async def retrieve_context(self, query: str, k: int = 10, score: float = 0.1) -> str:
        print(f"\n🔍 Searching for relevant users...")
        start_time = time.time()
        
        # 1. Perform similarity search
        results = self.vectorstore.similarity_search_with_relevance_scores(query, k=k)
        print(f"   → Found {len(results)} potential matches ({time.time() - start_time:.2f}s)")

        # 2. Create `context_parts` to collect content
        context_parts = []

        # 3. Iterate through retrieved relevant docs
        for idx, (doc, relevance_score) in enumerate(results, 1):
            if relevance_score >= score:
                context_parts.append(doc.page_content)
                print(f"   ✓ Match {len(context_parts)}: Relevance score = {relevance_score:.4f}")

        if context_parts:
            print(f"\n📋 Using {len(context_parts)} relevant user(s) for context")
        else:
            print(f"\n⚠️  No matches found above threshold ({score})")
        
        # 4. Return joined context with `\n\n` as separator
        return "\n\n".join(context_parts)

    def augment_prompt(self, query: str, context: str) -> str:
        # Use the USER_PROMPT template and format it with the query and context
        USER_PROMPT = """
        Given the following context:
        {context}

        Answer the following question:
        {query}
        """
        return USER_PROMPT.format(context=context, query=query)

    def generate_answer(self, augmented_prompt: str) -> str:
        print("\n🤖 Generating answer from AI...")
        start_time = time.time()
        
        # 1. Create messages array with system and user prompts
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": augmented_prompt}
        ]

        # 2. Generate response using the LLM client
        response = self.llm_client.invoke(messages)
        print(f"   ✓ Response generated ({time.time() - start_time:.2f}s)\n")

        # 3. Return the response content
        return response.content


async def main():
    print("\n" + "=" * 80)
    print("🚀 Vector-Based RAG System")
    print("=" * 80)
    
    # 1. Create AzureOpenAIEmbeddings (match llm_client config)
    print("\n⚙️  Initializing AI components...")
    embeddings = AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-3-small-1",
        azure_endpoint=DIAL_URL,
        api_key=SecretStr(API_KEY),
        api_version="",
        model="text-embedding-3-small-1",
        dimensions=384,
    )
    print("   ✓ Embeddings model ready (text-embedding-3-small-1)")

    # 2. Create AzureChatOpenAI
    llm_client = AzureChatOpenAI(
        temperature=0.0,
        azure_deployment='gpt-4o',
        azure_endpoint=DIAL_URL,
        api_key=SecretStr(API_KEY),
        api_version="",
    )
    print("   ✓ Chat model ready\n")

    async with UserRAG(embeddings, llm_client) as rag:
        print("=" * 80)
        print("💬 Ready for queries! Type 'quit' or 'exit' to stop.")
        print("\nQuery samples:")
        print(" • I need user emails that filled with hiking and psychology")
        print(" • Who is John?")
        print("=" * 80)
        
        query_count = 0
        while True:
            user_question = input("\n> ").strip()
            if user_question.lower() in ['quit', 'exit']:
                print(f"\n👋 Goodbye! Processed {query_count} queries.\n")
                break

            if not user_question:
                continue
                
            query_count += 1
            print(f"\n{'─'*80}")
            print(f"Query #{query_count}: {user_question}")
            print(f"{'─'*80}")
            total_start = time.time()

            # 1. Retrieve context
            context = await rag.retrieve_context(user_question)

            # 2. Make augmentation
            augmented_prompt = rag.augment_prompt(user_question, context)

            # 3. Generate answer and print it
            answer = rag.generate_answer(augmented_prompt)
            
            print(f"{'─'*80}")
            print(f"📝 Answer:")
            print(f"{'─'*80}")
            print(f"\n{answer}\n")
            print(f"⏱️  Total time: {time.time() - total_start:.2f}s")
            print(f"{'='*80}")


asyncio.run(main())

# The problems with Vector based Grounding approach are:
#   - In current solution we fetched all users once, prepared Vector store (Embed takes money) but we didn't play
#     around the point that new users added and deleted every 5 minutes. (Actually, it can be fixed, we can create once
#     Vector store and with new request we will fetch all the users, compare new and deleted with version in Vector
#     store and delete the data about deleted users and add new users).
#   - Limit with top_k (we can set up to 100, but what if the real number of similarity search 100+?)
#   - With some requests works not so perfectly. (Here we can play and add extra chain with LLM that will refactor the
#     user question in a way that will help for Vector search, but it is also not okay in the point that we have
#     changed original user question).
#   - Need to play with balance between top_k and score_threshold
# Benefits are:
#   - Similarity search by context
#   - Any input can be used for search
#   - Costs reduce