const state = {
  authHeader: "",
  username: "",
  currentScreen: "homeScreen",
  currentAnalysisId: "",
  currentAnalysis: null,
  handoff: null,
  analyses: [],
  requests: [],
  jobs: []
};

const loginScreen = document.getElementById("loginScreen");
const authenticatedShell = document.getElementById("authenticatedShell");
const loginForm = document.getElementById("loginForm");
const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const loginStatus = document.getElementById("loginStatus");
const refreshHomeBtn = document.getElementById("refreshHomeBtn");
const refreshRequestsBtn = document.getElementById("refreshRequestsBtn");
const refreshJobsBtn = document.getElementById("refreshJobsBtn");
const homeNewIntakeBtn = document.getElementById("homeNewIntakeBtn");
const homeResumeLatestBtn = document.getElementById("homeResumeLatestBtn");
const newDraftBtn = document.getElementById("newDraftBtn");
const intakeForm = document.getElementById("intakeForm");
const saveDraftBtn = document.getElementById("saveDraftBtn");
const uploadScreenshotsBtn = document.getElementById("uploadScreenshotsBtn");
const createQuoteDraftBtn = document.getElementById("createQuoteDraftBtn");
const prepareHandoffBtn = document.getElementById("prepareHandoffBtn");
const intakeStatus = document.getElementById("intakeStatus");
const uploadStatus = document.getElementById("uploadStatus");
const handoffStatus = document.getElementById("handoffStatus");
const currentDraftMeta = document.getElementById("currentDraftMeta");
const draftLockNotice = document.getElementById("draftLockNotice");
const recentDraftsList = document.getElementById("recentDraftsList");
const requestsList = document.getElementById("requestsList");
const jobsList = document.getElementById("jobsList");
const ocrReviewBox = document.getElementById("ocrReviewBox");
const extractedDetailsBox = document.getElementById("extractedDetailsBox");
const quoteGuidanceBox = document.getElementById("quoteGuidanceBox");
const draftCount = document.getElementById("draftCount");
const requestCount = document.getElementById("requestCount");
const upcomingCount = document.getElementById("upcomingCount");
const navButtons = Array.from(document.querySelectorAll(".navButton"));
const appScreens = Array.from(document.querySelectorAll(".appScreen"));

const fields = {
  username: document.getElementById("mobileAdminUsername"),
  password: document.getElementById("mobileAdminPassword"),
  message: document.getElementById("intakeMessage"),
  customerName: document.getElementById("intakeCustomerName"),
  customerPhone: document.getElementById("intakeCustomerPhone"),
  description: document.getElementById("intakeDescription"),
  requestedDate: document.getElementById("intakeRequestedDate"),
  requestedWindow: document.getElementById("intakeRequestedWindow"),
  serviceType: document.getElementById("intakeServiceType"),
  jobAddress: document.getElementById("intakeJobAddress"),
  estimatedHours: document.getElementById("intakeEstimatedHours"),
  crewSize: document.getElementById("intakeCrewSize"),
  pickupAddress: document.getElementById("intakePickupAddress"),
  dropoffAddress: document.getElementById("intakeDropoffAddress"),
  files: document.getElementById("intakeScreenshotFiles"),
  responseDraft: document.getElementById("responseDraft")
};

function getAuthHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  if (state.authHeader) {
    headers.Authorization = state.authHeader;
  }
  return headers;
}

function setStatus(el, level, message, code) {
  if (!el) return;
  const className = level === "ok" ? "okText" : (level === "bad" ? "badText" : "warningText");
  el.innerHTML = `<span class="${className}">${escapeHtml(message || "")}</span>${code ? ` <code>${escapeHtml(code)}</code>` : ""}`;
}

function setLoading(button, isLoading, label) {
  if (!button) return;
  if (isLoading) {
    button.disabled = true;
  } else if ([saveDraftBtn, uploadScreenshotsBtn, createQuoteDraftBtn].includes(button)) {
    button.disabled = isDraftLocked();
  } else if (button === prepareHandoffBtn) {
    button.disabled = !state.currentAnalysis?.quote_id;
  } else {
    button.disabled = false;
  }
  if (label) button.textContent = isLoading ? label : button.dataset.idleLabel || button.textContent;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function money(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "—";
  return `$${amount.toFixed(2)} CAD`;
}

function formatDateTime(value) {
  if (!value) return "—";
  return String(value).replace("T", " ");
}

function statusLabel(status) {
  const labels = {
    draft: "Draft",
    customer_pending: "Customer pending",
    customer_accepted: "Customer accepted",
    customer_declined: "Customer declined",
    admin_approved: "Admin approved",
    approved: "Approved",
    scheduled: "Scheduled",
    in_progress: "In progress",
    completed: "Completed",
    cancelled: "Cancelled",
    rejected: "Rejected"
  };
  return labels[String(status || "").toLowerCase()] || (status || "Unknown");
}

function clearNode(node) {
  if (!node) return;
  while (node.firstChild) node.removeChild(node.firstChild);
}

function renderEmptyState(node, message) {
  clearNode(node);
  const div = document.createElement("div");
  div.className = "cardItem";
  div.innerHTML = `<div class="muted">${escapeHtml(message)}</div>`;
  node.appendChild(div);
}

async function fetchJSON(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: getAuthHeaders(options.headers || {})
  });

  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }

  if (!response.ok) {
    throw { status: response.status, data, raw: text };
  }

  return data;
}

function parseApiError(err) {
  if (err && typeof err === "object" && "status" in err) return err;
  return { status: null, data: {}, raw: String(err || "Unknown error") };
}

function showScreen(screenId) {
  state.currentScreen = screenId;
  appScreens.forEach((section) => {
    section.hidden = section.id !== screenId;
  });
  navButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.screen === screenId);
  });
}

function setAuthenticated(isAuthenticated) {
  loginScreen.hidden = isAuthenticated;
  authenticatedShell.hidden = !isAuthenticated;
  logoutBtn.hidden = !isAuthenticated;
}

function reviewedDraftFields() {
  return [
    fields.message,
    fields.customerName,
    fields.customerPhone,
    fields.description,
    fields.requestedDate,
    fields.requestedWindow,
    fields.serviceType,
    fields.jobAddress,
    fields.estimatedHours,
    fields.crewSize,
    fields.pickupAddress,
    fields.dropoffAddress,
    fields.files,
    fields.responseDraft
  ].filter(Boolean);
}

function isDraftLocked(analysis = state.currentAnalysis) {
  return !!(analysis && analysis.quote_id);
}

function setDraftLocked(isLocked) {
  const locked = !!isLocked;
  reviewedDraftFields().forEach((field) => {
    field.disabled = locked;
  });
  saveDraftBtn.disabled = locked;
  uploadScreenshotsBtn.disabled = locked;
  createQuoteDraftBtn.disabled = locked;
  prepareHandoffBtn.disabled = !state.currentAnalysis?.quote_id;
  draftLockNotice.classList.toggle("hidden", !locked);
}

function resetDraftState() {
  state.currentAnalysisId = "";
  state.currentAnalysis = null;
  state.handoff = null;
  fields.message.value = "";
  fields.customerName.value = "";
  fields.customerPhone.value = "";
  fields.description.value = "";
  fields.requestedDate.value = "";
  fields.requestedWindow.value = "";
  fields.serviceType.value = "";
  fields.jobAddress.value = "";
  fields.estimatedHours.value = "";
  fields.crewSize.value = "";
  fields.pickupAddress.value = "";
  fields.dropoffAddress.value = "";
  fields.files.value = "";
  fields.responseDraft.value = "";
  currentDraftMeta.textContent = "No draft selected yet.";
  setStatus(intakeStatus, "warn", "Start a draft, paste the message, then save/analyze.");
  setStatus(uploadStatus, "warn", "Upload screenshots after creating or selecting a draft.");
  setStatus(handoffStatus, "warn", "Create a quote draft before preparing customer handoff.");
  renderEmptyState(ocrReviewBox, "No screenshot uploads yet.");
  renderEmptyState(extractedDetailsBox, "No extracted details yet.");
  renderEmptyState(quoteGuidanceBox, "No quote guidance yet.");
  setDraftLocked(false);
}

function getReviewedCandidateInputs(analysis) {
  const intake = analysis?.intake || {};
  return {
    ...(intake.candidate_inputs || {}),
    ...(intake.operator_overrides || {})
  };
}

function applyAnalysisToForm(analysis) {
  const intake = analysis?.intake || {};
  const candidate = getReviewedCandidateInputs(analysis);
  fields.message.value = intake.message || "";
  fields.customerName.value = candidate.customer_name || "";
  fields.customerPhone.value = candidate.customer_phone || "";
  fields.description.value = candidate.description || candidate.job_description_customer || "";
  fields.requestedDate.value = intake.requested_job_date || "";
  fields.requestedWindow.value = intake.requested_time_window || "";
  fields.serviceType.value = candidate.service_type || "";
  fields.jobAddress.value = candidate.job_address || "";
  fields.estimatedHours.value = candidate.estimated_hours ?? "";
  fields.crewSize.value = candidate.crew_size ?? "";
  fields.pickupAddress.value = candidate.pickup_address || "";
  fields.dropoffAddress.value = candidate.dropoff_address || "";
}

function updateDraftMeta(analysis) {
  if (!analysis) {
    currentDraftMeta.textContent = "No draft selected yet.";
    return;
  }
  const serviceType = analysis?.quote_guidance?.service_type || analysis?.normalized_candidate?.service_type || "unknown service";
  currentDraftMeta.textContent = `${analysis.analysis_id} • ${statusLabel(analysis.status)} • ${serviceType}${analysis.quote_id ? ` • quote ${analysis.quote_id}` : ""}`;
}

function renderRecentDrafts() {
  if (!state.analyses.length) {
    renderEmptyState(recentDraftsList, "No draft analyses found yet.");
    return;
  }

  clearNode(recentDraftsList);
  state.analyses.slice(0, 8).forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "cardItem textButton";
    button.innerHTML = `
      <strong>${escapeHtml(item.quote_guidance?.service_type || item.normalized_candidate?.service_type || "Untitled draft")}</strong>
      <div class="muted">${escapeHtml(item.analysis_id || "")}</div>
      <div class="inlineMeta">
        <span class="pill">${escapeHtml(statusLabel(item.status))}</span>
        <span class="pill">${escapeHtml(item.quote_id ? "Quote linked" : "Recommendation only")}</span>
      </div>
    `;
    button.addEventListener("click", () => {
      loadAnalysis(item.analysis_id || "");
    });
    recentDraftsList.appendChild(button);
  });
}

function renderRequests() {
  if (!state.requests.length) {
    renderEmptyState(requestsList, "No booking/customer handoff requests found.");
    return;
  }

  clearNode(requestsList);
  state.requests.forEach((item) => {
    const card = document.createElement("article");
    card.className = "cardItem";
    card.innerHTML = `
      <strong>${escapeHtml(item.customer_name || item.job_address || item.request_id || "Request")}</strong>
      <div class="muted">${escapeHtml(item.service_type || "Unknown service")}</div>
      <div class="inlineMeta">
        <span class="pill">${escapeHtml(statusLabel(item.status))}</span>
        <span class="pill">${escapeHtml(item.requested_job_date || "No date")}</span>
        <span class="pill">${escapeHtml(item.requested_time_window || "No window")}</span>
      </div>
      <div class="subtleDivider"></div>
      <div><strong>Phone:</strong> ${escapeHtml(item.customer_phone || "—")}</div>
      <div><strong>Address:</strong> ${escapeHtml(item.job_address || "—")}</div>
      <div><strong>Notes:</strong> ${escapeHtml(item.notes || "—")}</div>
    `;
    requestsList.appendChild(card);
  });
}

function sortJobsForMobile(items) {
  return [...items].sort((a, b) => {
    const aDate = String(a.scheduled_start || a.created_at || "");
    const bDate = String(b.scheduled_start || b.created_at || "");
    return aDate.localeCompare(bDate);
  });
}

function renderJobs() {
  const visibleJobs = sortJobsForMobile(
    state.jobs.filter((item) => ["approved", "scheduled", "in_progress"].includes(String(item.status || "").toLowerCase()))
  );

  if (!visibleJobs.length) {
    renderEmptyState(jobsList, "No upcoming jobs found.");
    return;
  }

  clearNode(jobsList);
  visibleJobs.forEach((item) => {
    const context = item.scheduling_context || {};
    const card = document.createElement("article");
    card.className = "cardItem";
    card.innerHTML = `
      <strong>${escapeHtml(item.customer_name || item.job_address || item.job_id || "Job")}</strong>
      <div class="muted">${escapeHtml(item.service_type || "Unknown service")}</div>
      <div class="inlineMeta">
        <span class="pill">${escapeHtml(statusLabel(item.status))}</span>
        <span class="pill">${escapeHtml(formatDateTime(item.scheduled_start))}</span>
      </div>
      <div class="subtleDivider"></div>
      <div><strong>Address:</strong> ${escapeHtml(item.job_address || "—")}</div>
      <div><strong>Requested Date:</strong> ${escapeHtml(context.requested_job_date || "—")}</div>
      <div><strong>Requested Window:</strong> ${escapeHtml(context.requested_time_window || "—")}</div>
      <div><strong>Calendar Sync:</strong> ${escapeHtml(item.calendar_sync_status || "—")}</div>
      <div><strong>Calendar Error:</strong> ${escapeHtml(item.calendar_last_error || "—")}</div>
    `;
    jobsList.appendChild(card);
  });
}

function renderAttachmentReview(analysis) {
  const attachments = Array.isArray(analysis?.attachments) ? analysis.attachments : [];
  if (!attachments.length) {
    renderEmptyState(ocrReviewBox, "No screenshot uploads yet.");
    return;
  }

  clearNode(ocrReviewBox);
  attachments.forEach((item) => {
    const ocr = item.ocr_json || {};
    const card = document.createElement("article");
    card.className = "cardItem";
    card.innerHTML = `
      <strong>${escapeHtml(item.filename || item.attachment_id || "Attachment")}</strong>
      <div class="inlineMeta">
        <span class="pill">${escapeHtml(ocr.status || "skipped")}</span>
        <span class="pill">${escapeHtml(item.mime_type || "unknown")}</span>
      </div>
      <div class="subtleDivider"></div>
      <div><strong>OCR Preview</strong></div>
      <code>${escapeHtml(ocr.preview || "No OCR preview available.")}</code>
      <div class="small mt12">${escapeHtml(ocr.warning || "No OCR warnings.")}</div>
    `;
    ocrReviewBox.appendChild(card);
  });
}

function formatSuggestionValue(meta) {
  if (meta && typeof meta === "object" && !Array.isArray(meta)) {
    return meta.value ?? "";
  }
  return meta ?? "";
}

function renderExtractedDetails(analysis) {
  const suggestions = analysis?.autofill_suggestions || {};
  const missingFields = Array.isArray(analysis?.autofill_missing_fields) ? analysis.autofill_missing_fields : [];
  const warnings = Array.isArray(analysis?.autofill_warnings) ? analysis.autofill_warnings : [];

  clearNode(extractedDetailsBox);

  const suggestionEntries = Object.entries(suggestions).filter(([, value]) => formatSuggestionValue(value) !== "");
  if (!suggestionEntries.length && !missingFields.length && !warnings.length) {
    renderEmptyState(extractedDetailsBox, "No extracted details available yet.");
    return;
  }

  if (suggestionEntries.length) {
    const suggestionCard = document.createElement("article");
    suggestionCard.className = "cardItem";
    suggestionCard.innerHTML = `<strong>Extracted Details</strong>`;
    suggestionEntries.forEach(([key, value]) => {
      const row = document.createElement("div");
      row.className = "mt12";
      const renderedValue = formatSuggestionValue(value);
      row.innerHTML = `<strong>${escapeHtml(key.replace(/_/g, " "))}:</strong> ${escapeHtml(renderedValue)}`;
      suggestionCard.appendChild(row);
    });
    extractedDetailsBox.appendChild(suggestionCard);
  }

  if (missingFields.length) {
    const missingCard = document.createElement("article");
    missingCard.className = "cardItem";
    missingCard.innerHTML = `<strong>Missing Fields</strong><div class="muted">${escapeHtml(missingFields.join(", "))}</div>`;
    extractedDetailsBox.appendChild(missingCard);
  }

  if (warnings.length) {
    const warningCard = document.createElement("article");
    warningCard.className = "cardItem";
    warningCard.innerHTML = `<strong>Warnings</strong><div class="muted">${escapeHtml(warnings.join(" • "))}</div>`;
    extractedDetailsBox.appendChild(warningCard);
  }
}

function renderQuoteGuidance(analysis) {
  const guidance = analysis?.quote_guidance || {};
  if (!Object.keys(guidance).length) {
    renderEmptyState(quoteGuidanceBox, "No quote guidance yet.");
    return;
  }

  clearNode(quoteGuidanceBox);
  const range = guidance.range || {};
  const card = document.createElement("article");
  card.className = "cardItem";
  card.innerHTML = `
    <strong>${escapeHtml(guidance.service_type || "Quote guidance")}</strong>
    <div class="inlineMeta">
      <span class="pill">${escapeHtml(guidance.confidence || "Unknown confidence")}</span>
      <span class="pill">${escapeHtml(guidance.source || "existing_quote_pricing_logic")}</span>
    </div>
    <div class="subtleDivider"></div>
    <div><strong>Minimum Safe:</strong> ${escapeHtml(money(range.minimum_safe_cash_cad ?? guidance.cash_total_cad))}</div>
    <div><strong>Recommended Target:</strong> ${escapeHtml(money(range.recommended_target_cash_cad ?? guidance.cash_total_cad))}</div>
    <div><strong>Upper Reasonable:</strong> ${escapeHtml(money(range.upper_reasonable_cash_cad ?? guidance.cash_total_cad))}</div>
    <div><strong>Cash Total:</strong> ${escapeHtml(money(guidance.cash_total_cad))}</div>
    <div><strong>EMT Total:</strong> ${escapeHtml(money(guidance.emt_total_cad))}</div>
    <div class="subtleDivider"></div>
    <div><strong>Unknowns:</strong> ${escapeHtml((guidance.unknowns || []).join(", ") || "None")}</div>
    <div><strong>Risk Notes:</strong> ${escapeHtml((guidance.risk_notes || []).join(" • ") || "None")}</div>
    <div class="small mt12">${escapeHtml(guidance.disclaimer || "")}</div>
  `;
  quoteGuidanceBox.appendChild(card);
}

function updateQueueMetrics() {
  const draftItems = state.analyses.filter((item) => !item.quote_id);
  const openRequests = state.requests.filter((item) => ["customer_pending", "customer_accepted", "admin_approved"].includes(String(item.status || "").toLowerCase()));
  const upcomingJobs = state.jobs.filter((item) => ["approved", "scheduled", "in_progress"].includes(String(item.status || "").toLowerCase()));
  draftCount.textContent = String(draftItems.length);
  requestCount.textContent = String(openRequests.length);
  upcomingCount.textContent = String(upcomingJobs.length);
}

function buildCandidateInputs() {
  const payload = {};
  const mappings = {
    customer_name: fields.customerName.value,
    customer_phone: fields.customerPhone.value,
    description: fields.description.value,
    job_address: fields.jobAddress.value,
    service_type: fields.serviceType.value,
    pickup_address: fields.pickupAddress.value,
    dropoff_address: fields.dropoffAddress.value
  };

  Object.entries(mappings).forEach(([key, value]) => {
    const trimmed = String(value || "").trim();
    if (trimmed) payload[key] = trimmed;
  });

  if (fields.estimatedHours.value !== "") payload.estimated_hours = Number(fields.estimatedHours.value);
  if (fields.crewSize.value !== "") payload.crew_size = Number(fields.crewSize.value);

  return payload;
}

function isQuoteLockConflict(parsed) {
  const detail = String(parsed?.data?.detail || parsed?.raw || "");
  return parsed?.status === 409 && /quote draft|locked after quote draft creation/i.test(detail);
}

async function syncLockedAnalysisFromConflict(statusEl, fallbackMessage) {
  if (!state.currentAnalysisId) return false;

  try {
    await loadAnalysis(state.currentAnalysisId);
    const linkedQuoteId = state.currentAnalysis?.quote_id || "";
    setStatus(
      statusEl,
      "warn",
      linkedQuoteId
        ? `This analysis is now locked because quote draft ${linkedQuoteId} was linked by another operator.`
        : fallbackMessage
    );
    return true;
  } catch {
    return false;
  }
}

function buildAnalysisPayload() {
  return {
    analysis_id: state.currentAnalysisId || null,
    message: fields.message.value.trim() || null,
    requested_job_date: fields.requestedDate.value || null,
    requested_time_window: fields.requestedWindow.value || null,
    screenshot_attachment_ids: Array.isArray(state.currentAnalysis?.attachments)
      ? state.currentAnalysis.attachments.map((item) => item.attachment_id).filter(Boolean)
      : [],
    candidate_inputs: buildCandidateInputs(),
    operator_overrides: {}
  };
}

async function loadDashboardData() {
  const [analyses, requests, jobs] = await Promise.all([
    fetchJSON("/admin/api/screenshot-assistant/analyses?limit=20"),
    fetchJSON("/admin/api/quote-requests?limit=20"),
    fetchJSON("/admin/api/jobs?limit=20")
  ]);

  state.analyses = analyses.items || [];
  state.requests = requests.items || [];
  state.jobs = jobs.items || [];

  renderRecentDrafts();
  renderRequests();
  renderJobs();
  updateQueueMetrics();
}

async function loadAnalysis(analysisId) {
  if (!analysisId) return;
  const analysis = await fetchJSON(`/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisId)}`);
  state.currentAnalysisId = analysis.analysis_id || "";
  state.currentAnalysis = analysis;
  state.handoff = null;
  applyAnalysisToForm(analysis);
  updateDraftMeta(analysis);
  renderAttachmentReview(analysis);
  renderExtractedDetails(analysis);
  renderQuoteGuidance(analysis);
  setDraftLocked(isDraftLocked(analysis));
  setStatus(intakeStatus, "ok", isDraftLocked(analysis)
    ? "Draft loaded in locked view because a quote is already linked."
    : "Draft loaded. Review fields and save again if you make edits.");
  setStatus(uploadStatus, "warn", isDraftLocked(analysis)
    ? "Screenshot uploads are locked because the linked quote draft already exists."
    : "Upload more screenshots if needed, then re-run Save / Analyze Intake.");
  setStatus(handoffStatus, "warn", analysis.quote_id ? "Quote draft exists. You can prepare the customer handoff." : "Create a quote draft before preparing customer handoff.");
  showScreen("intakeScreen");
}

async function handleLogin(event) {
  event.preventDefault();
  const username = fields.username.value.trim();
  const password = fields.password.value.trim();

  if (!username || !password) {
    setStatus(loginStatus, "bad", "Enter both admin username and password.");
    return;
  }

  loginBtn.dataset.idleLabel = "Log In";
  setLoading(loginBtn, true, "Logging In...");
  state.authHeader = `Basic ${btoa(`${username}:${password}`)}`;
  state.username = username;

  try {
    await fetchJSON("/admin/api/quotes?limit=1");
    await loadDashboardData();
    setAuthenticated(true);
    showScreen("homeScreen");
    setStatus(loginStatus, "ok", "Mobile admin data loaded successfully.");
    resetDraftState();
    if (state.analyses[0]?.analysis_id) {
      await loadAnalysis(state.analyses[0].analysis_id);
      showScreen("homeScreen");
    }
  } catch (err) {
    const parsed = parseApiError(err);
    state.authHeader = "";
    state.username = "";
    if (parsed.status === 401) {
      setStatus(loginStatus, "bad", "Login failed. Check admin username/password and try again.", "HTTP 401");
    } else if (parsed.status === 429) {
      setStatus(loginStatus, "bad", "Too many failed login attempts. Wait a few minutes, then try again.", "HTTP 429");
    } else {
      setStatus(loginStatus, "bad", `Admin API error. ${parsed.data?.detail || parsed.raw || "Please try again."}`, parsed.status ? `HTTP ${parsed.status}` : "");
    }
  } finally {
    setLoading(loginBtn, false, "Logging In...");
  }
}

async function refreshAllData() {
  const screenToRestore = state.currentScreen;
  try {
    await loadDashboardData();
    if (state.currentAnalysisId) {
      await loadAnalysis(state.currentAnalysisId);
    }
    showScreen(screenToRestore);
  } catch (err) {
    const parsed = parseApiError(err);
    setStatus(loginStatus, "bad", `Refresh failed. ${parsed.data?.detail || parsed.raw || "Please try again."}`, parsed.status ? `HTTP ${parsed.status}` : "");
  }
}

async function saveDraftAnalysis(event) {
  event.preventDefault();
  if (isDraftLocked()) {
    setStatus(intakeStatus, "warn", "This analysis is locked because a quote draft is already linked.");
    return;
  }
  saveDraftBtn.dataset.idleLabel = "Save / Analyze Intake";
  setLoading(saveDraftBtn, true, "Saving...");
  setStatus(intakeStatus, "warn", "Saving reviewed intake and refreshing quote guidance...");

  try {
    const analysis = await fetchJSON("/admin/api/screenshot-assistant/analyses/intake", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildAnalysisPayload())
    });
    state.currentAnalysisId = analysis.analysis_id || "";
    state.currentAnalysis = analysis;
    updateDraftMeta(analysis);
    renderAttachmentReview(analysis);
    renderExtractedDetails(analysis);
    renderQuoteGuidance(analysis);
    setDraftLocked(isDraftLocked(analysis));
    setStatus(intakeStatus, "ok", "Draft analysis saved. Guidance still reuses the existing quote engine.");
    setStatus(handoffStatus, "warn", analysis.quote_id ? "Quote draft already exists. You can prepare the customer handoff." : "Create a quote draft before preparing customer handoff.");
    await loadDashboardData();
  } catch (err) {
    const parsed = parseApiError(err);
    if (isQuoteLockConflict(parsed) && await syncLockedAnalysisFromConflict(intakeStatus, "This analysis is now locked because a quote draft was linked by another operator.")) {
      return;
    }
    setStatus(intakeStatus, "bad", `Save failed. ${parsed.data?.detail || parsed.raw || "Please review the intake fields and try again."}`, parsed.status ? `HTTP ${parsed.status}` : "");
  } finally {
    setLoading(saveDraftBtn, false, "Saving...");
  }
}

async function uploadScreenshots() {
  if (isDraftLocked()) {
    setStatus(uploadStatus, "warn", "This analysis is locked because a quote draft is already linked.");
    return;
  }

  const files = Array.from(fields.files.files || []);
  if (!files.length) {
    setStatus(uploadStatus, "bad", "Choose at least one screenshot or photo before uploading.");
    return;
  }

  uploadScreenshotsBtn.dataset.idleLabel = "Upload Files";
  setLoading(uploadScreenshotsBtn, true, "Uploading...");
  setStatus(uploadStatus, "warn", "Uploading screenshots and collecting OCR previews...");

  try {
    if (!state.currentAnalysisId) {
      const analysis = await fetchJSON("/admin/api/screenshot-assistant/analyses/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildAnalysisPayload())
      });
      state.currentAnalysisId = analysis.analysis_id || "";
      state.currentAnalysis = analysis;
      updateDraftMeta(analysis);
    }

    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    const response = await fetch(`/admin/api/screenshot-assistant/analyses/${encodeURIComponent(state.currentAnalysisId)}/attachments`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: formData
    });

    const text = await response.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { raw: text };
    }
    if (!response.ok) throw { status: response.status, data, raw: text };

    await loadAnalysis(data.analysis_id || state.currentAnalysisId);
    await loadDashboardData();
    fields.files.value = "";
    setStatus(uploadStatus, "ok", `Uploaded ${(data.uploaded || []).length} screenshot(s). OCR previews are shown below.`);
  } catch (err) {
    const parsed = parseApiError(err);
    if (isQuoteLockConflict(parsed) && await syncLockedAnalysisFromConflict(uploadStatus, "This analysis is now locked because a quote draft was linked by another operator.")) {
      return;
    }
    setStatus(uploadStatus, "bad", `Upload failed. ${parsed.data?.detail || parsed.raw || "Please review the files and try again."}`, parsed.status ? `HTTP ${parsed.status}` : "");
  } finally {
    setLoading(uploadScreenshotsBtn, false, "Uploading...");
  }
}

async function createQuoteDraft() {
  if (!state.currentAnalysisId) {
    setStatus(handoffStatus, "bad", "Create or load a draft analysis before creating a quote draft.");
    return;
  }
  if (isDraftLocked()) {
    setStatus(handoffStatus, "warn", "This analysis is locked because a quote draft is already linked.");
    return;
  }

  createQuoteDraftBtn.dataset.idleLabel = "Create Quote Draft";
  setLoading(createQuoteDraftBtn, true, "Creating...");
  setStatus(handoffStatus, "warn", "Creating a real quote draft from the reviewed analysis...");

  try {
    const data = await fetchJSON(`/admin/api/screenshot-assistant/analyses/${encodeURIComponent(state.currentAnalysisId)}/quote-draft`, {
      method: "POST"
    });
    state.currentAnalysis = data.analysis || null;
    if (data.analysis?.analysis_id) state.currentAnalysisId = data.analysis.analysis_id;
    updateDraftMeta(state.currentAnalysis);
    renderQuoteGuidance(state.currentAnalysis);
    setDraftLocked(isDraftLocked(state.currentAnalysis));
    await loadDashboardData();
    setStatus(handoffStatus, "ok", `Quote draft ${data.quote?.quote_id || "created"} linked. You can now prepare customer handoff.`);
  } catch (err) {
    const parsed = parseApiError(err);
    if (isQuoteLockConflict(parsed) && await syncLockedAnalysisFromConflict(handoffStatus, "This analysis is now locked because a quote draft was linked by another operator.")) {
      return;
    }
    setStatus(handoffStatus, "bad", `Quote draft failed. ${parsed.data?.detail || parsed.raw || "Please review the draft and try again."}`, parsed.status ? `HTTP ${parsed.status}` : "");
  } finally {
    setLoading(createQuoteDraftBtn, false, "Creating...");
  }
}

async function prepareCustomerHandoff() {
  const quoteId = state.currentAnalysis?.quote_id || "";
  if (!quoteId) {
    setStatus(handoffStatus, "bad", "Create a linked quote draft before preparing customer handoff.");
    return;
  }

  prepareHandoffBtn.dataset.idleLabel = "Prepare Customer Handoff";
  setLoading(prepareHandoffBtn, true, "Preparing...");
  setStatus(handoffStatus, "warn", "Preparing the normal customer handoff...");

  try {
    const data = await fetchJSON(`/admin/api/quotes/${encodeURIComponent(quoteId)}/handoff`, {
      method: "POST"
    });
    state.handoff = data;
    await loadDashboardData();
    setStatus(handoffStatus, "ok", `Customer handoff ready for request ${data.request_id}.`);
    const handoffCard = document.createElement("article");
    handoffCard.className = "cardItem";
    handoffCard.innerHTML = `
      <strong>Customer Handoff</strong>
      <div class="muted">Request ${escapeHtml(data.request_id || "")}</div>
      <div class="inlineMeta">
        <span class="pill">${escapeHtml(statusLabel(data.status))}</span>
        <span class="pill">${escapeHtml(data.already_existed ? "Existing request reused" : "New request")}</span>
      </div>
      <code>${escapeHtml(data.handoff_url || "")}</code>
    `;
    quoteGuidanceBox.prepend(handoffCard);
  } catch (err) {
    const parsed = parseApiError(err);
    setStatus(handoffStatus, "bad", `Handoff failed. ${parsed.data?.detail || parsed.raw || "Please review the quote draft and try again."}`, parsed.status ? `HTTP ${parsed.status}` : "");
  } finally {
    setLoading(prepareHandoffBtn, false, "Preparing...");
  }
}

function logout() {
  state.authHeader = "";
  state.username = "";
  state.analyses = [];
  state.requests = [];
  state.jobs = [];
  setAuthenticated(false);
  resetDraftState();
  renderEmptyState(recentDraftsList, "Log in to load recent drafts.");
  renderEmptyState(requestsList, "Log in to load requests.");
  renderEmptyState(jobsList, "Log in to load upcoming jobs.");
  draftCount.textContent = "0";
  requestCount.textContent = "0";
  upcomingCount.textContent = "0";
  setStatus(loginStatus, "warn", "Enter admin username/password, then log in.");
  showScreen("homeScreen");
}

navButtons.forEach((button) => {
  button.addEventListener("click", () => showScreen(button.dataset.screen || "homeScreen"));
});

loginForm.addEventListener("submit", handleLogin);
refreshHomeBtn.addEventListener("click", refreshAllData);
refreshRequestsBtn.addEventListener("click", refreshAllData);
refreshJobsBtn.addEventListener("click", refreshAllData);
homeNewIntakeBtn.addEventListener("click", () => {
  resetDraftState();
  showScreen("intakeScreen");
});
homeResumeLatestBtn.addEventListener("click", async () => {
  if (!state.analyses[0]?.analysis_id) {
    setStatus(loginStatus, "warn", "No saved draft is available yet.");
    return;
  }
  await loadAnalysis(state.analyses[0].analysis_id);
});
newDraftBtn.addEventListener("click", resetDraftState);
intakeForm.addEventListener("submit", saveDraftAnalysis);
uploadScreenshotsBtn.addEventListener("click", uploadScreenshots);
createQuoteDraftBtn.addEventListener("click", createQuoteDraft);
prepareHandoffBtn.addEventListener("click", prepareCustomerHandoff);
logoutBtn.addEventListener("click", logout);

renderEmptyState(recentDraftsList, "Log in to load recent drafts.");
renderEmptyState(requestsList, "Log in to load requests.");
renderEmptyState(jobsList, "Log in to load upcoming jobs.");
resetDraftState();
setAuthenticated(false);
setStatus(loginStatus, "warn", "Enter admin username/password, then log in.");
showScreen("homeScreen");
