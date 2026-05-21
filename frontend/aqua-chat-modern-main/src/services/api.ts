<<<<<<< HEAD
const API_URL = "/api";

export async function sendMessage(message: string) {
  const response = await fetch(`${API_URL}/chat`, {
=======
/**
 * api.ts — Frontend API client
 *
 * Uses a per-browser-session user ID so multiple demo visitors
 * don't share the same conversation context.
 *
 * In production (VITE_API_URL set), calls go directly to the backend.
 * In development, calls go through the Vite proxy (no CORS issues).
 */

// In production builds VITE_API_URL is set to the real backend URL.
// In dev mode we use an empty string so the Vite proxy handles routing.
const API_URL = import.meta.env.PROD
  ? (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "")
  : "";

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
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: message,
<<<<<<< HEAD
      user_id: "demo-user",
    }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Backend error (${response.status}): ${detail || response.statusText}`);
  }

  return response.json();
}

export async function clearChat(userId: string = "demo-user") {
  const response = await fetch(`${API_URL}/chat/clear`, {
=======
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
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
<<<<<<< HEAD
    body: JSON.stringify({ user_id: userId }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Backend error (${response.status}): ${detail || response.statusText}`);
  }

  return response.json();
=======
    body: JSON.stringify({ user_id: uid }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Backend error (${res.status}): ${detail || res.statusText}`);
  }

  return res.json();
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
}

export async function getChatUpdates(userId: string, after: number) {
  const params = new URLSearchParams({
    user_id: userId,
    after: String(after ?? 0),
  });

<<<<<<< HEAD
  const response = await fetch(`${API_URL}/chat/updates?${params.toString()}`);

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Backend error (${response.status}): ${detail || response.statusText}`);
  }

  return response.json();
=======
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
>>>>>>> 9a7f394 (Initial clean commit for capstone project)
}
