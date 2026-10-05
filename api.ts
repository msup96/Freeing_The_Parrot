export interface FtpSessionStart {
    ok: boolean;
    session_id: string;
    state: string;
    analysis_ready: boolean;
  }
  
  export interface FtpChatResult {
    response: string;
    parrot_behavior?: string;
    closed?: boolean;
    [key: string]: unknown;
  }
  
  async function request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(path, options);
    const text = await response.text();
  
    let body: (T & { error?: string }) | null = null;
    if (text) {
      const trimmed = text.trim();
      const looksLikeJson = trimmed.startsWith("{") || trimmed.startsWith("[");
      if (looksLikeJson || response.headers.get("content-type")?.includes("application/json")) {
        try {
          body = JSON.parse(text) as T & { error?: string };
        } catch {
          throw new Error(`Unexpected JSON response from ${path}: ${trimmed.slice(0, 120)}`);
        }
      }
    }
  
    if (!response.ok) {
      const message = typeof body === "object" && body && "error" in body
        ? String(body.error)
        : text || `FTP request failed: ${response.status}`;
      throw new Error(message);
    }
  
    return body ?? ({} as T);
  }
  
  export function startSession(): Promise<FtpSessionStart> {
    return request<FtpSessionStart>("/api/session/start", { method: "POST" });
  }
  
  export function submitInitialText(sessionId: string, text: string) {
    return request<{ analysis_ready: boolean; state: string }>("/api/input/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, text }),
    });
  }
  
  export function submitInitialMedia(
    sessionId: string,
    modality: "AUDIO" | "IMAGE" | "CAMERA",
    media: Blob,
    filename: string,
  ) {
    const form = new FormData();
    form.append("session_id", sessionId);
    form.append("modality", modality);
    form.append("file", media, filename);
    return request<{ analysis_ready: boolean; state: string }>("/api/input/ingest", {
      method: "POST",
      body: form,
    });
  }
  
  export function completeInput(sessionId: string) {
    return request<{ lifecycle_state: string }>("/api/session-lifecycle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, action: "input_complete" }),
    });
  }
  
  export function sendChat(sessionId: string, message: string): Promise<FtpChatResult> {
    return request<FtpChatResult>("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  }
  
  export function endConversation(sessionId: string) {
    return request<{ lifecycle_state: string; closed: boolean }>("/api/end-conversation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
  }
  
  export function advanceLifecycle(sessionId: string, action: string, extra = {}) {
    return request<{ lifecycle_state: string }>("/api/session-lifecycle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, action, ...extra }),
    });
  }
  
  export function generateOutput(sessionId: string) {
    return request<{ success: boolean }>("/api/session-output", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });
  }
  
  export function resetSession(sessionId: string, consentType: "SHARE" | "KEEP_PRIVATE") {
    return request<{ lifecycle_state: string }>("/api/session-output-reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, consent_type: consentType }),
    });
  }