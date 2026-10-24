from flask import Flask, request, jsonify, render_template
from agent import chat
from tools import init_db, db

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
    rows = db().execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 20").fetchall()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(debug=True)
