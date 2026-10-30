// Keep transport details and backend diagnostics out of the UI.
// Components receive short, user-facing messages from this module only.

const MAX_DOCUMENT_BYTES = 200_000; // The backend remains the source of truth.
const ERROR_MESSAGES = {
  invalid_request: "We couldn't process that input. Check the document and question, then try again.",
  payload_too_large: "This document is too large. Please use a file smaller than 200 KB.",
  session_not_found: "This document session has expired. Upload the document again to continue.",
  provider_rate_limited: "The AI service is receiving too many requests. Wait a minute, then try again.",
  provider_error: "The AI service couldn't complete that request. Please try again in a moment.",
  internal_error: "Something went wrong while processing your request. Please try again.",
};

function messageForFailure(status, code) {
  if (code && ERROR_MESSAGES[code]) return ERROR_MESSAGES[code];

  // Fall back to status-based copy for framework/proxy errors that do not use
  // the application's JSON error envelope. Never display their raw body.
  if (status === 400) return "Some of the information is missing or invalid. Check your input and try again.";
  if (status === 404) return "The requested document session could not be found. Upload your document again.";
  if (status === 413) return "This document is too large. Please use a file smaller than 200 KB.";
  if (status === 429) return "The AI service is busy. Wait a moment, then try again.";
  if (status >= 500) return "The server or AI service is temporarily unavailable. Please try again shortly.";
  return "We couldn't complete that request. Please check your input and try again.";
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("Couldn't connect to Docwise. Check that the backend is running and try again.");
  }
  if (response.status === 204) return null;

  // A proxy or an unhandled framework response may not be JSON. Parse only
  // the structured error code; never render arbitrary server response text.
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const code = typeof body?.error?.code === "string" ? body.error.code : null;
    throw new Error(messageForFailure(response.status, code));
  }
  if (!body || typeof body !== "object") {
    throw new Error("The server returned an unexpected response. Please try again.");
  }
  return body;
}

/** Submit pasted text OR a .txt/.md file. Returns { sessionId, chunkCount }. */
export function submitDocument({ text, file }) {
  if (file && file.size > MAX_DOCUMENT_BYTES) {
    return Promise.reject(new Error("This file is larger than 200 KB. Choose a smaller TXT or MD file."));
  }
  if (file && !/\.(txt|md)$/i.test(file.name)) {
    return Promise.reject(new Error("Choose a plain-text .txt or Markdown .md file."));
  }
  if (!file && !text?.trim()) {
    return Promise.reject(new Error("Paste some text or choose a document before continuing."));
  }

  const form = new FormData();
  if (file) form.append("file", file);
  else form.append("text", text);
  return request("/api/documents", { method: "POST", body: form });
}

/** Ask a question about an existing session. Returns { answer, sources }. */
export function askQuestion(sessionId, question) {
  if (!sessionId) {
    return Promise.reject(new Error("Your document session is missing. Upload the document again."));
  }
  if (!question?.trim()) {
    return Promise.reject(new Error("Enter a question before submitting."));
  }
  return request("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId, question: question.trim() }),
  });
}

export function deleteSession(sessionId) {
  return request(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
}
