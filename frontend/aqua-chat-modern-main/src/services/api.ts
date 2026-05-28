/**
 * api.ts — Frontend API client
 *
 * Uses a per-browser-session user ID so multiple demo visitors
 * don't share the same conversation context.
 *
 * In production (VITE_API_URL set), calls go directly to the backend.
 * In development, calls go through the Vite proxy (no CORS issues).
 */

// In production builds VITE_API_URL is set to the real backend URL if remote.
// If VITE_API_URL is localhost or missing, we use an empty string in production so same-origin relative paths are used.
// In dev mode we use an empty string so the Vite proxy handles routing.
const API_URL = (() => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && !envUrl.includes("127.0.0.1") && !envUrl.includes("localhost")) {
    return envUrl.replace(/\/$/, "");
  }
  return "";
})();


/**
 * Returns a stable, per-browser-session user ID.
 * Stored in sessionStorage so each browser tab gets its own conversation.
 * Survives page refreshes within the same tab but resets on new tabs.
 */
export function getSessionUserId(): string {
  let id = sessionStorage.getItem("chat_user_id");
  if (!id) {
    const rand = crypto.randomUUID
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
    id = `demo-${rand}`;
    sessionStorage.setItem("chat_user_id", id);
  }
  return id;
}

export async function sendMessage(message: string, userId?: string) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: message,
      user_id: userId ?? getSessionUserId(),
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Backend error (${res.status}): ${detail || res.statusText}`);
  }

  return res.json();
}

export async function clearChat(userId?: string) {
  const uid = userId ?? getSessionUserId();
  const res = await fetch(`${API_URL}/chat/clear`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_id: uid }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Backend error (${res.status}): ${detail || res.statusText}`);
  }

  return res.json();
}

export async function getChatUpdates(userId: string, after: number) {
  const params = new URLSearchParams({
    user_id: userId,
    after: String(after ?? 0),
  });

  const res = await fetch(`${API_URL}/chat/updates?${params.toString()}`);

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Backend error (${res.status}): ${detail || res.statusText}`);
  }

  return res.json();
}

export async function submitFeedback({
  sessionId,
  userId,
  rating,
  textFeedback,
}: {
  sessionId: string;
  userId?: string;
  rating: number;
  textFeedback?: string;
}) {
  const res = await fetch(`${API_URL}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: sessionId,
      user_id: userId ?? getSessionUserId(),
      rating,
      text_feedback: textFeedback || null,
      helpful: rating >= 4,
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Backend error (${res.status}): ${detail || res.statusText}`);
  }

  return res.json();
}
