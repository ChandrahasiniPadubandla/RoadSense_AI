import React from 'react';
import { Link } from 'react-router-dom';

const MARKDOWN_LINK_PATTERN = /\[([^\]]+)\]\(([^)]+)\)/g;

function renderMessageText(text) {
  const parts = [];
  let lastIndex = 0;
  for (const match of text.matchAll(MARKDOWN_LINK_PATTERN)) {
    const [markdown, label, urlText] = match;
    const index = match.index ?? 0;
    parts.push(text.slice(lastIndex, index));
    let url;

    try {
      url = new URL(urlText, window.location.origin);
    } catch {
      parts.push(markdown);
      lastIndex = index + markdown.length;
      continue;
    }

    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      parts.push(markdown);
      lastIndex = index + markdown.length;
      continue;
    }

    const isInternal = url.origin === window.location.origin;
    const href = isInternal
      ? `${url.pathname}${url.search}${url.hash}`
      : url.href;
    const className = 'font-semibold text-blue-600 underline underline-offset-2 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300';

    parts.push(isInternal ? (
      <Link key={index} to={href} className={className}>
        {label}
      </Link>
    ) : (
      <a
        key={index}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={className}
      >
        {label}
      </a>
    ));
    lastIndex = index + markdown.length;
  }

  parts.push(text.slice(lastIndex));
  return parts;
}

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
        <span className="whitespace-pre-wrap">{renderMessageText(text)}</span>
      </div>
    </div>
  );
}