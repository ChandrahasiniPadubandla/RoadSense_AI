import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Thin, defensive wrapper around the browser Web Speech API
 * (SpeechRecognition / webkitSpeechRecognition).
 *
 *  - Works in Chrome, Edge and Safari. Firefox has no SpeechRecognition, so
 *    `supported` is false there and the UI falls back to typed input.
 *  - Needs a secure context (https:// or http://localhost) AND microphone
 *    permission. Opening the app through a plain-http LAN address such as
 *    http://192.168.x.x:5173 makes Chrome reject it with "not-allowed".
 *
 * The final transcript is delivered exactly once per session through
 * `onFinal(text)`; problems are reported through `onError(code)` using the
 * browser's own error codes ('not-allowed', 'no-speech', 'network', ...).
 */

function getRecognitionCtor() {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function isSpeechRecognitionSupported() {
  return Boolean(getRecognitionCtor());
}

/** Speak a short sentence aloud (best effort, silently ignored if unsupported). */
export function speak(text, lang = 'en-IN') {
  try {
    if (typeof window === 'undefined' || !('speechSynthesis' in window) || !text) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  } catch {
    /* speech output is a nicety, never a requirement */
  }
}

export function cancelSpeech() {
  try {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  } catch {
    /* ignore */
  }
}

export default function useSpeechRecognition({ lang = 'en-IN', onFinal, onError } = {}) {
  const supported = isSpeechRecognitionSupported();

  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');

  const recognitionRef = useRef(null);
  const latestTextRef = useRef('');
  const deliveredRef = useRef(false);

  // Keep the newest callbacks without re-creating start()/stop().
  const onFinalRef = useRef(onFinal);
  const onErrorRef = useRef(onError);
  useEffect(() => {
    onFinalRef.current = onFinal;
    onErrorRef.current = onError;
  });

  const deliver = useCallback(() => {
    if (deliveredRef.current) return;
    const text = latestTextRef.current.trim();
    if (!text) return;
    deliveredRef.current = true;
    onFinalRef.current?.(text);
  }, []);

  const start = useCallback(() => {
    const Ctor = getRecognitionCtor();
    if (!Ctor) {
      onErrorRef.current?.('unsupported');
      return;
    }

    // Never run two sessions at once.
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {
        /* ignore */
      }
    }

    const recognition = new Ctor();
    recognition.lang = lang;
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    latestTextRef.current = '';
    deliveredRef.current = false;
    setInterim('');

    recognition.onstart = () => setListening(true);

    recognition.onresult = (event) => {
      let finalText = '';
      let interimText = '';
      for (let i = 0; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) finalText += `${result[0].transcript} `;
        else interimText += result[0].transcript;
      }
      const combined = `${finalText}${interimText}`.trim();
      latestTextRef.current = combined;
      setInterim(combined);
    };

    recognition.onerror = (event) => {
      // 'aborted' is what we cause ourselves when cancelling — not a problem.
      if (event.error && event.error !== 'aborted') {
        onErrorRef.current?.(event.error);
      }
    };

    recognition.onend = () => {
      setListening(false);
      if (recognitionRef.current === recognition) recognitionRef.current = null;
      // Some browsers end the session without flagging the last chunk as
      // final, so we hand over whatever was heard.
      deliver();
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
    } catch (err) {
      setListening(false);
      onErrorRef.current?.(err?.name === 'InvalidStateError' ? 'busy' : 'start-failed');
    }
  }, [lang, deliver]);

  /** Stop listening but still process what was heard so far. */
  const stop = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      /* ignore */
    }
  }, []);

  /** Stop listening and throw the audio away. */
  const abort = useCallback(() => {
    deliveredRef.current = true;
    try {
      recognitionRef.current?.abort();
    } catch {
      /* ignore */
    }
    setListening(false);
    setInterim('');
  }, []);

  // Release the microphone if the page unmounts mid-session.
  useEffect(
    () => () => {
      deliveredRef.current = true;
      try {
        recognitionRef.current?.abort();
      } catch {
        /* ignore */
      }
      cancelSpeech();
    },
    []
  );

  return { supported, listening, interim, start, stop, abort };
}
