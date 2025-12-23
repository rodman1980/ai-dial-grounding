import asyncio
from enum import StrEnum
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import SystemMessagePromptTemplate, ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, SecretStr, Field
from task._constants import DIAL_URL, API_KEY
from task.user_client import UserClient

# Initialize AzureChatOpenAI client
llm_client = AzureChatOpenAI(
    temperature=0.0,
    azure_deployment='gpt-4o',
    azure_endpoint=DIAL_URL,
    api_key=SecretStr(API_KEY),
    api_version="",
)

# Initialize UserClient
user_client = UserClient()

QUERY_ANALYSIS_PROMPT = """You are a query analysis system that extracts search parameters from user questions about users.

## Available Search Fields:
- **name**: User's first name (e.g., "John", "Mary")
- **surname**: User's last name (e.g., "Smith", "Johnson") 
- **email**: User's email address (e.g., "john@example.com")

## Instructions:
1. Analyze the user's question and identify what they're looking for
2. Extract specific search values mentioned in the query
3. Map them to the appropriate search fields
4. If multiple search criteria are mentioned, include all of them
5. Only extract explicit values - don't infer or assume values not mentioned

## Examples:
- "Who is John?" → name: "John"
- "Find users with surname Smith" → surname: "Smith" 
- "Look for john@example.com" → email: "john@example.com"
- "Find John Smith" → name: "John", surname: "Smith"
- "I need user emails that filled with hiking" → No clear search parameters (return empty list)

## Response Format:
{format_instructions}
"""

SYSTEM_PROMPT = """You are a RAG-powered assistant that assists users with their questions about user information.
            
## Structure of User message:
`RAG CONTEXT` - Retrieved documents relevant to the query.
`USER QUESTION` - The user's actual question.

## Instructions:
- Use information from `RAG CONTEXT` as context when answering the `USER QUESTION`.
- Cite specific sources when using information from the context.
- Answer ONLY based on conversation history and RAG context.
- If no relevant information exists in `RAG CONTEXT` or conversation history, state that you cannot answer the question.
- Be conversational and helpful in your responses.
- When presenting user information, format it clearly and include relevant details.
"""

USER_PROMPT = """## RAG CONTEXT:
{context}

## USER QUESTION: 
{query}"""


class SearchField(StrEnum):
    name = "name"
    surname = "surname"
    email = "email"

    def _generate_next_value_(name, start, count, last_values):
        return name


class SearchRequest(BaseModel):
    search_field: SearchField = Field(..., description="Field to search by (name, surname, email)")
    search_value: str = Field(..., description="Value to search for")


class SearchRequests(BaseModel):
    search_request_parameters: list[SearchRequest] = Field(default_factory=list)


#TODO:
# Before implementation open the `api_based_grounding.png` to see the flow of app


#TODO:
# Now we need to create pydentic models that will be user for search and their JSON schema will be passed to LLM by
# langchain. In response from LLM we expect to get response in such format (JSON by JSON Schema)
# 1. SearchField class, extend StrEnum and has constants: name, surname, email
# 2. Create SearchRequest, extends pydentic BaseModel and has such fields:
#       - search_field (enum from above), also you can provide its `description` that will be provided with JSON Schema
#         to LLM that model will be better understand what you expect there
#       - search_value, its string, sample what we expect here is some name, surname or email to make search
# 3. Create SearchRequests, extends pydentic BaseModel and has such fields:
#       - search_request_parameters, list of SearchRequest, by default empty list


def retrieve_context(user_question: str) -> list[dict[str, Any]]:
    """Extract search parameters from user query and retrieve matching users."""
    print(f"User question: {user_question}")

    # Create PydanticOutputParser
    parser = PydanticOutputParser(pydantic_object=SearchRequests)

    # Generate format instructions explicitly
    format_instructions = parser.get_format_instructions()
    print(f"Format instructions: {format_instructions}")  # Debugging output

    # Create SystemMessagePromptTemplate with format_instructions placeholder
    system_prompt_template = SystemMessagePromptTemplate.from_template(QUERY_ANALYSIS_PROMPT)
    
    # Create messages array with the template (not yet formatted)
    messages = [
        system_prompt_template,
        HumanMessage(content=user_question)
    ]

    # Generate prompt and inject format_instructions
    prompt = ChatPromptTemplate.from_messages(messages=messages).partial(format_instructions=format_instructions)
    print(f"Generated prompt: {prompt}")

    # Invoke LLM
    try:
        search_requests: SearchRequests = (prompt | llm_client | parser).invoke({})
        print(f"Parsed search requests: {search_requests}")

        if search_requests.search_request_parameters:
            requests_dict = {}
            for search_request in search_requests.search_request_parameters:
                requests_dict[search_request.search_field.value] = search_request.search_value

            print(f"Search parameters: {requests_dict}")

            # Search users
            users = user_client.search_users(**requests_dict)
            print(f"Users found: {users}")
            return users
        else:
            print("No specific search parameters found!")
            return []
    except Exception as e:
        print(f"Error during context retrieval: {e}")
        return []


def augment_prompt(user_question: str, context: list[dict[str, Any]]) -> str:
    """Combine user query with retrieved context into a formatted prompt."""
    print(f"Augmenting prompt for question: {user_question}")

    # Format context
    formatted_context = []
    for user in context:
        user_info = "\n".join([f"  {key}: {value}" for key, value in user.items()])
        formatted_context.append(f"User:\n{user_info}")
    context_string = "\n\n".join(formatted_context)

    # Combine with user question
    augmented_prompt = USER_PROMPT.format(context=context_string, query=user_question)
    print(f"Augmented prompt: {augmented_prompt}")
    return augmented_prompt


# Fix the response handling in `generate_answer`
async def generate_answer(augmented_prompt: str) -> str:
    print(f"Generating answer for augmented prompt: {augmented_prompt}")

    # Create messages array
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=augmented_prompt)
    ]

    # Generate response
    try:
        response = await llm_client.ainvoke(messages)
        return response.content
    except Exception as e:
        print(f"Error during answer generation: {e}")
        return "Error generating response."


async def main():
    print("Query samples:")
    print(" - I need user emails that filled with hiking and psychology")
    print(" - Who is John?")
    print(" - Find users with surname Adams")
    print(" - Do we have smbd with name John that love painting?")

    while True:
        try:
            user_question = input("Enter your query: ").strip()
            if not user_question:
                print("No query provided. Exiting.")
                break

            # Retrieve context
            context = retrieve_context(user_question)

            if context:
                # Confirm before augmenting prompt
                proceed = input("Context retrieved. Do you want to proceed with augmenting the prompt? (yes/no): ").strip().lower()
                if proceed != 'yes':
                    print("Process aborted by user.")
                    continue

                # Augment prompt
                augmented_prompt = augment_prompt(user_question, context)

                # Confirm before generating answer
                proceed = input("Prompt augmented. Do you want to proceed with generating the answer? (yes/no): ").strip().lower()
                if proceed != 'yes':
                    print("Process aborted by user.")
                    continue

                # Generate answer
                answer = await generate_answer(augmented_prompt)
                print(f"Answer: {answer}")
            else:
                print("No relevant information found.")
        except KeyboardInterrupt:
            print("\nProcess interrupted by user.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())


# The problems with API based Grounding approach are:
#   - We need a Pre-Step to figure out what field should be used for search (Takes time)
#   - Values for search should be correct (✅ John -> ❌ Jonh)
#   - Is not so flexible
# Benefits are:
#   - We fetch actual data (new users added and deleted every 5 minutes)
#   - Costs reduce