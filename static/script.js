// ------------------ Dark/Light Mode ------------------
function toggleDarkLight() {
  document.body.classList.toggle("dark");
  localStorage.setItem("darkMode", document.body.classList.contains("dark"));
}
if (localStorage.getItem("darkMode") === "true") document.body.classList.add("dark");

// ------------------ Greetings ------------------
const greetings = [
  "What's on your mind today?",
  "Hello! How can I help you?",
  "Ready to chat!",
  "Ask me anything!"
];

function getRandomGreeting() {
  return greetings[Math.floor(Math.random() * greetings.length)];
}

// ------------------ Chat Storage ------------------
let conversations = [];
let currentChat = null;
let typingInterval = null;

// ------------------ Render Chat ------------------
function renderChat() {
  const chatDiv = document.getElementById("chat");
  chatDiv.innerHTML = "";

  const welcome = document.getElementById("welcome-title");

  if (!currentChat || currentChat.messages.length === 0) {
    welcome.style.display = "block";
    welcome.textContent = "OK is here"; // show welcome until first message
    return;
  } else {
    welcome.style.display = "none";
  }

  currentChat.messages.forEach(msg => {
    const div = document.createElement("div");
    div.className = "message " + msg.sender;
    div.innerHTML = msg.text.replace(/\n/g, "<br>");
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
    deleteBtn.onclick = (e) => {
      e.stopPropagation();
      conversations.splice(index, 1);
      saveConversations();
      if (currentChat === chat) startNewChat();
    };
    item.appendChild(deleteBtn);

    item.onclick = () => loadChat(index);
    historyDiv.appendChild(item);
  });
}

function saveConversations() {
  localStorage.setItem("conversations", JSON.stringify(conversations));
  renderHistory();
}

function loadChat(index) {
  currentChat = conversations[index];
  renderChat();
}

// ------------------ Typing Animation ------------------
function typeBotMessage(text, callback) {
  const chatDiv = document.getElementById("chat");
  const div = document.createElement("div");
  div.className = "message bot";
  chatDiv.appendChild(div);
  chatDiv.scrollTop = chatDiv.scrollHeight;

  let index = 0;
  const sendBtn = document.getElementById("sendBtn");
  sendBtn.textContent = "Stop";
  sendBtn.onclick = stopTyping;

  typingInterval = setInterval(() => {
    div.textContent += text.charAt(index);
    index++;
    chatDiv.scrollTop = chatDiv.scrollHeight;

    if (index === text.length) {
      clearInterval(typingInterval);
      typingInterval = null;
      sendBtn.textContent = "Send";
      sendBtn.onclick = sendMessage;
      if (callback) callback();
      div.style.animation = "slideInLeft 0.3s forwards";
    }
  }, 20);
}

function stopTyping() {
  if (typingInterval) {
    clearInterval(typingInterval);
    typingInterval = null;
    renderChat();
    const sendBtn = document.getElementById("sendBtn");
    sendBtn.textContent = "Send";
    sendBtn.onclick = sendMessage;
  }
}

// ------------------ Start New Chat ------------------
function startNewChat() {
  const newChat = {
    id: Date.now(),
    title: "New Conversation",
    messages: []
  };
  conversations = [newChat];
  currentChat = newChat;
  saveConversations();
  renderChat();
}

// ------------------ Send Message ------------------
async function sendMessage() {
  const input = document.getElementById("message");
  const message = input.value.trim();
  if (!message) return;

  if (currentChat.title === "New Conversation") {
    currentChat.title = message.length > 30 ? message.slice(0,30) + "..." : message;
  }

  const userMsg = {sender: "user", text: message};
  currentChat.messages.push(userMsg);
  renderChat();
  input.value = "";

  const chatDiv = document.getElementById("chat");
  const typingDiv = document.createElement("div");
  typingDiv.className = "message bot";
  typingDiv.textContent = "Typing...";
  chatDiv.appendChild(typingDiv);
  chatDiv.scrollTop = chatDiv.scrollHeight;

  // Hide welcome overlay after first message
  document.getElementById("welcome-title").style.display = "none";

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message})
    });
    const data = await response.json();
    typingDiv.remove();
    currentChat.messages.push({sender: "bot", text: data.reply});
    renderChat();
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
  document.getElementById("login-form").style.display = type==='login'?"block":"none";
  document.getElementById("signup-form").style.display = type==='signup'?"block":"none";
}

function closeAuthModal() {
  document.getElementById("auth-modal").style.display = "none";
}

// ------------------ Login/Signup ------------------
async function login() {
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;
  const res = await fetch("/login", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({username, password})
  });
  const data = await res.json();
  if(data.success){
    closeAuthModal();
    alert("Logged in!");
    location.reload();
  } else alert(data.message);
}

async function signup() {
  const username = document.getElementById("signup-username").value;
  const password = document.getElementById("signup-password").value;
  const res = await fetch("/signup", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({username, password})
  });
  const data = await res.json();
  if(data.success){
    closeAuthModal();
    alert("Signed up!");
    location.reload();
  } else alert(data.message);
}

// ------------------ Logout ------------------
function logoutUser() {
  fetch('/logout')
    .then(() => location.reload())
    .catch(err => console.error(err));
}

// ------------------ Load conversations ------------------
window.onload = () => {
  const saved = JSON.parse(localStorage.getItem("conversations") || "[]");
  if(saved.length>0){
    conversations = saved;
    currentChat = conversations[0];
  }
  renderChat();
};
