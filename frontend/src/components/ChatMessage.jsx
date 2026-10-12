import React from 'react';

export default function ChatMessage({ role, text, isError }) {
  const isUser = role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
          isUser
            ? 'bg-signal-blue text-white'
            : isError
            ? 'border border-signal-red/40 bg-signal-red/10 text-signal-red'
            : 'bg-asphalt-800 text-asphalt-100'
        }`}
      >
        {text}
      </div>
    </div>
  );
}
