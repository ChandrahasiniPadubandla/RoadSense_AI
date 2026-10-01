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
  text: 'Hi! I’m the RoadSense AI Assistant. Ask me about traffic conditions, congestion predictions, accident risk, routes, or accident hotspots — all answers are grounded in RoadSense data and ML predictions.',
};

export default function ChatWidget({
  isOpen,
  setIsOpen,
}) {
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('');

  const scrollRef = useRef(null);

  // Automatically scroll to latest message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop =
        scrollRef.current.scrollHeight;
    }
  }, [messages, loading, isOpen]);

  // Send message to backend
  async function sendMessage(text = input) {
    const trimmed = text.trim();

    if (!trimmed || loading) return;

    const userMessage = {
      role: 'user',
      text: trimmed,
    };

    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    try {
      // Send last 10 messages as conversation history
      const history = nextMessages
        .slice(-10)
        .map((m) => ({
          role: m.role,
          content: m.text,
        }));

      const data = await sendChatbotMessage(
        trimmed,
        history
      );

      // Add AI response
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: data.reply,
        },
      ]);

      // Update backend mode
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
        {
          role: 'assistant',
          text: detail,
          isError: true,
        },
      ]);

    } finally {
      setLoading(false);
    }
  }

  // Handle form submit
  function handleSubmit(e) {
    e.preventDefault();
    sendMessage();
  }

  // Reset conversation
  function handleReset() {
    setMessages([WELCOME_MESSAGE]);
    setMode('');
    setInput('');
  }

  return (
    <>
      {/* =========================================================
          FULL HEIGHT CHAT PANEL
      ========================================================= */}

      {isOpen && (
        <div
          className="
            fixed
            right-0
            top-0
            z-50

            flex
            h-screen
            w-[360px]
            max-w-[90vw]
            flex-col
            overflow-hidden

            border-l
            border-slate-200
            bg-white
            shadow-2xl

            dark:border-slate-700
            dark:bg-slate-900

            transition-transform
            duration-300
            ease-in-out
          "
        >

          {/* =====================================================
              HEADER
          ===================================================== */}

          <div
            className="
              flex
              shrink-0
              items-center
              justify-between

              border-b
              border-slate-200
              bg-slate-50
              px-4
              py-4

              dark:border-slate-700
              dark:bg-slate-800
            "
          >

            {/* LEFT SIDE */}

            <div className="flex min-w-0 items-center gap-3">

              {/* AI ICON */}

              <div
                className="
                  flex
                  h-10
                  w-10
                  shrink-0
                  items-center
                  justify-center
                  rounded-xl

                  bg-blue-100
                  text-xl

                  dark:bg-blue-500/20
                "
              >
                🚦
              </div>

              {/* TITLE */}

              <div className="min-w-0">

                <div className="flex items-center gap-2">

                  <p
                    className="
                      truncate
                      text-sm
                      font-bold
                      uppercase
                      tracking-wide

                      text-slate-800

                      dark:text-slate-100
                    "
                  >
                    RoadSense AI
                  </p>

                  {/* ONLINE */}

                  <span
                    className="
                      flex
                      shrink-0
                      items-center
                      gap-1
                      rounded-full

                      bg-emerald-100
                      px-2
                      py-0.5

                      text-[9px]
                      font-semibold
                      text-emerald-600

                      dark:bg-emerald-500/15
                      dark:text-emerald-400
                    "
                  >

                    <span
                      className="
                        h-1.5
                        w-1.5
                        animate-pulse
                        rounded-full
                        bg-emerald-500

                        dark:bg-emerald-400
                      "
                    />

                    Online

                  </span>

                </div>

                <p
                  className="
                    mt-0.5
                    text-[11px]
                    text-slate-500

                    dark:text-slate-400
                  "
                >
                  Traffic Intelligence Assistant
                </p>

              </div>

            </div>

            {/* RIGHT SIDE BUTTONS */}

            <div className="flex shrink-0 items-center gap-1">

              {/* RESET */}

              <button
                onClick={handleReset}
                title="Restart conversation"
                className="
                  rounded-lg
                  px-2
                  py-1.5

                  text-[10px]
                  font-medium

                  text-slate-500
                  transition-colors

                  hover:bg-slate-200
                  hover:text-slate-800

                  dark:text-slate-400
                  dark:hover:bg-slate-700
                  dark:hover:text-slate-100
                "
              >
                Reset
              </button>

              {/* CLOSE */}

              <button
                onClick={() => setIsOpen(false)}
                className="
                  rounded-lg
                  p-1.5

                  text-slate-500
                  transition-colors

                  hover:bg-slate-200
                  hover:text-slate-800

                  dark:text-slate-400
                  dark:hover:bg-slate-700
                  dark:hover:text-slate-100
                "
                aria-label="Close chat"
              >
                ✕
              </button>

            </div>

          </div>

          {/* =====================================================
              MESSAGES AREA
          ===================================================== */}

          <div
            ref={scrollRef}
            className="
              flex-1
              space-y-3
              overflow-y-auto

              bg-white
              px-4
              py-4

              dark:bg-slate-900
            "
          >

            {/* CHAT MESSAGES */}

            {messages.map((m, idx) => (
              <ChatMessage
                key={idx}
                role={m.role}
                text={m.text}
                isError={m.isError}
              />
            ))}

            {/* STARTER QUESTIONS */}

            {messages.length === 1 && (
              <div className="mt-3 space-y-2 pt-1">

                <p
                  className="
                    text-[10px]
                    font-semibold
                    uppercase
                    tracking-wider

                    text-slate-400

                    dark:text-slate-500
                  "
                >
                  Suggested questions
                </p>

                <div className="flex flex-col gap-2">

                  {STARTER_QUESTIONS.map((question) => (
                    <button
                      key={question}
                      onClick={() => sendMessage(question)}
                      disabled={loading}
                      className="
                        rounded-xl
                        border

                        border-slate-200
                        bg-slate-50

                        px-3
                        py-2.5

                        text-left
                        text-xs
                        leading-5

                        text-slate-700
                        transition-all

                        hover:border-blue-300
                        hover:bg-blue-50
                        hover:text-blue-600

                        disabled:cursor-not-allowed
                        disabled:opacity-50

                        dark:border-slate-700
                        dark:bg-slate-800
                        dark:text-slate-300

                        dark:hover:border-blue-500/50
                        dark:hover:bg-blue-500/10
                        dark:hover:text-blue-400
                      "
                    >
                      {question}
                    </button>
                  ))}

                </div>

              </div>
            )}

            {/* THINKING INDICATOR */}

            {loading && (
              <div className="flex items-center gap-2">

                <div
                  className="
                    flex
                    h-7
                    items-center
                    gap-1.5
                    rounded-lg

                    bg-slate-100
                    px-3

                    text-[10px]
                    text-slate-500

                    dark:bg-slate-800
                    dark:text-slate-400
                  "
                >

                  <span
                    className="
                      h-1.5
                      w-1.5
                      animate-bounce
                      rounded-full
                      bg-slate-400
                    "
                  />

                  <span
                    className="
                      h-1.5
                      w-1.5
                      animate-bounce
                      rounded-full
                      bg-slate-400

                      [animation-delay:0.2s]
                    "
                  />

                  <span
                    className="
                      h-1.5
                      w-1.5
                      animate-bounce
                      rounded-full
                      bg-slate-400

                      [animation-delay:0.4s]
                    "
                  />

                  <span className="ml-1">
                    Thinking…
                  </span>

                </div>

              </div>
            )}

          </div>

          {/* =====================================================
              INPUT AREA
          ===================================================== */}

          <form
            onSubmit={handleSubmit}
            className="
              flex
              shrink-0
              items-center
              gap-2

              border-t
              border-slate-200

              bg-slate-50
              p-3

              dark:border-slate-700
              dark:bg-slate-800
            "
          >

            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about traffic..."
              disabled={loading}
              className="
                min-w-0
                flex-1

                rounded-xl
                border
                border-slate-200

                bg-white

                px-3
                py-2.5

                text-xs
                text-slate-800

                outline-none

                placeholder:text-slate-400

                focus:border-blue-500
                focus:ring-2
                focus:ring-blue-500/10

                dark:border-slate-600
                dark:bg-slate-900
                dark:text-slate-100
                dark:placeholder:text-slate-500
              "
            />

            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="
                shrink-0
                rounded-xl

                bg-blue-600
                px-3
                py-2.5

                text-xs
                font-semibold
                text-white

                transition-all

                hover:bg-blue-700

                disabled:cursor-not-allowed
                disabled:opacity-40
              "
            >
              Send
            </button>

          </form>

          {/* =====================================================
              FOOTER
          ===================================================== */}

          <div
            className="
              shrink-0

              border-t
              border-slate-200

              bg-white

              px-4
              py-2

              text-center
              text-[9px]
              text-slate-400

              dark:border-slate-800
              dark:bg-slate-950
              dark:text-slate-500
            "
          >
            {mode === 'groq'
              ? 'Powered by Groq · LangChain'
              : 'RoadSense AI Assistant'}
          </div>

        </div>
      )}

      {/* =========================================================
          FLOATING CHAT BUTTON
      ========================================================= */}

      <button
        onClick={() => setIsOpen((v) => !v)}
        className="
          fixed

          bottom-5
          right-5

          z-[60]

          flex
          h-12
          w-12

          items-center
          justify-center

          rounded-full

          bg-blue-600
          text-lg
          text-white

          shadow-xl

          transition-all
          duration-200

          hover:scale-105
          hover:bg-blue-700

          active:scale-95
        "
        aria-label="Toggle chat assistant"
      >
        {isOpen ? '✕' : '💬'}
      </button>

    </>
  );
}