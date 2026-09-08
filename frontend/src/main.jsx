import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { sendChatbotMessage } from "./api_services";
import "./styles.css";

const starterQuestions = [
  "What does the traffic prediction module do?",
  "How is accident risk calculated?",
  "What is an accident hotspot?",
  "Does this chatbot have live traffic data?",
];

function App() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I’m the Smart Traffic AI Assistant. Ask me about traffic, accident risk, hotspots, anomalies, alerts, emergency response, or the application modules.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("");

  async function sendMessage(text = input) {
    const message = text.trim();
    if (!message || loading) return;

    const history = messages.slice(-10);
    setMessages((current) => [...current, { role: "user", content: message }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendChatbotMessage(message, history);
      setMessages((current) => [
        ...current,
        { role: "assistant", content: data.reply },
      ]);
      setMode(data.mode);
    } catch (error) {
      const detail =
        error.response?.data?.detail ||
        error.message ||
        "Could not connect to the chatbot backend.";
      setMessages((current) => [...current, { role: "assistant", content: detail }]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage();
  }

  return (
    <div className="page">
      <div className="app-shell">
        <header className="header">
          <div className="brand">
            <div className="logo">🚦</div>
            <div>
              <div className="eyebrow">SMART TRAFFIC AI</div>
              <h1>Traffic Intelligence Assistant</h1>
            </div>
          </div>
          <div className="online"><span /> Online</div>
        </header>

        <main className="content">
          <section className="intro">
            <h2>How can I help?</h2>
            <p>Ask questions about the Smart Traffic & Accident Prediction System.</p>
          </section>

          <section className="suggestions">
            {starterQuestions.map((question) => (
              <button key={question} onClick={() => sendMessage(question)}>{question}</button>
            ))}
          </section>

          <section className="chat-window">
            <div className="messages">
              {messages.map((message, index) => (
                <div key={index} className={`message-row ${message.role}`}>
                  <div className="avatar">{message.role === "assistant" ? "AI" : "You"}</div>
                  <div className="bubble">{message.content}</div>
                </div>
              ))}
              {loading && (
                <div className="message-row assistant">
                  <div className="avatar">AI</div>
                  <div className="bubble typing">Thinking…</div>
                </div>
              )}
            </div>

            <form className="composer" onSubmit={handleSubmit}>
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask about traffic, accident risk, alerts..."
                disabled={loading}
              />
              <button type="submit" disabled={loading || !input.trim()}>Send</button>
            </form>
            <div className="footer-note">
              {mode === "openai" ? "AI mode: OpenAI" : "Standalone mode: local knowledge responses"}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
