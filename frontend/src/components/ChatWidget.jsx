import React, { useEffect, useRef, useState } from 'react';
import ChatMessage from './ChatMessage';
import { sendChatbotMessage } from '../api_services';

const STARTER_QUESTIONS = [
  'What roads does RoadSense track?',
  'What is the accident risk from Banjara Hills to Hitec City?',
  'Which zones have the most accident hotspots?',
  'What are the current system-wide traffic statistics?',
];

const WELCOME_MESSAGE = {
  role: 'assistant',
  text: 'Hi! I’m the RoadSense AI Assistant, powered by Groq + LangChain. Ask me about traffic conditions, congestion predictions, accident risk, routes, or accident hotspots — all answers are grounded in real RoadSense data and ML predictions.',
};

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading, isOpen]);

  async function sendMessage(text = input) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMessage = { role: 'user', text: trimmed };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    try {
      const history = nextMessages
        .slice(-10)
        .map((m) => ({ role: m.role, content: m.text }));

      const data = await sendChatbotMessage(trimmed, history);

      setMessages((current) => [
        ...current,
        { role: 'assistant', text: data.reply },
      ]);
      if (data.mode) {
        setMode(data.mode);
      }
    } catch (error) {
      const detail =
        error.response?.data?.detail ||
        error.message ||
        'Could not connect to the chatbot backend.';
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: detail, isError: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    sendMessage();
  }

  function handleReset() {
    setMessages([WELCOME_MESSAGE]);
    setMode('');
  }

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {isOpen && (
        <div className="mb-3 flex h-[32rem] w-88 max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-xl border border-asphalt-700 bg-asphalt-900 shadow-2xl transition-all">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-asphalt-700 bg-asphalt-850 px-4 py-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal-blue/20 text-base">
                🚦
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <p className="text-xs font-bold tracking-wider text-asphalt-100 uppercase">
                    Smart Traffic AI
                  </p>
                  <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-1.5 py-0.2 text-[10px] font-semibold text-emerald-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    Online
                  </span>
                </div>
                <p className="text-[11px] text-asphalt-400">Traffic Intelligence Assistant</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleReset}
                title="Restart conversation"
                className="rounded px-1.5 py-0.5 text-xs text-asphalt-400 hover:bg-asphalt-800 hover:text-asphalt-100"
              >
                Reset
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="rounded p-1 text-asphalt-400 hover:bg-asphalt-800 hover:text-asphalt-100"
                aria-label="Close chat"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-3.5 py-3">
            {messages.map((m, idx) => (
              <ChatMessage key={idx} role={m.role} text={m.text} isError={m.isError} />
            ))}

            {/* Starter Suggestion Chips (when conversation is fresh) */}
            {messages.length === 1 && (
              <div className="mt-2 space-y-1.5 pt-1">
                <p className="text-[11px] font-medium text-asphalt-400">Suggested questions:</p>
                <div className="flex flex-col gap-1.5">
                  {STARTER_QUESTIONS.map((question) => (
                    <button
                      key={question}
                      onClick={() => sendMessage(question)}
                      disabled={loading}
                      className="rounded-lg border border-asphalt-700 bg-asphalt-800/80 px-2.5 py-1.5 text-left text-xs text-asphalt-200 transition-colors hover:border-signal-blue/50 hover:bg-asphalt-800 hover:text-signal-blue disabled:opacity-50"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {loading && (
              <div className="flex items-center gap-2 text-xs text-asphalt-400">
                <div className="flex h-5 items-center gap-1 rounded-md bg-asphalt-800 px-2.5 py-1 text-xs text-asphalt-300">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-asphalt-400"></span>
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-asphalt-400 [animation-delay:0.2s]"></span>
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-asphalt-400 [animation-delay:0.4s]"></span>
                  <span className="ml-1 text-[11px]">Thinking…</span>
                </div>
              </div>
            )}
          </div>

          {/* Input Composer */}
          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 border-t border-asphalt-700 bg-asphalt-900 p-2.5"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about traffic, accident risk, alerts..."
              disabled={loading}
              className="flex-1 rounded-lg border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-xs text-asphalt-100 outline-none placeholder:text-asphalt-500 focus:border-signal-blue"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-lg bg-signal-blue px-3 py-2 text-xs font-semibold text-white transition-opacity hover:opacity-95 disabled:opacity-40"
            >
              Send
            </button>
          </form>

          {/* Mode Footer Note */}
          <div className="border-t border-asphalt-800 bg-asphalt-950 px-3 py-1.5 text-right text-[10px] text-asphalt-400">
            {mode === 'groq'
              ? 'Powered by Groq · LangChain'
              : 'RoadSense AI Assistant'}
          </div>
        </div>
      )}

      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-signal-blue text-white shadow-xl transition-transform hover:scale-105 active:scale-95"
        aria-label="Toggle chat assistant"
      >
        {isOpen ? '✕' : '💬'}
      </button>
    </div>
  );
}
