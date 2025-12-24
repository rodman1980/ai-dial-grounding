"""Local test runner for InOutRAG without external Azure credentials.

This test uses:
- A very small fake embeddings implementation that returns zero vectors.
- A fake LLM client that returns a deterministic JSON mapping.

Purpose: validate vectorstore build/update/lookup and output grounding logic
against the local mock user service without contacting Azure.
"""
import asyncio
from typing import List

from langchain_core.documents import Document
from pydantic import SecretStr

from task.t3.in_out_grounding import InOutRAG, format_user_document
from task.user_client import UserClient


class FakeEmbeddings:
    """Minimal embeddings shim matching the interface used by Chroma.

    Chroma expects a callable that maps texts -> vector list. We provide a
    function that returns a short fixed-size vector for each input string.
    """

    def __call__(self, texts: List[str]):
        # return a list of identical vectors (small dim) for deterministic behavior
        return [[0.0] * 8 for _ in texts]


class FakeLLMClient:
    """Fake LLM that ignores messages and returns a static JSON string.

    It mimics the `.invoke(messages)` API used in the main code and returns
    an object with a `content` attribute containing JSON.
    """

    class Resp:
        def __init__(self, content: str):
            self.content = content

    def invoke(self, messages):
        # For testing, return a mapping of a hobby to the first three user ids
        user_client = UserClient()
        users = user_client.get_all_users()
        ids = [u.get("id") for u in users][:3]
        # Build a small JSON structure
        import json

        matches = {"hiking": ids}
        return FakeLLMClient.Resp(json.dumps({"matches": matches}))


async def run_test():
    embeddings = FakeEmbeddings()
    llm = FakeLLMClient()

    async with InOutRAG(embeddings, llm, persist_dir="data/vectorstores/t3_test") as rag:
        # run a retrieval for a sample query
        docs = await rag.retrieve_context("mountains", k=10)
        print("Retrieved docs count:", len(docs))

        extraction = await rag.perform_entity_extraction(docs)
        print("Extraction:", extraction)

        grounded = await rag.output_grounding_and_fetch_users(extraction)
        print("Grounded result keys:", list(grounded.keys()))
        for hobby, users in grounded.items():
            print(hobby, len(users))


if __name__ == "__main__":
    asyncio.run(run_test())
