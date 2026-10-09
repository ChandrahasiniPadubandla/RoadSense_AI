import React, { useCallback, useEffect, useRef, useState } from 'react';
import useSpeechRecognition, { speak, cancelSpeech } from '../hooks/useSpeechRecognition';
import { extractRouteFromVoice, getVoiceStatus } from '../api_services';

/**
 * Voice assistant for route queries.
 *
 *   mic  ->  browser speech-to-text  ->  database-backed route resolution
 *        ->  onRoute({ success, start_location, end_location, ... })
 *
 * The parent page decides what to do with the result (fill its form, draw a
 * route, run a prediction...). `onRoute` is called whenever at least one
 * location was understood; check `result.success` to know if BOTH were found.
 *
 * Props
 *   onRoute(result)  required – receives the VoiceRouteExtractResponse
 *   hint             example phrase shown while idle
 *   compact          tighter layout (used inside the Live Map panel)
 *   disabled         disable the mic (e.g. while a request is running)
 */

const ERROR_MESSAGES = {
  'no-speech': "I didn't hear anything. Tap the mic and try again.",
  'audio-capture': 'No microphone was found on this device.',
  network: 'Speech recognition needs an internet connection.',
  'language-not-supported': 'This browser does not support the selected speech language.',
  busy: 'The microphone is already in use. Try again in a moment.',
  'start-failed': 'Could not start the microphone. Please try again.',
};

function describeSpeechError(code) {
  if (code === 'not-allowed' || code === 'service-not-allowed') {
    if (typeof window !== 'undefined' && window.isSecureContext === false) {
      return 'The microphone needs a secure page. Open the app via https:// or http://localhost (a plain http:// IP address is blocked by the browser).';
    }
    return "Microphone access was blocked. Allow it from the browser's address bar and try again.";
  }
  return ERROR_MESSAGES[code] || 'Voice input failed. Please try again.';
}

function MicIcon({ className = 'h-5 w-5' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 18v3" />
    </svg>
  );
}

function SpeakerIcon({ muted, className = 'h-4 w-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M11 5 6 9H3v6h3l5 4V5z" />
      {muted ? (
        <>
          <path d="m16 9 5 6" />
          <path d="m21 9-5 6" />
        </>
      ) : (
        <>
          <path d="M15.5 8.5a5 5 0 0 1 0 7" />
          <path d="M18.5 5.5a9 9 0 0 1 0 13" />
        </>
      )}
    </svg>
  );
}

function KeyboardIcon({ className = 'h-4 w-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10" />
    </svg>
  );
}

export default function VoiceAssistant({
  onRoute,
  hint = 'Try: “Traffic from Uppal to Nagole”',
  compact = false,
  disabled = false,
}) {
  const [phase, setPhase] = useState('idle'); // 'idle' | 'listening' | 'processing'
  const [heard, setHeard] = useState('');
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error' | 'info', text }
  const [service, setService] = useState(null); // { online, resolverReady } | null while checking
  const [liveResolution, setLiveResolution] = useState(null);
  const [liveResolutionError, setLiveResolutionError] = useState('');
  const [spokenReplies, setSpokenReplies] = useState(true);
  const [showTyped, setShowTyped] = useState(false);
  const [typed, setTyped] = useState('');

  const onRouteRef = useRef(onRoute);
  const spokenRef = useRef(spokenReplies);
  const mountedRef = useRef(true);
  const requestSequenceRef = useRef(0);
  const liveRequestTimerRef = useRef(null);

  useEffect(() => {
    onRouteRef.current = onRoute;
    spokenRef.current = spokenReplies;
  });

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Ask the backend whether the database-backed resolver is available.
  useEffect(() => {
    let cancelled = false;
    getVoiceStatus().then((s) => {
      if (cancelled) return;
      setService({
        online: s?.status === 'online',
        resolverReady: Boolean(s?.resolver_ready),
      });
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const reply = useCallback((text) => {
    if (spokenRef.current) speak(text);
  }, []);

  // Send the transcript to the backend and hand the result to the page.
  const processTranscript = useCallback(
    async (text) => {
      const clean = (text || '').trim();
      if (!clean) return;

      setHeard(clean);
      setFeedback(null);
      setPhase('processing');
      requestSequenceRef.current += 1;
      clearTimeout(liveRequestTimerRef.current);
      setLiveResolutionError('');

      try {
        const result = await extractRouteFromVoice(clean);
        if (!mountedRef.current) return;
        setLiveResolution(result);

        if (result?.success) {
          const line = `${result.start_location} → ${result.end_location}`;
          setFeedback({ type: 'success', text: `Got it: ${line}` });
          reply(`Got it. From ${result.start_location} to ${result.end_location}.`);
        } else {
          const hasEmptyOrUnmatchedLocation = [
            result?.start_status,
            result?.end_status,
          ].some((status) => status === 'empty' || status === 'not_found');
          const msg = hasEmptyOrUnmatchedLocation
            ? 'Say an origin and destination that match the available locations.'
            : result?.message || 'Choose the matching locations from the suggestions.';
          setFeedback({ type: 'info', text: msg });
          reply("Sorry, I couldn't catch both locations. Please try again.");
        }

        if (result && (result.start_location || result.end_location)) {
          onRouteRef.current?.(result);
        }
      } catch (err) {
        if (!mountedRef.current) return;
        console.error('Voice extraction failed:', err);
        const detail = err?.response?.data?.detail;
        setFeedback({
          type: 'error',
          text: err?.request && !err?.response
            ? 'Cannot reach the voice service. Check that the backend is running.'
            : (typeof detail === 'string' ? detail : 'The voice service could not process that. Please try again.'),
        });
      } finally {
        if (mountedRef.current) setPhase('idle');
      }
    },
    [reply]
  );

  const handleSpeechError = useCallback((code) => {
    if (!mountedRef.current) return;
    setPhase('idle');
    setFeedback({ type: 'error', text: describeSpeechError(code) });
    if (code === 'unsupported') setShowTyped(true);
  }, []);

  const { supported, listening, interim, start, stop } = useSpeechRecognition({
    lang: 'en-IN',
    onFinal: processTranscript,
    onError: handleSpeechError,
  });

  useEffect(() => {
    const transcript = interim.trim();
    if (!listening || !transcript) return undefined;

    const requestSequence = ++requestSequenceRef.current;
    clearTimeout(liveRequestTimerRef.current);
    liveRequestTimerRef.current = setTimeout(async () => {
      try {
        const result = await extractRouteFromVoice(transcript);
        if (!mountedRef.current || requestSequence !== requestSequenceRef.current) return;
        setLiveResolution(result);
        setLiveResolutionError('');
      } catch (error) {
        if (!mountedRef.current || requestSequence !== requestSequenceRef.current) return;
        console.warn('Live voice location resolution failed:', error);
        setLiveResolutionError('Live database matching is unavailable. The final transcript will be checked again.');
      }
    }, 350);

    return () => clearTimeout(liveRequestTimerRef.current);
  }, [interim, listening]);

  // Keep the visual phase in sync with the recogniser.
  useEffect(() => {
    if (listening) setPhase('listening');
    else setPhase((p) => (p === 'listening' ? 'idle' : p));
  }, [listening]);

  function handleMicClick() {
    if (disabled || phase === 'processing') return;
    if (listening) {
      stop();
      return;
    }
    cancelSpeech();
    setFeedback(null);
    setHeard('');
    setLiveResolution(null);
    setLiveResolutionError('');
    requestSequenceRef.current += 1;
    start();
  }

  function handleTypedSubmit() {
    if (disabled || phase === 'processing') return;
    const text = typed.trim();
    if (!text) return;
    processTranscript(text);
    setTyped('');
  }

  function applySuggestion(field, candidate) {
    if (!liveResolution || !candidate) return;
    const isStart = field === 'start_location';
    const updated = {
      ...liveResolution,
      [field]: candidate.name,
      [isStart ? 'start_status' : 'end_status']: 'matched',
      [isStart ? 'start_matches' : 'end_matches']: [candidate],
    };
    updated.success = Boolean(updated.start_location && updated.end_location);
    updated.method = 'database';
    setLiveResolution(updated);
    setFeedback({
      type: updated.success ? 'success' : 'info',
      text: updated.success
        ? `Verified route: ${updated.start_location} → ${updated.end_location}`
        : `${isStart ? 'Origin' : 'Destination'} selected from the database: ${candidate.name}`,
    });
    onRouteRef.current?.(updated);
  }

  const isListening = phase === 'listening';
  const isProcessing = phase === 'processing';

  let statusLine = hint;
  if (isListening) statusLine = interim || 'Listening… speak now';
  else if (isProcessing) statusLine = heard ? `Understanding “${heard}”` : 'Understanding…';
  else if (heard) statusLine = `Heard: “${heard}”`;

  let serviceDot = 'bg-slate-300 dark:bg-asphalt-600';
  let serviceTitle = 'Checking voice service…';
  if (service) {
    if (!service.online) {
      serviceDot = 'bg-signal-red';
      serviceTitle = 'Voice service offline';
    } else if (service.resolverReady) {
      serviceDot = 'bg-signal-green';
      serviceTitle = 'Database location resolver ready';
    } else {
      serviceDot = 'bg-signal-amber';
      serviceTitle = 'Voice service online; database resolver unavailable';
    }
  }

  const hasVisibleLocationResults = liveResolution && ['start', 'end'].some((side) => {
    return (liveResolution[side === 'start' ? 'start_matches' : 'end_matches'] || []).length > 0;
  });

  const iconBtn =
    'flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-200/70 hover:text-slate-800 dark:text-asphalt-400 dark:hover:bg-asphalt-700 dark:hover:text-asphalt-100';

  return (
    <div
      className={`rounded-lg border border-slate-200 bg-slate-50 dark:border-asphalt-700 dark:bg-asphalt-800/60 ${
        compact ? 'p-2' : 'p-3'
      } ${compact ? '' : 'mb-5'}`}
    >
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleMicClick}
          disabled={disabled || isProcessing}
          aria-pressed={isListening}
          aria-label={isListening ? 'Stop listening' : 'Start voice input'}
          title={supported ? (isListening ? 'Tap to stop' : 'Tap and speak') : 'Voice input is not supported in this browser — use the keyboard option'}
          className={`relative flex shrink-0 items-center justify-center rounded-full text-white shadow transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
            compact ? 'h-9 w-9' : 'h-11 w-11'
          } ${isListening ? 'bg-signal-red' : 'bg-signal-blue hover:opacity-90'}`}
        >
          {isListening && <span className="absolute inset-0 animate-ping rounded-full bg-signal-red/40" />}
          <MicIcon className="relative h-5 w-5" />
        </button>

        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-slate-900 dark:text-asphalt-100">
            Voice assistant
            <span className={`inline-block h-2 w-2 rounded-full ${serviceDot}`} title={serviceTitle} aria-label={serviceTitle} />
          </p>
          <p className="truncate text-[11px] text-slate-500 dark:text-asphalt-400" aria-live="polite" title={statusLine}>
            {isProcessing && <span className="mr-1 inline-block animate-pulse">●</span>}
            {statusLine}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowTyped((v) => !v)}
          className={iconBtn}
          aria-label="Type instead of speaking"
          title="Type instead of speaking"
          aria-pressed={showTyped}
        >
          <KeyboardIcon />
        </button>
        <button
          type="button"
          onClick={() => {
            setSpokenReplies((v) => !v);
            cancelSpeech();
          }}
          className={iconBtn}
          aria-label={spokenReplies ? 'Mute spoken replies' : 'Unmute spoken replies'}
          title={spokenReplies ? 'Spoken replies on' : 'Spoken replies off'}
          aria-pressed={spokenReplies}
        >
          <SpeakerIcon muted={!spokenReplies} />
        </button>
      </div>

      {showTyped && (
        <div className="mt-2 flex gap-2">
          <input
            type="text"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleTypedSubmit();
              }
            }}
            placeholder="e.g. traffic from Uppal to Nagole"
            className="min-w-0 flex-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 outline-none focus:border-signal-blue dark:border-asphalt-600 dark:bg-asphalt-900 dark:text-asphalt-100"
          />
          <button
            type="button"
            onClick={handleTypedSubmit}
            disabled={disabled || isProcessing || !typed.trim()}
            className="rounded-md bg-signal-blue px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            Go
          </button>
        </div>
      )}

      {(hasVisibleLocationResults || liveResolutionError) && (
        <div className="mt-2 rounded-md border border-slate-200 bg-white px-2.5 py-2 text-[11px] dark:border-asphalt-700 dark:bg-asphalt-900">
          <p className="mb-1 font-semibold text-slate-700 dark:text-asphalt-200">
            {isListening ? 'Live database matches' : 'Database location results'}
          </p>
          {liveResolutionError && (
            <p role="status" className="mb-1 text-signal-amber">{liveResolutionError}</p>
          )}
          {liveResolution && ['start', 'end'].map((side) => {
            const isStart = side === 'start';
            const field = isStart ? 'start_location' : 'end_location';
            const statusField = isStart ? 'start_status' : 'end_status';
            const matchesField = isStart ? 'start_matches' : 'end_matches';
            const label = isStart ? 'Origin' : 'Destination';
            const location = liveResolution[field];
            const matches = liveResolution[matchesField] || [];
            const matchStatus = liveResolution[statusField];

            if (!matches.length) {
              return null;
            }

            const verifiedMatch =
              matchStatus === 'matched' &&
              typeof location === 'string' &&
              location.trim() !== '' &&
              matches.some((candidate) => candidate.name === location);

            return (
              <div key={side} className="mb-1 last:mb-0">
                {verifiedMatch ? (
                  <p className="text-signal-green">
                    {label}: <strong>{location}</strong> <span>(verified in database)</span>
                  </p>
                ) : matches.length > 0 ? (
                  <div>
                    <p className="text-slate-600 dark:text-asphalt-300">
                      {matchStatus === 'ambiguous'
                        ? `Several ${label.toLowerCase()} matches; choose one:`
                        : `No confident ${label.toLowerCase()} match; suggestions:`}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {matches.map((candidate) => (
                        <button
                          key={`${side}-${candidate.name}`}
                          type="button"
                          onClick={() => applySuggestion(field, candidate)}
                          className="rounded border border-signal-blue/40 px-2 py-1 text-signal-blue hover:bg-signal-blue/10"
                          title={`${candidate.source} · ${Math.round(candidate.score * 100)}% match`}
                        >
                          {candidate.name}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      {!supported && !showTyped && (
        <p className="mt-2 text-[11px] text-signal-amber">
          This browser has no speech recognition. Use the keyboard icon to type your request, or open the app in Chrome / Edge.
        </p>
      )}

      {feedback && (
        <p
          role={feedback.type === 'error' ? 'alert' : 'status'}
          className={`mt-2 rounded-md border px-2.5 py-1.5 text-[11px] ${
            feedback.type === 'success'
              ? 'border-signal-green/40 bg-signal-green/10 text-signal-green'
              : feedback.type === 'error'
              ? 'border-signal-red/40 bg-signal-red/10 text-signal-red'
              : 'border-slate-200 bg-white text-slate-600 dark:border-asphalt-700 dark:bg-asphalt-900 dark:text-asphalt-300'
          }`}
        >
          {feedback.text}
        </p>
      )}
    </div>
  );
}
