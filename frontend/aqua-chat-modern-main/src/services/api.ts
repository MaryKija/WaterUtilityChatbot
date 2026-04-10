const API_URL = "/api";

export async function sendMessage(message: string) {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: message,
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
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_id: userId }),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Backend error (${response.status}): ${detail || response.statusText}`);
  }

  return response.json();
}

export async function getChatUpdates(userId: string, after: number) {
  const params = new URLSearchParams({
    user_id: userId,
    after: String(after ?? 0),
  });

  const response = await fetch(`${API_URL}/chat/updates?${params.toString()}`);

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Backend error (${response.status}): ${detail || response.statusText}`);
  }

  return response.json();
}
