type Json = Record<string, unknown>;

async function readJson(response: Response): Promise<Json> {
  const data = (await response.json().catch(() => ({}))) as Json;
  if (!response.ok) {
    const message = typeof data.error === 'string' ? data.error : `Request failed (${response.status}).`;
    throw new Error(message);
  }
  return data;
}

export async function startSession(): Promise<{ session_id: string }> {
  const data = await readJson(await fetch('/api/session/start', { method: 'POST' }));
  return { session_id: String(data.session_id) };
}

export async function submitInitialText(sessionId: string, text: string): Promise<{ analysis_ready: boolean }> {
  const data = await readJson(await fetch('/api/input/text', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, text }),
  }));
  return { analysis_ready: Boolean(data.analysis_ready) };
}

export async function submitInitialMedia(
  sessionId: string,
  modality: 'AUDIO' | 'IMAGE' | 'CAMERA',
  media: Blob,
  filename: string,
): Promise<{ analysis_ready: boolean }> {
  const body = new FormData();
  body.append('session_id', sessionId);
  body.append('modality', modality);
  body.append('file', media, filename);
  const data = await readJson(await fetch('/api/input/ingest', { method: 'POST', body }));
  return { analysis_ready: Boolean(data.analysis_ready ?? data.ok) };
}

export async function completeInput(sessionId: string): Promise<void> {
  await readJson(await fetch('/api/session-lifecycle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, action: 'input_complete' }),
  }));
}

export async function sendChat(sessionId: string, message: string): Promise<{
  response: string;
  parrot_behavior?: string;
  closed?: boolean;
}> {
  const data = await readJson(await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  }));
  return {
    response: String(data.response ?? ''),
    parrot_behavior: typeof data.parrot_behavior === 'string' ? data.parrot_behavior : undefined,
    closed: Boolean(data.closed),
  };
}

export async function endConversation(sessionId: string): Promise<{
  cards: Array<{
    card_id: string;
    card_index: number;
    title: string;
    archetype?: string;
    qualitative_reading: string;
  }>;
}> {
  const data = await readJson(await fetch('/api/end-conversation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  }));
  const cards = Array.isArray(data.cards) ? data.cards : [];
  return {
    cards: cards.map((card) => {
      const row = card as Record<string, unknown>;
      return {
        card_id: String(row.card_id),
        card_index: Number(row.card_index),
        title: String(row.title ?? ''),
        archetype: typeof row.archetype === 'string' ? row.archetype : undefined,
        qualitative_reading: String(row.qualitative_reading ?? ''),
      };
    }),
  };
}

export async function advanceLifecycle(
  sessionId: string,
  action: string,
  extra: Record<string, unknown> = {},
): Promise<void> {
  await readJson(await fetch('/api/session-lifecycle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, action, ...extra }),
  }));
}

export async function generateOutput(sessionId: string): Promise<void> {
  const data = await readJson(await fetch('/api/session-output', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  }));
  if (data.success === false) {
    throw new Error(typeof data.error === 'string' ? data.error : 'Output failed.');
  }
}

export async function resetSession(sessionId: string, consentType: string): Promise<void> {
  await readJson(await fetch('/api/session-output-reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, consent_type: consentType }),
  }));
}
