import React, { useEffect, useRef, useState } from 'react';
import ChatMessage from './ChatMessage';
import * as chatbotService from '../api/chatbotService';

const WELCOME_MESSAGE = {
  role: 'assistant',
  text: "Hi, I'm the Traffic Assistant. Ask me about congestion, accident risk, or hotspots anywhere in the system.",
};

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  async function handleSend(e) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    const userMessage = { role: 'user', text: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsSending(true);

    try {
      const { reply } = await chatbotService.sendMessage(trimmed);
      setMessages((prev) => [...prev, { role: 'assistant', text: reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: "Sorry, I couldn't reach the assistant service. Please try again.",
          isError: true,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  function handleReset() {
    chatbotService.resetConversation();
    setMessages([WELCOME_MESSAGE]);
  }

  return (
    <div className="fixed bottom-5 right-5 z-50">
      {isOpen && (
        <div className="mb-3 flex h-[28rem] w-80 flex-col overflow-hidden rounded-lg border border-asphalt-700 bg-asphalt-900 shadow-xl">
          <div className="flex items-center justify-between border-b border-asphalt-700 px-4 py-3">
            <div>
              <p className="text-sm font-medium text-asphalt-100">Traffic Assistant</p>
              <p className="text-xs text-asphalt-400">Ask about traffic &amp; accidents</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleReset}
                title="Start a new conversation"
                className="text-xs text-asphalt-400 hover:text-asphalt-100"
              >
                Reset
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="text-asphalt-400 hover:text-asphalt-100"
                aria-label="Close chat"
              >
                ✕
              </button>
            </div>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-2 overflow-y-auto px-3 py-3">
            {messages.map((m, idx) => (
              <ChatMessage key={idx} role={m.role} text={m.text} isError={m.isError} />
            ))}
            {isSending && (
              <ChatMessage role="assistant" text="Thinking…" />
            )}
          </div>

          <form
            onSubmit={handleSend}
            className="flex items-center gap-2 border-t border-asphalt-700 p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about traffic conditions…"
              className="flex-1 rounded-md border border-asphalt-600 bg-asphalt-800 px-3 py-2 text-sm text-asphalt-100 outline-none focus:border-signal-blue"
            />
            <button
              type="submit"
              disabled={isSending || !input.trim()}
              className="rounded-md bg-signal-blue px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      )}

      <button
        onClick={() => setIsOpen((v) => !v)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-signal-blue text-white shadow-lg hover:opacity-90"
        aria-label="Toggle chat assistant"
      >
        {isOpen ? '✕' : '💬'}
      </button>
    </div>
  );
}
