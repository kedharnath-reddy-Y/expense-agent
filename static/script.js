const messages = document.getElementById("messages");
const input = document.getElementById("input");

function addMessage(text, who) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

async function loadExpenses() {
  const res = await fetch("/expenses");
  const data = await res.json();
  document.getElementById("rows").innerHTML = data.map(e =>
    `<tr><td>${e.id}</td><td>${e.date}</td><td>${e.amount}</td><td>${e.category}</td><td>${e.description}</td></tr>`
  ).join("");
}

document.getElementById("form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMessage(text, "user");
  const thinking = addMessage("...", "bot");
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text }),
  });
  const data = await res.json();
  thinking.textContent = data.reply;
  loadExpenses();  // refresh the table after every message
});

loadExpenses();
