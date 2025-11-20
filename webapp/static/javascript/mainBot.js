document.addEventListener("DOMContentLoaded", () => {
  console.log("✅ mainBot.js loaded successfully");

  // === Element References ===
  const chatContainer = document.getElementById("chatbott");
  const chatInput = document.getElementById("messageInput");
  const sendButton = document.getElementById("btnClick");
  const newChatButton = document.getElementById("new-chat-button");
  const themeButton = document.getElementById("theme-btn");

  let userChatHistory = [];

  // === Load Theme from Local Storage ===
  const savedTheme = localStorage.getItem("themeColor");
  if (savedTheme === "light_mode") {
    document.body.classList.add("light-mode");
    themeButton.innerText = "light_mode";
  } else {
    themeButton.innerText = "dark_mode";
  }

  // === Load Chat History from Local Storage ===
  const savedChats = JSON.parse(localStorage.getItem("chatHistory")) || [];
  userChatHistory = savedChats;
  chatContainer.innerHTML = "";
  savedChats.forEach(msg => chatContainer.insertAdjacentHTML("beforeend", msg));
  chatContainer.scrollTop = chatContainer.scrollHeight;

  // === Theme Toggle ===
  themeButton.addEventListener("click", () => {
    document.body.classList.toggle("light-mode");
    const theme = document.body.classList.contains("light-mode") ? "light_mode" : "dark_mode";
    themeButton.innerText = theme;
    localStorage.setItem("themeColor", theme);
  });

  // === Typing Animation Helper ===
  function typeWriter(text, element, speed = 30) {
    let i = 0;
    function typing() {
      if (i < text.length) {
        element.textContent += text.charAt(i);
        i++;
        setTimeout(typing, speed);
      }
    }
    typing();
  }

  // === Bot Reply Logic ===
  function getBotReply(userMessage) {
    const msg = userMessage.toLowerCase();
    const replies = {
      "hi": "Hi there! I'm Sting Chatbot, how can I assist you today?",
      "hello": "Hello! How are you doing today?",
      "who are you": "I'm Sting Chatbot, your virtual assistant from CvSU!",
      "what can you do": "I can answer basic questions and help guide you through CvSU-related info.",
      "bye": "Goodbye! Have a great day ahead!",
      "thank you": "You're very welcome!",
    };
    return replies[msg] || "I'm not sure I understand that yet, but I'm learning every day!";
  }

  // === Append Messages ===
  function appendMessage(sender, message) {
    const msgClass = sender === "user" ? "userText" : "botText";
    const msgHTML = `<p class='${msgClass}'><span class='typing'></span></p>`;
    chatContainer.insertAdjacentHTML("beforeend", msgHTML);

    const msgElement = chatContainer.querySelectorAll(".typing");
    const lastMsg = msgElement[msgElement.length - 1];
    typeWriter(message, lastMsg);

    // Save to history
    userChatHistory.push(msgHTML.replace("typing'></span>", `typing'>${message}</span>`));
    localStorage.setItem("chatHistory", JSON.stringify(userChatHistory));

    // Auto scroll
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  // === Handle Send Message ===
  function handleSendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    appendMessage("user", message);
    chatInput.value = "";

    setTimeout(() => {
      const reply = getBotReply(message);
      appendMessage("bot", reply);
    }, 500);
  }

  // === Button Click & Enter Key ===
  sendButton.addEventListener("click", handleSendMessage);
  chatInput.addEventListener("keydown", e => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // === New Chat Button (clears chat) ===
  newChatButton.addEventListener("click", () => {
    if (confirm("Start a new chat? This will clear your previous messages.")) {
      localStorage.removeItem("chatHistory");
      userChatHistory = [];
      chatContainer.innerHTML = "";
      appendMessage("bot", "New chat started! 👋 How can I assist you today?");
    }
  });

  // === Greeting Message (if no history) ===
  if (userChatHistory.length === 0) {
    appendMessage("bot", "Hi there! I'm Sting Chatbot 👋 How can I assist you today?");
  }
});
