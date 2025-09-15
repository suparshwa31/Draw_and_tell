const BASE_URL = 'http://localhost:8000/parent';

export async function fetchSessions() {
  const res = await fetch(`${BASE_URL}/sessions`);
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

export async function fetchSession(sessionId) {
  const res = await fetch(`${BASE_URL}/session/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch session');
  return res.json();
}

export async function fetchRecap(sessionId) {
  const res = await fetch(`${BASE_URL}/recap/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch recap');
  return res.json();
}

export function imageUrl(drawingId) {
  return `${BASE_URL}/image/${drawingId}`;
}


