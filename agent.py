from dotenv import load_dotenv

load_dotenv()  # reads the API key from the .env file

import sqlite3
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
import db
from tools import ALL_TOOLS, CATEGORIES
from middleware import log_tool_calls, handle_tool_errors

SYSTEM_PROMPT = f"""You are a friendly personal expense tracker.
- All amounts are in Indian Rupees (Rs.).
- Categories must be one of: {", ".join(CATEGORIES)}. Pick the closest one.
- If the user mentions a relative date (today, yesterday, this week), call get_today first.
- If no date is mentioned, assume today.
- To change or delete an expense, find its id with list_expenses first.
- To change an expense, call update_expense with only the fields that change.
- Keep replies short."""

model = init_chat_model("groq:openai/gpt-oss-120b", temperature=0)

# Memory saved in a file, so the agent still remembers after a restart
memory = SqliteSaver(sqlite3.connect("memory.db", check_same_thread=False))

agent = create_agent(
    model=model,
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=memory,
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={"delete_expense": True}),  # pause and ask before deleting
        log_tool_calls,
        handle_tool_errors,
    ],
)


# ---------- streaming ----------
def text_of(content):
    """A chunk's content is a string (Groq) or a list of blocks (Gemini). Return only the text."""
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def _stream(agent_input, thread_id):
    """Run the agent and yield the reply piece by piece."""
    after_tool = False        # True once a tool has run
    sent_any = False          # True once we have yielded some text
    last_tool_result = ""     # the text of the last tool result
    for token, meta in agent.stream(
        agent_input,
        {"configurable": {"thread_id": thread_id}},
        stream_mode="messages",
    ):
        if meta["langgraph_node"] == "tools":   # tool output is not shown to the user
            after_tool = True
            last_tool_result = text_of(token.content)
            continue
        text = text_of(token.content)
        if not text:                            # tool-call chunks have no text
            continue
        if after_tool and sent_any:             # new paragraph after a tool call
            yield "\n\n"
        after_tool = False
        sent_any = True
        yield text
    # if the model said nothing after the tool ran, show the tool's own result
    if not sent_any and last_tool_result:
        yield last_tool_result


def stream_chat(message, thread_id="default"):
    return _stream({"messages": [{"role": "user", "content": message}]}, thread_id)


# ---------- human in the loop ----------
def get_pending(thread_id="default"):
    """If the agent is paused waiting for approval, return a question for the user. Otherwise ''."""
    state = agent.get_state({"configurable": {"thread_id": thread_id}})
    for interrupt in state.interrupts:
        for request in interrupt.value["action_requests"]:
            return f"The agent wants to run {request['name']} with {request['args']}. Allow it?"
    return ""


def stream_decision(approve, thread_id="default"):
    """Continue the paused agent after the user clicked Approve or Reject."""
    if approve:
        decision = {"type": "approve"}
    else:
        decision = {"type": "reject", "message": "The user rejected this action."}
    return _stream(Command(resume={"decisions": [decision]}), thread_id)


# ---------- structured output ----------
# Python works out the numbers. The model only writes three short sentences about them.
class Report(BaseModel):
    headline: str = Field(description="One sentence, max 15 words, saying where most money went, with the amount")
    insight: str = Field(description="One sentence about a pattern in the facts, using the exact numbers given")
    tip: str = Field(description="One short, specific tip about the biggest category or biggest expense")


report_agent = create_agent(
    model=model,
    response_format=Report,   # the agent must answer in this shape
    system_prompt=(
        "You write a short spending report from the facts you are given. Amounts are in Indian Rupees. "
        "Use only the numbers in the facts. Be specific and brief. No general advice."
    ),
)


def make_report():
    rows = db.get_expenses(limit=100)   # latest 100 expenses
    if not rows:
        return {"empty": True}

    total = float(sum(r["amount"] for r in rows))
    by_category = {}
    for r in rows:
        by_category[r["category"]] = by_category.get(r["category"], 0) + float(r["amount"])
    top_category = max(by_category, key=by_category.get)
    top_amount = by_category[top_category]
    biggest = max(rows, key=lambda r: r["amount"])
    biggest_text = f"Rs.{float(biggest['amount']):.0f} on {biggest['category']} ({biggest['description']})"

    facts = f"Total: Rs.{total:.0f} across {len(rows)} expenses.\n"
    facts += "\n".join(f"{c}: Rs.{a:.0f} ({a / total * 100:.0f}%)" for c, a in by_category.items())
    facts += f"\nBiggest single expense: {biggest_text} on {biggest['date']}."

    result = report_agent.invoke({"messages": [{"role": "user", "content": facts}]})
    ai = result["structured_response"]

    return {
        "total": total,
        "count": len(rows),
        "top_category": top_category,
        "top_amount": top_amount,
        "top_percent": round(top_amount / total * 100),
        "biggest": biggest_text,
        "headline": ai.headline,
        "insight": ai.insight,
        "tip": ai.tip,
    }
