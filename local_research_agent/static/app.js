const REQUEST_HEADER = { "X-Requested-With": "LocalResearchAgent" };
const state = { modelMode: "offline", modelName: null, busy: false };

const elements = {
  modelBadge: document.querySelector("#model-badge"),
  privacyLabel: document.querySelector("#privacy-label"),
  documentCount: document.querySelector("#document-count"),
  documentList: document.querySelector("#document-list"),
  uploadTrigger: document.querySelector("#upload-trigger"),
  fileInput: document.querySelector("#file-input"),
  refreshDocuments: document.querySelector("#refresh-documents"),
  remoteNotice: document.querySelector("#remote-notice"),
  remoteConsentControl: document.querySelector("#remote-consent-control"),
  remoteConsent: document.querySelector("#remote-consent"),
  conversation: document.querySelector("#conversation"),
  welcomeState: document.querySelector("#welcome-state"),
  messageList: document.querySelector("#message-list"),
  clearChat: document.querySelector("#clear-chat"),
  askForm: document.querySelector("#ask-form"),
  question: document.querySelector("#question-input"),
  characterCount: document.querySelector("#character-count"),
  sendButton: document.querySelector("#send-button"),
  toast: document.querySelector("#toast"),
};

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : null;
  if (!response.ok) {
    const message = body && typeof body.detail === "string"
      ? body.detail
      : `Request failed (${response.status}).`;
    throw new Error(message);
  }
  return body;
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.classList.toggle("is-error", isError);
  elements.toast.classList.add("is-visible");
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => {
    elements.toast.classList.remove("is-visible");
  }, 3600);
}

function formatBytes(value) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(0)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function updateModelBadge(status) {
  state.modelMode = status.model_mode || "offline";
  state.modelName = status.model_name || null;
  elements.modelBadge.className = `model-badge mode-${state.modelMode}`;
  if (state.modelMode === "remote") {
    elements.modelBadge.textContent = `Remote model · ${state.modelName}`;
    elements.privacyLabel.textContent = "Remote sharing only with consent";
    elements.remoteNotice.hidden = false;
    elements.remoteConsentControl.hidden = false;
  } else if (state.modelMode === "local") {
    elements.modelBadge.textContent = `Local model · ${state.modelName}`;
    elements.privacyLabel.textContent = "Local data and model";
    elements.remoteNotice.hidden = true;
    elements.remoteConsentControl.hidden = true;
  } else {
    elements.modelBadge.textContent = "Offline evidence mode";
    elements.privacyLabel.textContent = "Your files stay on this machine";
    elements.remoteNotice.hidden = true;
    elements.remoteConsentControl.hidden = true;
  }
}

function createDocumentRow(documentInfo) {
  const row = document.createElement("article");
  row.className = "document-row";

  const icon = document.createElement("span");
  icon.className = "document-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = documentInfo.name.toLowerCase().endsWith(".md") ? "MD" : "TXT";

  const copy = document.createElement("span");
  copy.className = "document-copy";
  const name = document.createElement("strong");
  name.textContent = documentInfo.name;
  name.title = documentInfo.path;
  const meta = document.createElement("span");
  const lineText = Number.isInteger(documentInfo.lines) ? `${documentInfo.lines} lines` : "Text file";
  meta.textContent = `${lineText} · ${formatBytes(documentInfo.bytes)}`;
  copy.append(name, meta);

  const remove = document.createElement("button");
  remove.className = "remove-document";
  remove.type = "button";
  remove.setAttribute("aria-label", `Remove ${documentInfo.name}`);
  remove.title = "Remove this document";
  remove.textContent = "×";
  remove.addEventListener("click", () => removeDocument(documentInfo.path));

  row.append(icon, copy, remove);
  return row;
}

async function loadDocuments() {
  elements.documentList.replaceChildren();
  const loading = document.createElement("div");
  loading.className = "list-loading";
  loading.textContent = "Loading documents…";
  elements.documentList.append(loading);
  try {
    const documents = await requestJson("/api/documents");
    elements.documentList.replaceChildren();
    elements.documentCount.textContent = String(documents.length);
    if (documents.length === 0) {
      const empty = document.createElement("div");
      empty.className = "document-empty";
      empty.textContent = "No documents yet. Add a few notes to begin.";
      elements.documentList.append(empty);
      return;
    }
    for (const documentInfo of documents) {
      elements.documentList.append(createDocumentRow(documentInfo));
    }
  } catch (error) {
    elements.documentList.replaceChildren();
    const failed = document.createElement("div");
    failed.className = "document-empty is-error";
    failed.textContent = error.message;
    elements.documentList.append(failed);
  }
}

async function uploadSelectedFiles(fileList) {
  const files = Array.from(fileList || []);
  if (files.length === 0) return;
  const formData = new FormData();
  for (const file of files) formData.append("files", file, file.name);
  elements.uploadTrigger.disabled = true;
  elements.uploadTrigger.classList.add("is-loading");
  try {
    const added = await requestJson("/api/documents", {
      method: "POST",
      headers: REQUEST_HEADER,
      body: formData,
    });
    showToast(`Added ${added.length} document${added.length === 1 ? "" : "s"}.`);
    await loadDocuments();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    elements.uploadTrigger.disabled = false;
    elements.uploadTrigger.classList.remove("is-loading");
    elements.fileInput.value = "";
  }
}

async function removeDocument(path) {
  if (!window.confirm(`Remove “${path}” from this research workspace?`)) return;
  try {
    await requestJson(`/api/documents/${path.split("/").map(encodeURIComponent).join("/")}`, {
      method: "DELETE",
      headers: REQUEST_HEADER,
    });
    showToast("Document removed from this workspace.");
    await loadDocuments();
  } catch (error) {
    showToast(error.message, true);
  }
}

function addUserMessage(text) {
  const article = document.createElement("article");
  article.className = "message message-user";
  const avatar = document.createElement("span");
  avatar.className = "message-avatar user-avatar";
  avatar.textContent = "YOU";
  const content = document.createElement("div");
  content.className = "message-content";
  const heading = document.createElement("div");
  heading.className = "message-heading";
  heading.textContent = "Your question";
  const body = document.createElement("p");
  body.className = "message-text";
  body.textContent = text;
  content.append(heading, body);
  article.append(avatar, content);
  elements.messageList.append(article);
}

function createCitationCard(citation, index) {
  const card = document.createElement("article");
  card.className = "citation-card";
  const top = document.createElement("div");
  top.className = "citation-topline";
  const label = document.createElement("span");
  label.className = "citation-number";
  label.textContent = `[${index + 1}]`;
  const file = document.createElement("strong");
  file.textContent = citation.file;
  const lines = document.createElement("span");
  lines.className = "citation-lines";
  lines.textContent = `Lines ${citation.start_line}–${citation.end_line}`;
  top.append(label, file, lines);
  const quote = document.createElement("p");
  quote.className = "citation-quote";
  quote.textContent = citation.quote;
  card.append(top, quote);
  return card;
}

function createTrace(trace, stopReason) {
  const details = document.createElement("details");
  details.className = "trace-details";
  const summary = document.createElement("summary");
  summary.textContent = `Run trace · ${trace.length} tool step${trace.length === 1 ? "" : "s"} · ${stopReason}`;
  const list = document.createElement("ol");
  list.className = "trace-list";
  for (const item of trace) {
    const row = document.createElement("li");
    row.className = `trace-row trace-${item.status}`;
    const status = document.createElement("span");
    status.className = "trace-status";
    status.textContent = item.status;
    const detail = document.createElement("span");
    detail.textContent = `${item.tool}: ${item.detail}`;
    row.append(status, detail);
    list.append(row);
  }
  details.append(summary, list);
  return details;
}

function addAssistantMessage(response) {
  const article = document.createElement("article");
  article.className = "message message-assistant";
  const avatar = document.createElement("span");
  avatar.className = "message-avatar agent-avatar";
  avatar.textContent = "RA";
  const content = document.createElement("div");
  content.className = "message-content";
  const heading = document.createElement("div");
  heading.className = "message-heading";
  const title = document.createElement("strong");
  title.textContent = "Research result";
  const mode = document.createElement("span");
  mode.className = "response-mode";
  mode.textContent = response.model_mode === "offline"
    ? "Extractive · offline"
    : `${response.model_mode === "local" ? "Local" : "Remote"} model`;
  heading.append(title, mode);
  const answer = document.createElement("p");
  answer.className = "message-text answer-text";
  answer.textContent = response.answer;
  content.append(heading, answer);

  if (response.citations.length > 0) {
    const citationHeading = document.createElement("div");
    citationHeading.className = "section-kicker citation-heading";
    citationHeading.textContent = "VERIFIABLE SOURCES";
    const citationList = document.createElement("div");
    citationList.className = "citation-list";
    response.citations.forEach((citation, index) => {
      citationList.append(createCitationCard(citation, index));
    });
    content.append(citationHeading, citationList);
  }

  if (response.trace.length > 0) {
    content.append(createTrace(response.trace, response.stop_reason));
  }
  article.append(avatar, content);
  elements.messageList.append(article);
  article.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function addWorkingMessage() {
  const article = document.createElement("article");
  article.className = "message message-assistant working-message";
  article.id = "working-message";
  const avatar = document.createElement("span");
  avatar.className = "message-avatar agent-avatar";
  avatar.textContent = "RA";
  const content = document.createElement("div");
  content.className = "message-content";
  const heading = document.createElement("div");
  heading.className = "message-heading";
  heading.textContent = "Researching your library";
  const status = document.createElement("p");
  status.className = "working-copy";
  status.textContent = "Searching approved documents and checking the source lines…";
  content.append(heading, status);
  article.append(avatar, content);
  elements.messageList.append(article);
  article.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function setBusy(busy) {
  state.busy = busy;
  elements.sendButton.disabled = busy;
  elements.question.disabled = busy;
  elements.sendButton.querySelector("span").textContent = busy ? "Researching…" : "Research";
}

function resetConversation() {
  elements.messageList.replaceChildren();
  elements.welcomeState.hidden = false;
  elements.question.value = "";
  elements.characterCount.textContent = "0 / 1000";
  elements.remoteConsent.checked = false;
  elements.question.focus();
}

async function submitQuestion(event) {
  event.preventDefault();
  if (state.busy) return;
  const question = elements.question.value.trim();
  if (question.length < 3) {
    elements.question.focus();
    showToast("Enter a question with at least 3 characters.", true);
    return;
  }
  if (state.modelMode === "remote" && !elements.remoteConsent.checked) {
    showToast("Confirm remote processing before sending this question.", true);
    return;
  }

  elements.welcomeState.hidden = true;
  addUserMessage(question);
  elements.question.value = "";
  elements.characterCount.textContent = "0 / 1000";
  setBusy(true);
  addWorkingMessage();
  try {
    const response = await requestJson("/api/ask", {
      method: "POST",
      headers: { ...REQUEST_HEADER, "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        allow_remote_processing: state.modelMode === "remote" && elements.remoteConsent.checked,
      }),
    });
    document.querySelector("#working-message")?.remove();
    addAssistantMessage(response);
  } catch (error) {
    document.querySelector("#working-message")?.remove();
    const response = {
      answer: error.message,
      citations: [],
      trace: [],
      stop_reason: "request_error",
      model_mode: state.modelMode,
    };
    addAssistantMessage(response);
  } finally {
    setBusy(false);
    elements.remoteConsent.checked = false;
    elements.question.focus();
  }
}

async function loadHealth() {
  try {
    const status = await requestJson("/api/health");
    updateModelBadge(status);
  } catch (error) {
    elements.modelBadge.textContent = "Agent unavailable";
    elements.modelBadge.className = "model-badge mode-error";
    showToast(error.message, true);
  }
}

elements.uploadTrigger.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", () => uploadSelectedFiles(elements.fileInput.files));
elements.refreshDocuments.addEventListener("click", loadDocuments);
elements.askForm.addEventListener("submit", submitQuestion);
elements.clearChat.addEventListener("click", resetConversation);
elements.question.addEventListener("input", () => {
  elements.characterCount.textContent = `${elements.question.value.length} / 1000`;
});
elements.question.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.askForm.requestSubmit();
  }
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    elements.question.value = button.dataset.question || "";
    elements.characterCount.textContent = `${elements.question.value.length} / 1000`;
    elements.question.focus();
  });
});

for (const eventName of ["dragenter", "dragover"]) {
  elements.uploadTrigger.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.uploadTrigger.classList.add("is-dragging");
  });
}
for (const eventName of ["dragleave", "drop"]) {
  elements.uploadTrigger.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.uploadTrigger.classList.remove("is-dragging");
  });
}
elements.uploadTrigger.addEventListener("drop", (event) => {
  uploadSelectedFiles(event.dataTransfer?.files);
});

loadHealth();
loadDocuments();
