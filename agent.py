from dotenv import load_dotenv

load_dotenv()  # reads GOOGLE_API_KEY from the .env file

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from tools import ALL_TOOLS, CATEGORIES

SYSTEM_PROMPT = f"""You are a friendly personal expense tracker.
- All amounts are in Indian Rupees (Rs.).
- Categories must be one of: {", ".join(CATEGORIES)}. Pick the closest one.
- If the user mentions a relative date (today, yesterday, this week), call get_today first.
- If no date is mentioned, assume today.
- To delete an expense, find its id with list_expenses first.
- Keep replies short."""

agent = create_agent(
    model="google_genai:gemini-3.1-flash-lite",
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=InMemorySaver(),  # remembers the conversation per thread_id
)


def chat(message: str, thread_id: str = "default") -> str:
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        {"configurable": {"thread_id": thread_id}},
    )
    content = result["messages"][-1].content
    # Gemini returns a list of blocks (you saw this in your notebook), so pull out the text
    if isinstance(content, list):
        content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content
