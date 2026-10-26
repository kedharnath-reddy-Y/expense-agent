const messages = document.getElementById("messages");
const input = document.getElementById("input");
const sendButton = document.getElementById("send");

// Every chat has its own ID. The current one is remembered in localStorage.
function makeId() {
    return Date.now() + "-" + Math.random().toString(36).slice(2);
}

let threadId = localStorage.getItem("thread_id");

if (!threadId) {
    threadId = makeId();
    localStorage.setItem("thread_id", threadId);
}

// ---------- Message handling ----------

function addMessage(text, who) {
    const div = document.createElement("div");

    div.className = "msg " + who;
    div.textContent = text;

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;

    return div;
}

// Lock the input while the agent is working or waiting for approval.
function setBusy(busy) {
    input.disabled = busy;
    sendButton.disabled = busy;

    if (!busy) {
        input.focus();
    }
}

// Read a streamed reply piece by piece into a chat bubble.
async function showStream(res, bubble) {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    let reply = "";

    while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        reply += decoder.decode(value, { stream: true });
        bubble.textContent = reply;

        messages.scrollTop = messages.scrollHeight;
    }
}

// ---------- Sidebar: list of chats ----------

async function loadChats() {
    const res = await fetch("/chats");
    const chats = await res.json();

    // A brand-new chat has no messages yet, so show it as "New chat".
    if (!chats.some(c => c.thread_id === threadId)) {
        chats.unshift({
            thread_id: threadId,
            title: "New chat"
        });
    }

    const list = document.getElementById("chats");
    list.innerHTML = "";

    chats.forEach(c => {
        const item = document.createElement("div");

        item.className =
            "chat-item" + (c.thread_id === threadId ? " active" : "");

        item.textContent = c.title || "New chat";
        item.onclick = () => openChat(c.thread_id);

        list.appendChild(item);
    });
}

function newChat() {
    if (input.disabled) return; // Wait until the agent is done.

    threadId = makeId();
    localStorage.setItem("thread_id", threadId);

    messages.innerHTML = "";

    loadChats();
    input.focus();
}

async function openChat(id) {
    if (input.disabled || id === threadId) return;

    threadId = id;
    localStorage.setItem("thread_id", threadId);

    messages.innerHTML = "";

    await loadHistory();
    checkPending();
    loadChats();
}

// ---------- Messages and expenses ----------

async function loadHistory() {
    const res = await fetch("/history?thread_id=" + threadId);
    const data = await res.json();

    data.forEach(m => {
        addMessage(m.text, m.role === "user" ? "user" : "bot");
    });
}

async function loadExpenses() {
    const res = await fetch("/expenses");
    const data = await res.json();

    document.getElementById("rows").innerHTML = data.map((e, i) =>
        `<tr>
            <td title="database id: ${e.id}">${i + 1}</td>
            <td>${e.date}</td>
            <td>${e.amount}</td>
            <td>${e.category}</td>
            <td>${e.description}</td>
        </tr>`
    ).join("");
}

// ---------- Approve / reject ----------

async function checkPending() {
    const res = await fetch("/pending?thread_id=" + threadId);
    const data = await res.json();

    if (data.question) {
        showConfirm(data.question);
    }
}

function showConfirm(question) {
    setBusy(true);

    const box = document.createElement("div");

    box.className = "msg bot confirm";

    box.innerHTML = `
        <div></div>
        <button data-choice="approve">Approve</button>
        <button data-choice="reject" class="secondary">Reject</button>
    `;

    box.firstElementChild.textContent = question;

    box.querySelectorAll("button").forEach(b => {
        b.onclick = () => decide(b.dataset.choice, box);
    });

    messages.appendChild(box);
    messages.scrollTop = messages.scrollHeight;
}

async function decide(choice, box) {
    // Keep the question and remove the buttons.
    box.querySelectorAll("button").forEach(b => b.remove());

    addMessage(
        choice === "approve" ? "Approved" : "Rejected",
        "user"
    );

    const bubble = addMessage("...", "bot");

    const res = await fetch("/decide", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            thread_id: threadId,
            decision: choice
        })
    });

    await showStream(res, bubble);

    setBusy(false);

    loadExpenses();
    checkPending();
}

// ---------- Sending a message ----------

document.getElementById("form").addEventListener("submit", async (ev) => {
    ev.preventDefault();

    const text = input.value.trim();

    if (!text) return;

    input.value = "";
    setBusy(true);

    addMessage(text, "user");

    const bubble = addMessage("...", "bot");

    const res = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            message: text,
            thread_id: threadId
        })
    });

    await showStream(res, bubble);

    setBusy(false);

    loadExpenses(); // Refresh the table once the reply is complete.
    loadChats();    // The chat now has a title.
    checkPending(); // Check whether the agent needs approval.
});

// ---------- Spending report (structured output) ----------

document.getElementById("report-btn").addEventListener("click", async () => {
    const bubble = addMessage("Making your report...", "bot");

    const res = await fetch("/report");
    const r = await res.json();

    if (!res.ok) {
        bubble.textContent = "Could not make the report: " + r.error;
    } else if (r.empty) {
        bubble.textContent =
            "No expenses yet, so there is nothing to report.";
    } else {
        bubble.textContent =
            `Total: Rs.${r.total} (${r.count} expenses)\n` +
            `Top category: ${r.top_category}, Rs.${r.top_amount} (${r.top_percent}%)\n` +
            `Biggest expense: ${r.biggest}\n\n` +
            `${r.headline}\n${r.insight}\nTip: ${r.tip}`;
    }
});

// ---------- Event listeners and initialization ----------

document.getElementById("new-chat").addEventListener("click", newChat);

loadHistory().then(checkPending);
loadChats();
loadExpenses();
