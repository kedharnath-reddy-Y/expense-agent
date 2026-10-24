from flask import Flask, request, jsonify, render_template
from agent import chat
from tools import init_db, run
app = Flask(__name__)
init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.post("/chat")
def chat_route():
    message = request.json["message"]
    try:
        return jsonify(reply=chat(message))
    except Exception as e:  # e.g. the 503 "high demand" error you hit earlier
        return jsonify(reply=f"Sorry, something went wrong: {e}"), 500


@app.get("/expenses")
def expenses():
    rows, _, _ = run("SELECT * FROM expenses ORDER BY id DESC LIMIT 20")
    for r in rows:
        r["date"] = str(r["date"])   # 2026-10-25 instead of "Sun, 25 Oct 2026 00:00:00 GMT"
    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True)
