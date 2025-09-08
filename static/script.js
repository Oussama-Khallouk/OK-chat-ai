// ------------------ Dark/Light Mode ------------------
function toggleDarkLight() {
  document.body.classList.toggle("dark");
  localStorage.setItem("darkMode", document.body.classList.contains("dark"));
}
if (localStorage.getItem("darkMode") === "true") document.body.classList.add("dark");

// ------------------ Chat Storage ------------------
let conversations = [];
let currentChat = null;

// ------------------ Load Conversations ------------------
async function loadConversations() {
  if (!document.body.dataset.loggedin) return;
  const res = await fetch("/get_chats");
  conversations = await res.json();
  if (conversations.length > 0) currentChat = conversations[0];
  renderChat();
}

// ------------------ Render Chat ------------------
function renderChat() {
  const chatDiv = document.getElementById("chat");
  chatDiv.innerHTML = "";

  const welcome = document.getElementById("welcome-title");
  if (!currentChat || currentChat.messages.length === 0) {
    welcome.style.display = "block";
    welcome.textContent = "OK is here";
    return;
  } else welcome.style.display = "none";

  currentChat.messages.forEach((msg, index) => {
    const div = document.createElement("div");
    div.className = "message " + msg.sender;
    div.innerHTML = msg.text.replace(/\n/g, "<br>");

    if (msg.sender === "user") {
      const editBtn = document.createElement("button");
      editBtn.textContent = "✏️";
      editBtn.onclick = async () => {
        const newText = prompt("Edit message:", msg.text);
        if (newText) {
          msg.text = newText;
          renderChat();
          if (currentChat.db_id) {
            await fetch(`/chat/${currentChat.db_id}/edit_message`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ index, text: newText })
            });
          }
        }
      };

      const delBtn = document.createElement("button");
      delBtn.textContent = "🗑";
      delBtn.onclick = async () => {
        if (confirm("Delete this message?")) {
          currentChat.messages.splice(index, 1);
          renderChat();
          if (currentChat.db_id) {
            await fetch(`/chat/${currentChat.db_id}/delete_message`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ index })
            });
          }
        }
      };
      div.appendChild(editBtn);
      div.appendChild(delBtn);
    }

    chatDiv.appendChild(div);
  });

  chatDiv.scrollTop = chatDiv.scrollHeight;
  renderHistory();
}

// ------------------ Sidebar ------------------
function renderHistory() {
  const historyDiv = document.getElementById("history");
  historyDiv.innerHTML = "";
  conversations.forEach((chat, index) => {
    const item = document.createElement("div");
    item.className = "history-item";
    const titleSpan = document.createElement("span");
    titleSpan.textContent = chat.title;
    item.appendChild(titleSpan);

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "🗑";
    deleteBtn.onclick = e => {
      e.stopPropagation();
      conversations.splice(index, 1);
      renderHistory();
      if (currentChat === chat) currentChat = null;
      renderChat();
    };
    item.appendChild(deleteBtn);

    item.onclick = () => {
      currentChat = conversations[index];
      renderChat();
    };
    historyDiv.appendChild(item);
  });
}

// ------------------ New Chat ------------------
async function startNewChat() {
  if (!document.body.dataset.loggedin) return alert("Log in first");
  const res = await fetch("/create_chat", { method: "POST" });
  const data = await res.json();
  if (!data.success) return alert("Error creating chat");

  const newChat = data.chat; // {db_id,title,messages}
  conversations = [newChat];
  currentChat = newChat;
  renderChat();
}

// ------------------ Send Message ------------------
async function sendMessage() {
  const input = document.getElementById("message");
  const message = input.value.trim();
  if (!message) return;

  if (currentChat.title === "New Conversation")
    currentChat.title = message.length > 30 ? message.slice(0, 30) + "..." : message;

  const userMsg = { sender: "user", text: message };
  currentChat.messages.push(userMsg);
  renderChat();
  input.value = "";

  if (currentChat.db_id) {
    await fetch(`/chat/${currentChat.db_id}/add_message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(userMsg)
    });
  }

  // AI response
  const chatDiv = document.getElementById("chat");
  const typingDiv = document.createElement("div");
  typingDiv.className = "message bot";
  typingDiv.textContent = "Typing...";
  chatDiv.appendChild(typingDiv);
  chatDiv.scrollTop = chatDiv.scrollHeight;

  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const data = await res.json();
    typingDiv.remove();
    const botMsg = { sender: "bot", text: data.reply };
    currentChat.messages.push(botMsg);
    renderChat();

    if (currentChat.db_id) {
      await fetch(`/chat/${currentChat.db_id}/add_message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(botMsg)
      });
    }
  } catch (err) {
    typingDiv.textContent = "Error fetching response";
  }
}

// ------------------ Filter Chats ------------------
function filterChats() {
  const filter = document.getElementById("searchInput").value.toLowerCase();
  const historyDiv = document.getElementById("history");
  Array.from(historyDiv.children).forEach(item => {
    const text = item.children[0].textContent.toLowerCase();
    item.style.display = text.includes(filter) ? "flex" : "none";
  });
}

// ------------------ Auth Modal ------------------
function openAuthModal(type) {
  document.getElementById("auth-modal").style.display = "flex";
  document.getElementById("login-form").style.display = type === "login" ? "block" : "none";
  document.getElementById("signup-form").style.display = type === "signup" ? "block" : "none";
}
function closeAuthModal() {
  document.getElementById("auth-modal").style.display = "none";
}

// ------------------ Profile Modal ------------------
function openProfileModal() {
  document.getElementById("profile-modal").style.display = "flex";
}
function closeProfileModal() {
  document.getElementById("profile-modal").style.display = "none";
}

// ------------------ Login/Signup ------------------
async function login() {
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  const res = await fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  const data = await res.json();
  if (data.success) { closeAuthModal(); location.reload(); }
  else alert(data.message);
}

async function signup() {
  const email = document.getElementById("signup-email").value;
  const password = document.getElementById("signup-password").value;
  const res = await fetch("/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  const data = await res.json();
  if (data.success) { closeAuthModal(); location.reload(); }
  else alert(data.message);
}

// ------------------ Google Login ------------------
function googleLogin() {
  window.location.href = "/login/google"; // handled by backend OAuth
}

// ------------------ Profile Settings ------------------
async function changePassword() {
  const newPass = document.getElementById("new-password").value;
  if (!newPass) return alert("Enter a new password");
  const res = await fetch("/change_password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: newPass })
  });
  const data = await res.json();
  alert(data.message);
  if (data.success) closeProfileModal();
}

async function deleteAccount() {
  if (!confirm("Are you sure? This cannot be undone.")) return;
  const res = await fetch("/delete_account", { method: "POST" });
  const data = await res.json();
  alert(data.message);
  if (data.success) location.reload();
}

// ------------------ Logout ------------------
function logoutUser() {
  fetch("/logout").then(() => location.reload()).catch(console.error);
}

// ------------------ Window Onload ------------------
window.onload = () => {
  loadConversations();
};
