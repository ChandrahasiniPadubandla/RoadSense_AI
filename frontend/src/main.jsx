import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { loginUser, sendChatbotMessage } from "./api_services";
import "./styles.css";

const starterQuestions = [
  "What does the traffic prediction module do?",
  "How is accident risk calculated?",
  "What is an accident hotspot?",
  "Does this chatbot have live traffic data?",
];

function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await loginUser(email, password);
      localStorage.setItem("roadsense_access_token", data.access_token);
      onLogin();
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Unable to log in. Check the backend connection and your credentials."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-panel">
        <div className="login-mark">RS</div>
        <div className="eyebrow">ROADSENSE AI</div>
        <h1>Welcome back</h1>
        <p className="login-subtitle">Sign in to your traffic intelligence workspace.</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && <div className="login-error" role="alert">{error}</div>}
          <button className="login-button" type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}

function App() {
  const [authenticated, setAuthenticated] = useState(
    () => Boolean(localStorage.getItem("roadsense_access_token"))
  );
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

  if (!authenticated) {
    return <Login onLogin={() => setAuthenticated(true)} />;
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
          <button className="logout-button" onClick={() => {
            localStorage.removeItem("roadsense_access_token");
            setAuthenticated(false);
          }}>Sign out</button>
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
