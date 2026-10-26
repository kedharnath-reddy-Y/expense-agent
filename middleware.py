
from langchain.agents.middleware import wrap_tool_call
from langchain_core.messages import ToolMessage


@wrap_tool_call
def log_tool_calls(request, handler):
    """Print every tool call and its result in the terminal."""
    name = request.tool_call["name"]
    args = request.tool_call["args"]

    print(f"[TOOL CALL]   {name} {args}")

    result = handler(request)  # Run the real tool

    print(f"[TOOL RESULT] {getattr(result, 'content', result)}")

    return result


@wrap_tool_call
def handle_tool_errors(request, handler):
    """If a tool crashes (for example MySQL is down), tell the model instead of crashing the app."""
    try:
        return handler(request)

    except Exception as e:
        print(f"[TOOL ERROR]  {request.tool_call['name']}: {e}")

        return ToolMessage(
            content=f"The tool failed: {e}. Tell the user it did not work.",
            tool_call_id=request.tool_call["id"],
        )