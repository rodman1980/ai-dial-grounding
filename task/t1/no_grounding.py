import asyncio
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import AzureChatOpenAI
from pydantic import SecretStr
from task._constants import DIAL_URL, API_KEY
from task.user_client import UserClient

BATCH_SYSTEM_PROMPT = """You are a user search assistant. Your task is to find users from the provided list that match the search criteria.

INSTRUCTIONS:
1. Analyze the user question to understand what attributes/characteristics are being searched for
2. Examine each user in the context and determine if they match the search criteria
3. For matching users, extract and return their complete information
4. Be inclusive - if a user partially matches or could potentially match, include them

OUTPUT FORMAT:
- If you find matching users: Return their full details exactly as provided, maintaining the original format
- If no users match: Respond with exactly "NO_MATCHES_FOUND"
- If uncertain about a match: Include the user with a note about why they might match"""

FINAL_SYSTEM_PROMPT = """You are a helpful assistant that provides comprehensive answers based on user search results.

INSTRUCTIONS:
1. Review all the search results from different user batches
2. Combine and deduplicate any matching users found across batches
3. Present the information in a clear, organized manner
4. If multiple users match, group them logically
5. If no users match, explain what was searched for and suggest alternatives"""

USER_PROMPT = """## USER DATA:
{context}

## SEARCH QUERY: 
{query}"""


class TokenTracker:
    def __init__(self):
        self.total_tokens = 0
        self.batch_tokens = []

    def add_tokens(self, tokens: int):
        self.total_tokens += tokens
        self.batch_tokens.append(tokens)

    def get_summary(self):
        return {
            'total_tokens': self.total_tokens,
            'batch_count': len(self.batch_tokens),
            'batch_tokens': self.batch_tokens
        }

# Create AzureChatOpenAI client
llm_client = AzureChatOpenAI(
    temperature=0.0,
    azure_deployment='gpt-4o',
    azure_endpoint=DIAL_URL,
    api_key=SecretStr(API_KEY),
    api_version="",
)

# Create TokenTracker
token_tracker = TokenTracker()

def join_context(context: list[dict[str, Any]]) -> str:
    # Collect user data into a readable string format
    formatted_context = []
    for user in context:
        user_info = "\n".join([f"  {key}: {value}" for key, value in user.items()])
        formatted_context.append(f"User:\n{user_info}")
    return "\n\n".join(formatted_context)


async def generate_response(system_prompt: str, user_message: str) -> str:
    print("Processing batch...")
    print(f"System Prompt: {system_prompt}")
    print(f"User Message: {user_message}")
    try:
        # Create messages array with system prompt and user message
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        print("Messages prepared for LLM:", messages)

        # Generate response
        response = await llm_client.ainvoke(messages)
        print("Raw response received from LLM:", response)

        # Get token usage from response usage_metadata
        token_usage = getattr(response, 'usage_metadata', {}).get('total_tokens', 0) if hasattr(response, 'usage_metadata') else 0
        token_tracker.add_tokens(token_usage)
        print(f"Token usage recorded: {token_usage}")

        # Print response content and token usage
        content = response.content if isinstance(response.content, str) else str(response.content)
        print(f"Batch response content: {content}")
        print(f"Tokens used in this batch: {token_usage}")

        return content
    except Exception as e:
        print(f"Error during LLM response generation: {e}")
        return "NO_MATCHES_FOUND"


async def main():
    print("Query samples:")
    print(" - Do we have someone with name John that loves traveling?")

    try:
        user_question = input("> ").strip()
        if not user_question:
            print("No query provided. Exiting.")
            return

        print("\n--- Searching user database ---")

        # Get all users
        user_client = UserClient()
        try:
            all_users = user_client.get_all_users()
        except Exception as e:
            print(f"Error fetching users from API: {e}")
            return

        if not all_users:
            print("No users found in the database.")
            return

        # Split all users into batches of 100
        user_batches = [all_users[i:i + 100] for i in range(0, len(all_users), 100)]

        # Prepare tasks for async run of response generation for user batches
        tasks = []
        for batch in user_batches:
            context = join_context(batch)
            user_prompt = USER_PROMPT.format(context=context, query=user_question)
            tasks.append(generate_response(BATCH_SYSTEM_PROMPT, user_prompt))

        # Run tasks asynchronously
        results = await asyncio.gather(*tasks)

        # Filter results on 'NO_MATCHES_FOUND'
        filtered_results = [result for result in results if result != "NO_MATCHES_FOUND"]

        if filtered_results:
            # Combine filtered results
            combined_results = "\n\n".join(filtered_results)

            # Generate final response
            final_prompt = FINAL_SYSTEM_PROMPT
            final_user_prompt = USER_PROMPT.format(context=combined_results, query=user_question)
            final_response = await generate_response(final_prompt, final_user_prompt)

            print("\nFinal Response:")
            print(final_response)
        else:
            print("No users found matching the query.")

        # Print token usage summary
        print("\nToken Usage Summary:")
        print(token_tracker.get_summary())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {e}")