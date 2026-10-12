import React from 'react';

export default function ChatMessage({ role, text, isError }) {
  const isUser = role === 'user';

  return (
    <div
      className={`flex ${
        isUser ? 'justify-end' : 'justify-start'
      }`}
    >
      <div
        className={`
          max-w-[88%]
          rounded-xl
          px-3
          py-2
          text-[11px]
          leading-relaxed
          shadow-sm

          ${
            isUser
              ? `
                bg-blue-600
                text-white
                dark:bg-blue-600
                dark:text-white
              `
              : isError
              ? `
                border
                border-red-200
                bg-red-50
                text-red-600

                dark:border-red-500/30
                dark:bg-red-500/10
                dark:text-red-400
              `
              : `
                border
                border-slate-200
                bg-slate-100
                text-slate-700

                dark:border-slate-700
                dark:bg-slate-800
                dark:text-slate-200
              `
          }
        `}
      >
        {text}
      </div>
    </div>
  );
}