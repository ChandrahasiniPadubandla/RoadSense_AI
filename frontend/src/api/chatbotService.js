import axiosClient, { USE_MOCK_DATA } from './axiosClient';

// -----------------------------------------------------------------------
// Contract expected from the backend (see chatbot-backend-reference/ for a
// working LangChain implementation of this exact endpoint):
//
//   POST /chatbot/query
//   body: { message: string, session_id: string }
//   -> 200 { reply: string, sources?: string[] }
//
// session_id groups a conversation so the backend (LangChain memory) can
// keep context across turns. We generate one per browser tab and keep it
// in sessionStorage — swap for a per-login session id if you want history
// tied to the logged-in user instead.
// -----------------------------------------------------------------------

function getSessionId() {
  let id = sessionStorage.getItem('chatbotSessionId');
  if (!id) {
    id = `sess-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem('chatbotSessionId', id);
  }
  return id;
}

function fakeDelay(ms = 600) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Very small canned-response mock so the widget is testable with no backend yet. */
function mockReply(message) {
  const lower = message.toLowerCase();
  if (lower.includes('accident') && lower.includes('risk')) {
    return "The highest accident risk right now is on PV Narasimha Rao Expressway at 89%, driven by heavy rainfall and high average speed. You can see the full breakdown on the Accident Risk Prediction page.";
  }
  if (lower.includes('congestion') || lower.includes('traffic')) {
    return "NH-44 and PV Narasimha Rao Expressway are both showing HIGH to SEVERE congestion right now. A prediction model expects that to peak between 17:30 and 19:00.";
  }
  if (lower.includes('hotspot')) {
    return "Junction A on NH-44 is the top accident hotspot with 43 recorded accidents, followed by PVNR Expressway KM 12 with 27.";
  }
  return "I can help with traffic conditions, congestion predictions, accident risk, and hotspots for this system. Try asking something like \"what's the accident risk on the expressway right now?\"";
}

/** POST /chatbot/query -> { reply, sources } */
export async function sendMessage(message) {
  const sessionId = getSessionId();

  if (USE_MOCK_DATA) {
    await fakeDelay();
    return { reply: mockReply(message), sources: [] };
  }

  const { data } = await axiosClient.post('/chatbot/query', {
    message,
    session_id: sessionId,
  });
  return data; // { reply, sources }
}

/** Optional: POST /chatbot/reset to clear server-side memory for this tab's session. */
export async function resetConversation() {
  const sessionId = getSessionId();
  sessionStorage.removeItem('chatbotSessionId');
  if (USE_MOCK_DATA) return;
  try {
    await axiosClient.post('/chatbot/reset', { session_id: sessionId });
  } catch {
    // non-fatal — a fresh session_id will be generated on next message anyway
  }
}
