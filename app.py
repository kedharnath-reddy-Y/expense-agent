from flask import Flask, request, jsonify, render_template, Response
from agent import stream_chat, stream_decision, get_pending, make_report
from db import init_db, get_expenses, save_message, get_messages, get_chats

app = Flask(__name__)
init_db()


def stream_and_save(pieces, thread_id):
    """Send each piece to the browser, then save the full reply when it ends."""
    reply = ""
    try:
        for piece in pieces:
            reply += piece
            yield piece
    except Exception as e:
        error = f"\nSorry, something went wrong: {e}"
        reply += error
        yield error
    finally:
        if reply.strip():
            save_message(thread_id, "assistant", reply)


@app.route("/")
def home():
    return render_template("index.html")


@app.post("/chat")
def chat_route():
    message = request.json["message"]
    thread_id = request.json.get("thread_id", "default")
    save_message(thread_id, "user", message)
    return Response(stream_and_save(stream_chat(message, thread_id), thread_id), mimetype="text/plain")


@app.post("/decide")
def decide_route():
    thread_id = request.json.get("thread_id", "default")
    approve = request.json["decision"] == "approve"
    question = get_pending(thread_id)
    if question:
        save_message(thread_id, "assistant", question)   # keep the question in the saved chat
    save_message(thread_id, "user", "Approved" if approve else "Rejected")
    return Response(stream_and_save(stream_decision(approve, thread_id), thread_id), mimetype="text/plain")


@app.get("/pending")
def pending_route():
    thread_id = request.args.get("thread_id", "default")
    return jsonify(question=get_pending(thread_id))


@app.get("/chats")
def chats_route():
    return jsonify(get_chats())


@app.get("/history")
def history():
    thread_id = request.args.get("thread_id", "default")
    return jsonify(get_messages(thread_id))


@app.get("/expenses")
def expenses():
    rows = get_expenses(limit=20)
    for r in rows:
        r["date"] = str(r["date"])
    return jsonify(rows)


@app.get("/report")
def report_route():
    try:
        return jsonify(make_report())
    except Exception as e:
        return jsonify(error=str(e)), 500


if __name__ == "__main__":
    app.run(debug=True)
