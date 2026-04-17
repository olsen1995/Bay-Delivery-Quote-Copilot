function renderAuditLog(items) {
  const box = document.getElementById("auditLogBox");
  if (!items || items.length === 0) return addEmptyState(box, "No audit log entries yet.");
  clearNode(box);

  const { table, tbody } = createTable([
    "Timestamp",
    "Operator",
    "Action",
    "Entity",
    "Record ID",
    "Success",
    "Error Summary"
  ]);

  items.forEach((entry) => {
    const tr = document.createElement("tr");

    const tdTime = document.createElement("td");
    tdTime.className = "small";
    tdTime.textContent = entry.timestamp || "";
    tr.appendChild(tdTime);

    const tdOp = document.createElement("td");
    tdOp.textContent = entry.operator_username || "";
    tr.appendChild(tdOp);

    const tdAction = document.createElement("td");
    tdAction.textContent = entry.action_type || "";
    tr.appendChild(tdAction);

    const tdEntity = document.createElement("td");
    tdEntity.textContent = entry.entity_type || "";
    tr.appendChild(tdEntity);

    const tdRec = document.createElement("td");
    tdRec.textContent = entry.record_id || "";
    tr.appendChild(tdRec);

    const tdSuccess = document.createElement("td");
    tdSuccess.textContent = entry.success ? "Yes" : "No";
    tr.appendChild(tdSuccess);

    const tdErr = document.createElement("td");
    tdErr.className = "small muted";
    tdErr.textContent = entry.error_summary || "";
    tr.appendChild(tdErr);

    tbody.appendChild(tr);
  });

  box.appendChild(table);
}
const statusLine = document.getElementById("statusLine");
const refreshBtn = document.getElementById("refreshBtn");
const adminUsernameInput = document.getElementById("adminUsername");
const adminPasswordInput = document.getElementById("adminPassword");
const adminProtectedDashboard = document.getElementById("adminProtectedDashboard");
const adminProtectedSections = Array.from(document.querySelectorAll("[data-admin-protected='true']"));
const adminPageRoot = document.body;
const scheduleCloseBtn = document.getElementById("scheduleCloseBtn");
const scheduleCancelBtn = document.getElementById("scheduleCancelBtn");
const assistantStatusLine = document.getElementById("assistantStatusLine");
const assistantDraftMeta = document.getElementById("assistantDraftMeta");
const assistantAttachmentIdsInput = document.getElementById("assistantAttachmentIds");
const assistantScreenshotFilesInput = document.getElementById("assistantScreenshotFiles");
const refreshButtonLabel = "Log In & Load Data";
let adminSessionReady = false;
let currentAssistantAnalysisId = "";
let currentAssistantHandoff = null;
let currentJobsById = {};
let currentQuoteItems = [];
let currentQuoteDetailId = "";
let currentQuoteDetailLoading = false;
let currentQuoteDetailError = "";
let currentQuoteDetailsById = {};
let assistantDraftDirty = false;
const assistantUnsavedDraftWarning = "Desktop admin guidance is reference-only. Use request and job workflow actions for operational updates.";
const assistantAutofillFieldConfig = {
  customer_name: { label: "Customer Name" },
  customer_phone: { label: "Customer Phone" },
  job_address: { label: "Job Address" },
  description: { label: "Description" },
  requested_job_date: { label: "Requested Job Date" },
  requested_time_window: { label: "Requested Time Window" }
};

function setAssistantDraftLocked(isLocked) {
  // Desktop assistant is read-only; no draft controls to lock/unlock.
  void isLocked;
}

function getAdminCreds() {
  return {
    username: (adminUsernameInput.value || "").trim(),
    password: (adminPasswordInput.value || "").trim()
  };
}

function setLoading(isLoading) {
  refreshBtn.disabled = isLoading;
  refreshBtn.textContent = isLoading ? "Loading..." : refreshButtonLabel;
}

function syncAssistantDraftActionState() {
  if (!adminSessionReady || !assistantStatusLine) return;
  if (assistantDraftDirty) {
    setLine(assistantStatusLine, "bad", assistantUnsavedDraftWarning);
  }
}

function setAssistantDraftDirty(isDirty) {
  assistantDraftDirty = !!isDirty;
  syncAssistantDraftActionState();
}

function markAssistantDraftDirty(message) {
  if (!currentAssistantAnalysisId) return;
  const wasDirty = assistantDraftDirty;
  setAssistantDraftDirty(true);
  if (message && !wasDirty) {
    setLine(assistantStatusLine, "bad", message);
  }
}

function authHeaders() {
  const headers = {};
  const { username: u, password: p } = getAdminCreds();
  if (u && p) {
    headers["Authorization"] = "Basic " + btoa(u + ":" + p);
  }
  return headers;
}

function parseApiError(err) {
  if (err && typeof err === "object" && err.status) return err;
  return { status: null, data: {}, raw: String(err) };
}

function setLine(el, level, msg, suffixCode) {
  el.textContent = "";
  const span = document.createElement("span");
  if (level === "ok") span.className = "ok";
  if (level === "bad") span.className = "bad";
  span.textContent = msg;
  el.appendChild(span);

  if (suffixCode) {
    el.appendChild(document.createTextNode(" "));
    const code = document.createElement("code");
    code.textContent = suffixCode;
    el.appendChild(code);
  }
}

function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function setAdminAuthenticated(isAuthenticated) {
  if (!adminPageRoot) return;
  adminPageRoot.classList.toggle("admin-authenticated", Boolean(isAuthenticated));
}

function setProtectedDashboardVisible(isVisible) {
  setAdminAuthenticated(isVisible);
  if (adminProtectedDashboard) {
    if (isVisible) {
      adminProtectedDashboard.removeAttribute("hidden");
      adminProtectedDashboard.setAttribute("aria-hidden", "false");
    } else {
      adminProtectedDashboard.setAttribute("hidden", "");
      adminProtectedDashboard.setAttribute("aria-hidden", "true");
    }
  }
  adminProtectedSections.forEach((section) => {
    if (isVisible) {
      section.removeAttribute("hidden");
      section.setAttribute("aria-hidden", "false");
      return;
    }
    section.setAttribute("hidden", "");
    section.setAttribute("aria-hidden", "true");
  });
}

function resetProtectedDashboard() {
  setProtectedDashboardVisible(false);
  const boxIds = ["quotesBox", "requestsBox", "jobsBox", "assistantResultBox", "assistantHistoryBox", "assistantUploadList"];
  boxIds.forEach((id) => {
    const box = document.getElementById(id);
    if (box) clearNode(box);
  });
  currentAssistantAnalysisId = "";
  currentAssistantHandoff = null;
  currentJobsById = {};
  currentQuoteItems = [];
  currentQuoteDetailId = "";
  currentQuoteDetailLoading = false;
  currentQuoteDetailError = "";
  currentQuoteDetailsById = {};
  setAssistantDraftLocked(false);
  if (assistantDraftMeta) assistantDraftMeta.textContent = "No screenshot intake guidance records yet.";
}

function createTable(headers) {
  const table = document.createElement("table");
  table.className = "dataTable";
  const thead = document.createElement("thead");
  const tr = document.createElement("tr");
  headers.forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h;
    tr.appendChild(th);
  });
  thead.appendChild(tr);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  table.appendChild(tbody);
  return { table, tbody };
}

function addEmptyState(container, text) {
  clearNode(container);
  const div = document.createElement("div");
  div.className = "emptyState";
  div.textContent = text;
  container.appendChild(div);
}

async function fetchJSON(path) {
  const res = await fetch(path, { headers: authHeaders() });

  // Some auth failures come back non-JSON; handle safely.
  const text = await res.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }

  if (!res.ok) {
    throw { status: res.status, data, raw: text };
  }
  return data;
}

function safeGet(obj, path, fallback = "") {
  try {
    return path.split(".").reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), obj) ?? fallback;
  } catch {
    return fallback;
  }
}

function statusLabel(status) {
  const map = {
    pending: "Pending",
    customer_pending: "Customer pending",
    customer_accepted: "Customer accepted",
    customer_declined: "Customer declined",
    admin_approved: "Admin approved",
    in_progress: "In progress",
    completed: "Completed",
    scheduled: "Scheduled",
    cancelled: "Cancelled",
    rejected: "Rejected"
  };
  return map[(status || "").toLowerCase()] || (status || "unknown");
}

function money(n) {
  const x = Number(n || 0);
  return "$" + x.toFixed(2);
}

const formatMoneyOrDash = (value) =>
  value == null || value === "" ? "-" : money(value);

function normalizeStatusKey(status) {
  const key = (status || "").toLowerCase();
  if (key === "customer_pending") return "pending";
  return key || "pending";
}

function makeStatusBadge(status) {
  const badge = document.createElement("span");
  const key = normalizeStatusKey(status);
  badge.className = "statusBadge status-" + key;
  badge.textContent = statusLabel(status);
  return badge;
}

function formatConfidenceLevel(level) {
  const normalized = String(level || "").trim().toLowerCase();
  if (!normalized) return "Unknown";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function makeRiskConfidenceBadge(level) {
  const normalized = String(level || "").trim().toLowerCase() || "unknown";
  const badge = document.createElement("span");
  badge.className = "statusBadge quoteRiskConfidence risk-confidence-" + normalized;
  badge.textContent = formatConfidenceLevel(normalized);
  return badge;
}

function createQuoteMetaRow(label, value, extraNode) {
  const row = document.createElement("div");
  row.className = "quoteDetailMetaRow";

  const labelEl = document.createElement("strong");
  labelEl.textContent = `${label}:`;
  row.appendChild(labelEl);

  if (value !== null && value !== undefined && value !== "") {
    row.appendChild(document.createTextNode(` ${value}`));
  } else if (!extraNode) {
    row.appendChild(document.createTextNode(" —"));
  }

  if (extraNode) {
    row.appendChild(document.createTextNode(" "));
    row.appendChild(extraNode);
  }

  return row;
}

function createQuoteDetailPanel(detail) {
  const panel = document.createElement("div");
  panel.className = "quoteDetailPanel";

  const title = document.createElement("div");
  title.className = "quoteDetailTitle";
  title.textContent = "Quote Details";
  panel.appendChild(title);

  const meta = document.createElement("div");
  meta.className = "quoteDetailMeta";
  const request = detail?.request ?? {};
  const response = detail?.response ?? {};
  const safeRequest = typeof request === "object" && request !== null ? request : {};
  const safeResponse = typeof response === "object" && response !== null ? response : {};

  [
    ["Quote", detail.quote_id || "—"],
    ["Created", detail.created_at || "—"],
    ["Customer", safeRequest.customer_name || "—"],
    ["Phone", safeRequest.customer_phone || "—"],
    ["Service", safeRequest.service_type || "—"],
    ["Address", safeRequest.job_address || "—"],
    ["Cash", formatMoneyOrDash(safeResponse.cash_total_cad)],
    ["EMT", formatMoneyOrDash(safeResponse.emt_total_cad)],
    ["Description", safeRequest.job_description_customer || "—"],
  ].forEach(([label, value]) => {
    meta.appendChild(createQuoteMetaRow(label, value));
  });
  panel.appendChild(meta);

  const assessment = detail.internal_risk_assessment || null;
  const riskFlags = Array.isArray(safeGet(assessment, "risk_flags", null))
    ? assessment.risk_flags.filter((flag) => String(flag || "").trim())
    : [];

  if (assessment && (assessment.confidence_level || riskFlags.length)) {
    const riskSection = document.createElement("section");
    riskSection.className = "quoteRiskSection";

    const riskTitle = document.createElement("div");
    riskTitle.className = "quoteDetailTitle";
    riskTitle.textContent = "Quote Risk Assessment";
    riskSection.appendChild(riskTitle);

    riskSection.appendChild(
      createQuoteMetaRow(
        "Confidence",
        null,
        makeRiskConfidenceBadge(assessment.confidence_level)
      )
    );

    const flagsRow = document.createElement("div");
    flagsRow.className = "quoteDetailMetaRow";
    const flagsLabel = document.createElement("strong");
    flagsLabel.textContent = "Flags:";
    flagsRow.appendChild(flagsLabel);

    if (riskFlags.length) {
      const list = document.createElement("ul");
      list.className = "quoteRiskFlags";
      riskFlags.forEach((flag) => {
        const item = document.createElement("li");
        item.textContent = flag;
        list.appendChild(item);
      });
      flagsRow.appendChild(list);
    } else {
      flagsRow.appendChild(document.createTextNode(" none"));
    }

    riskSection.appendChild(flagsRow);
    panel.appendChild(riskSection);
  }

  return panel;
}

function createQuoteDetailRow(quoteId) {
  const tr = document.createElement("tr");
  tr.className = "quoteDetailRow";

  const td = document.createElement("td");
  td.colSpan = 7;

  if (currentQuoteDetailLoading && currentQuoteDetailId === quoteId) {
    td.appendChild(createQuoteMetaRow("Loading", "Retrieving quote details..."));
    tr.appendChild(td);
    return tr;
  }

  if (currentQuoteDetailError && currentQuoteDetailId === quoteId) {
    const error = document.createElement("div");
    error.className = "quoteDetailPanel";
    const message = document.createElement("div");
    message.className = "bad";
    message.textContent = currentQuoteDetailError;
    error.appendChild(message);
    td.appendChild(error);
    tr.appendChild(td);
    return tr;
  }

  const detail = currentQuoteDetailsById[quoteId];
  if (detail) {
    td.appendChild(createQuoteDetailPanel(detail));
  }

  tr.appendChild(td);
  return tr;
}

async function toggleQuoteDetails(quoteId) {
  if (!quoteId) return;

  if (currentQuoteDetailId === quoteId) {
    currentQuoteDetailId = "";
    currentQuoteDetailLoading = false;
    currentQuoteDetailError = "";
    renderQuotes(currentQuoteItems);
    return;
  }

  currentQuoteDetailId = quoteId;
  currentQuoteDetailLoading = true;
  currentQuoteDetailError = "";
  renderQuotes(currentQuoteItems);

  try {
    const detail = await fetchJSON(`/admin/api/quotes/${encodeURIComponent(quoteId)}`);
    if (currentQuoteDetailId !== quoteId) return;
    currentQuoteDetailsById[quoteId] = detail;
    currentQuoteDetailLoading = false;
    renderQuotes(currentQuoteItems);
  } catch (err) {
    if (currentQuoteDetailId !== quoteId) return;
    const parsed = parseApiError(err);
    currentQuoteDetailLoading = false;
    currentQuoteDetailError = parsed.status
      ? `Quote details failed to load. ${safeGet(parsed, "data.detail", parsed.raw || "")}`.trim()
      : `Quote details failed to load. ${parsed.raw}`;
    renderQuotes(currentQuoteItems);
  }
}

function renderQuotes(items) {
  currentQuoteItems = items || [];
  const box = document.getElementById("quotesBox");
  if (!items || items.length === 0) return addEmptyState(box, "No quotes yet.");
  clearNode(box);

  const { table, tbody } = createTable(["Quote", "Status", "Customer", "Service", "Address", "Estimated", "Actions"]);

  items.forEach((q) => {
    const tr = document.createElement("tr");
    const isDetailOpen = currentQuoteDetailId === (q.quote_id || "");

    const tdId = document.createElement("td");
    const code = document.createElement("code");
    code.textContent = q.quote_id || "";
    const created = document.createElement("div");
    created.className = "small";
    created.textContent = q.created_at || "";
    tdId.append(code, created);

    const tdStatus = document.createElement("td");
    const quoteStatus = safeGet(q, "request.status", q.status || "pending");
    tdStatus.appendChild(makeStatusBadge(quoteStatus));

    const tdCustomer = document.createElement("td");
    tdCustomer.textContent = safeGet(q, "request.customer_name", "");

    const tdSvc = document.createElement("td");
    const service = safeGet(q, "request.service_type", "");
    const servicePill = document.createElement("span");
    servicePill.className = "pill";
    servicePill.textContent = service;
    tdSvc.appendChild(servicePill);

    const tdAddress = document.createElement("td");
    tdAddress.className = "small";
    tdAddress.textContent = safeGet(q, "request.job_address", "");

    const tdTotal = document.createElement("td");
    const estimate = safeGet(q, "response.cash_total_cad", null);
    tdTotal.textContent = estimate === null || estimate === undefined || estimate === "" ? "-" : money(estimate);

    const tdActions = document.createElement("td");
    const detailBtn = document.createElement("button");
    detailBtn.type = "button";
    detailBtn.className = "secondaryAction quoteDetailToggle";
    detailBtn.textContent = isDetailOpen ? "Hide Details" : "View Details";
    detailBtn.disabled = !q.quote_id;
    detailBtn.addEventListener("click", () => toggleQuoteDetails(q.quote_id || ""));
    tdActions.appendChild(detailBtn);

    tr.append(tdId, tdStatus, tdCustomer, tdSvc, tdAddress, tdTotal, tdActions);
    tbody.appendChild(tr);
    if (isDetailOpen) {
      tbody.appendChild(createQuoteDetailRow(q.quote_id || ""));
    }
  });

  box.appendChild(table);
}

async function decide(requestId, action) {
  const notes = prompt("Admin notes (" + action + ") - optional:") || "";
  statusLine.textContent = "Saving decision...";

  const headers = Object.assign({ "Content-Type": "application/json" }, authHeaders());
  const res = await fetch("/admin/api/quote-requests/" + encodeURIComponent(requestId) + "/decision", {
    method: "POST",
    headers,
    body: JSON.stringify({ action, notes: (notes.trim() || null) })
  });

  const text = await res.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }

  if (!res.ok) {
    setLine(statusLine, "bad", "Error:");
    statusLine.appendChild(document.createTextNode(" " + JSON.stringify(data)));
    return;
  }

  const newStatus = safeGet(data, "request.status", "");
  setLine(statusLine, "ok", "Saved:", (newStatus || action.toUpperCase()));

  await refreshAll();
}

function actionCell(item) {
  const td = document.createElement("td");
  const st = (item.status || "").toLowerCase();

  // Only allow admin action once customer accepted
  if (st !== "customer_accepted") {
    const noAction = document.createElement("span");
    noAction.className = "muted small";
    if (st === "customer_pending") noAction.textContent = "Waiting on customer";
    else noAction.textContent = "No action needed";
    td.appendChild(noAction);
    return td;
  }

  const approveBtn = document.createElement("button");
  approveBtn.type = "button";
  approveBtn.className = "actionBtn";
  approveBtn.textContent = "Approve";
  approveBtn.addEventListener("click", () => decide(item.request_id || "", "approve"));

  const rejectBtn = document.createElement("button");
  rejectBtn.type = "button";
  rejectBtn.className = "btnSpacer actionBtn danger";
  rejectBtn.textContent = "Reject";
  rejectBtn.addEventListener("click", () => decide(item.request_id || "", "reject"));

  td.append(approveBtn, rejectBtn);
  return td;
}

function renderRequests(items) {
  const box = document.getElementById("requestsBox");
  if (!items || items.length === 0) return addEmptyState(box, "No booking requests yet.");
  clearNode(box);

  const { table, tbody } = createTable(["Request", "Customer", "Job", "Requested", "Totals", "Actions"]);

  items.forEach((r) => {
    const tr = document.createElement("tr");

    const tdReq = document.createElement("td");
    const reqCode = document.createElement("code");
    reqCode.textContent = r.request_id || "";
    const reqDate = document.createElement("div");
    reqDate.className = "small";
    reqDate.textContent = r.created_at || "";
    tdReq.append(reqCode, reqDate);

    const tdCustomer = document.createElement("td");
    const cName = document.createElement("div");
    cName.textContent = r.customer_name || "";
    const cPhone = document.createElement("div");
    cPhone.className = "small";
    cPhone.textContent = r.customer_phone || "";
    tdCustomer.append(cName, cPhone);

    const tdJob = document.createElement("td");
    tdJob.className = "small";
    const addr = document.createElement("div");
    addr.textContent = r.job_address || "";
    const svc = document.createElement("div");
    svc.textContent = "Service: " + (r.service_type || "");
    tdJob.append(addr, svc);

    const tdRequested = document.createElement("td");
    tdRequested.className = "small";
    const date = document.createElement("div");
    date.textContent = "Date: " + (r.requested_job_date || "-");
    const windowEl = document.createElement("div");
    windowEl.textContent = "Window: " + (r.requested_time_window || "-");
    tdRequested.append(date, windowEl);

    const tdTotals = document.createElement("td");
    const stWrap = document.createElement("div");
    stWrap.className = "small";
    const stPill = makeStatusBadge(r.status);
    stWrap.appendChild(document.createTextNode("Status: "));
    stWrap.appendChild(stPill);

    const cash = document.createElement("div");
    cash.className = "small";
    cash.textContent = "Cash: " + money(r.cash_total_cad);

    const emt = document.createElement("div");
    emt.className = "small";
    emt.textContent = "EMT: " + money(r.emt_total_cad);

    tdTotals.append(stWrap, cash, emt);

    tr.append(tdReq, tdCustomer, tdJob, tdRequested, tdTotals, actionCell(r));
    tbody.appendChild(tr);
  });

  box.appendChild(table);
}

function renderJobs(items) {
  const box = document.getElementById("jobsBox");
  if (!items || items.length === 0) return addEmptyState(box, "No jobs yet.");
  clearNode(box);
  currentJobsById = Object.fromEntries((items || []).filter((item) => item && item.job_id).map((item) => [item.job_id, item]));

  const { table, tbody } = createTable(["Job", "Quote", "Status", "Customer", "Address", "Cash Total", "Scheduled", "Calendar Sync", "Actions"]);

  items.forEach((j) => {
    const tr = document.createElement("tr");

    const tdJob = document.createElement("td");
    const jobCode = document.createElement("code");
    jobCode.textContent = j.job_id || "";
    const created = document.createElement("div");
    created.className = "small";
    created.textContent = j.created_at || "";
    tdJob.append(jobCode, created);

    const tdQuote = document.createElement("td");
    const qCode = document.createElement("code");
    qCode.textContent = j.quote_id || "";
    tdQuote.appendChild(qCode);

    const tdStatus = document.createElement("td");
    tdStatus.appendChild(makeStatusBadge(j.status || "pending"));
    const lifecycleRows = [
      ["Started:", j.started_at || ""],
      ["Completed:", j.completed_at || ""],
      ["Cancelled:", j.cancelled_at || ""],
      ["Close-out notes:", j.closeout_notes || ""]
    ].filter(([, value]) => value);
    lifecycleRows.forEach(([label, value]) => {
      const line = document.createElement("div");
      line.className = "small muted";
      line.textContent = `${label} ${value}`;
      tdStatus.appendChild(line);
    });

    const tdCustomer = document.createElement("td");
    const name = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = j.customer_name || "";
    name.appendChild(strong);
    const phone = document.createElement("div");
    phone.className = "small";
    phone.textContent = j.customer_phone || "";
    tdCustomer.append(name, phone);

    const tdAddress = document.createElement("td");
    tdAddress.className = "small";
    const addressLine = document.createElement("div");
    addressLine.textContent = j.job_address || "";
    tdAddress.appendChild(addressLine);
    if (j.service_type) {
      const serviceLine = document.createElement("div");
      serviceLine.textContent = "Service: " + j.service_type;
      tdAddress.appendChild(serviceLine);
    }

    const tdTotal = document.createElement("td");
    tdTotal.textContent = money(j.cash_total_cad);

    const tdScheduled = document.createElement("td");
    tdScheduled.className = "small";
    if (j.scheduled_start && j.scheduled_end) {
      const start = new Date(j.scheduled_start).toLocaleString();
      const end = new Date(j.scheduled_end).toLocaleString();
      tdScheduled.textContent = `${start} - ${end}`;
    } else {
      tdScheduled.textContent = "Not scheduled";
    }

    const tdSync = document.createElement("td");
    const syncStatus = j.calendar_sync_status || "not_configured";
    const syncPill = document.createElement("span");
    syncPill.className = "pill";
    syncPill.textContent = syncStatus;
    tdSync.appendChild(syncPill);
    if (j.calendar_last_error) {
      const errorDiv = document.createElement("div");
      errorDiv.className = "small muted";
      errorDiv.textContent = j.calendar_last_error;
      tdSync.appendChild(errorDiv);
    }

    const tdActions = document.createElement("td");
    if (j.status === "approved") {
      const startBtn = document.createElement("button");
      startBtn.type = "button";
      startBtn.className = "actionBtn";
      startBtn.textContent = "Start Job";
      startBtn.addEventListener("click", () => startJob(j.job_id));
      tdActions.appendChild(startBtn);

      if (!j.scheduled_start) {
        const scheduleBtn = document.createElement("button");
        scheduleBtn.type = "button";
        scheduleBtn.className = "actionBtn btnSpacer";
        scheduleBtn.textContent = "Schedule";
        scheduleBtn.addEventListener("click", () => showScheduleModal(j.job_id, false));
        tdActions.appendChild(scheduleBtn);
      } else {
        const rescheduleBtn = document.createElement("button");
        rescheduleBtn.type = "button";
        rescheduleBtn.className = "actionBtn btnSpacer";
        rescheduleBtn.textContent = "Reschedule";
        rescheduleBtn.addEventListener("click", () => showScheduleModal(j.job_id, true));
        tdActions.appendChild(rescheduleBtn);
      }

      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.textContent = "Cancel";
      cancelBtn.className = "danger btnSpacer actionBtn";
      cancelBtn.addEventListener("click", () => cancelJob(j.job_id));
      tdActions.appendChild(cancelBtn);
    } else if (j.status === "in_progress") {
      const completeBtn = document.createElement("button");
      completeBtn.type = "button";
      completeBtn.className = "actionBtn";
      completeBtn.textContent = "Mark Complete";
      completeBtn.addEventListener("click", () => completeJob(j.job_id));
      tdActions.appendChild(completeBtn);

      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.textContent = "Cancel";
      cancelBtn.className = "danger btnSpacer actionBtn";
      cancelBtn.addEventListener("click", () => cancelJob(j.job_id));
      tdActions.appendChild(cancelBtn);
    }

    tr.append(tdJob, tdQuote, tdStatus, tdCustomer, tdAddress, tdTotal, tdScheduled, tdSync, tdActions);
    tbody.appendChild(tr);
  });

  box.appendChild(table);
}

function renderScheduleContext(job) {
  const summary = document.getElementById("scheduleContextSummary");
  const fields = document.getElementById("scheduleContextFields");
  if (!summary || !fields) return;

  clearNode(fields);
  if (!job) {
    summary.textContent = "Load a job to view customer booking preferences, any missing readiness details, and calendar sync context.";
    return;
  }

  const schedulingContext = job.scheduling_context || {};
  const missingFields = Array.isArray(schedulingContext.missing_fields) ? schedulingContext.missing_fields : [];
  const syncStatus = job.calendar_sync_status || "not_configured";
  const readinessLabel = schedulingContext.scheduling_ready ? "Scheduling-ready" : "Review booking preferences";
  summary.textContent = `${readinessLabel} • Customer preferences captured for ops review • Calendar sync: ${syncStatus}`;

  const rows = [
    ["Customer", job.customer_name || "—"],
    ["Phone", job.customer_phone || "—"],
    ["Service", job.service_type || "—"],
    ["Job Address", job.job_address || "—"],
    ["Requested Job Date", schedulingContext.requested_job_date || "—"],
    ["Requested Time Window", schedulingContext.requested_time_window || "—"],
    ["Booking Notes", schedulingContext.notes || "—"],
    ["Request ID", schedulingContext.request_id || job.request_id || "—"],
  ];

  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "rowToken";
    const name = document.createElement("strong");
    name.textContent = `${label}:`;
    const text = document.createElement("span");
    text.textContent = ` ${value}`;
    row.append(name, text);
    fields.appendChild(row);
  });

  if (missingFields.length > 0) {
    const missing = document.createElement("div");
    missing.className = "small muted";
    missing.textContent = `Missing booking preference fields: ${missingFields.join(", ")}. Follow up with the customer if needed before scheduling.`;
    fields.appendChild(missing);
  }

  if (job.calendar_last_error) {
    const error = document.createElement("div");
    error.className = "small muted";
    error.textContent = `Last calendar error: ${job.calendar_last_error}`;
    fields.appendChild(error);
  }
}

function showScheduleModal(jobId, isReschedule) {
  if (!adminSessionReady) {
    closeScheduleModal();
    setLine(statusLine, "bad", "Authenticate and click Refresh before scheduling jobs.");
    return;
  }
  renderScheduleContext(currentJobsById[jobId] || null);
  document.getElementById("scheduleTitle").textContent = isReschedule ? "Reschedule Job" : "Schedule Job";
  document.getElementById("scheduleModal").style.display = "block";
  const form = document.getElementById("scheduleForm");
  form.onsubmit = (e) => {
    e.preventDefault();
    const start = document.getElementById("scheduledStart").value;
    const end = document.getElementById("scheduledEnd").value;
    if (isReschedule) {
      rescheduleJob(jobId, start, end);
    } else {
      scheduleJob(jobId, start, end);
    }
  };
}

function closeScheduleModal() {
  const modal = document.getElementById("scheduleModal");
  const form = document.getElementById("scheduleForm");
  if (!modal || !form) return;
  modal.style.display = "none";
  form.reset();
  form.onsubmit = null;
  renderScheduleContext(null);
}

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const modal = document.getElementById("scheduleModal");
  if (modal && modal.style.display === "block") closeScheduleModal();
});

document.addEventListener("click", (e) => {
  const modal = document.getElementById("scheduleModal");
  if (modal && e.target === modal) closeScheduleModal();
});

async function scheduleJob(jobId, start, end) {
  try {
    const resp = await fetch(`/admin/api/jobs/${jobId}/schedule`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Basic ${btoa(`${document.getElementById("adminUsername").value}:${document.getElementById("adminPassword").value}`)}` },
      body: JSON.stringify({ scheduled_start: start, scheduled_end: end })
    });
    if (resp.ok) {
      closeScheduleModal();
      refreshAll();
    } else {
      alert("Error scheduling job: " + await resp.text());
    }
  } catch (err) {
    alert("Error: " + err);
  }
}

async function rescheduleJob(jobId, start, end) {
  try {
    const resp = await fetch(`/admin/api/jobs/${jobId}/reschedule`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Basic ${btoa(`${document.getElementById("adminUsername").value}:${document.getElementById("adminPassword").value}`)}` },
      body: JSON.stringify({ scheduled_start: start, scheduled_end: end })
    });
    if (resp.ok) {
      closeScheduleModal();
      refreshAll();
    } else {
      alert("Error rescheduling job: " + await resp.text());
    }
  } catch (err) {
    alert("Error: " + err);
  }
}

async function startJob(jobId) {
  try {
    const resp = await fetch(`/admin/api/jobs/${jobId}/start`, {
      method: "POST",
      headers: authHeaders()
    });
    if (resp.ok) {
      refreshAll();
    } else {
      alert("Error starting job: " + await resp.text());
    }
  } catch (err) {
    alert("Error: " + err);
  }
}

async function completeJob(jobId) {
  const notes = prompt("Close-out notes (optional):", "");
  if (notes === null) return;
  try {
    const resp = await fetch(`/admin/api/jobs/${jobId}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ closeout_notes: notes.trim() || null })
    });
    if (resp.ok) {
      refreshAll();
    } else {
      alert("Error completing job: " + await resp.text());
    }
  } catch (err) {
    alert("Error: " + err);
  }
}

async function cancelJob(jobId) {
  const notes = prompt("Close-out notes (optional):", "");
  if (notes === null) return;
  if (!confirm("Are you sure you want to cancel this job?")) return;
  try {
    const resp = await fetch(`/admin/api/jobs/${jobId}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ closeout_notes: notes.trim() || null })
    });
    if (resp.ok) {
      refreshAll();
    } else {
      alert("Error cancelling job: " + await resp.text());
    }
  } catch (err) {
    alert("Error: " + err);
  }
}

function parseAttachmentIds(rawValue) {
  return String(rawValue || "").split(",").map((item) => item.trim()).filter(Boolean);
}

function syncAssistantAttachmentIds(attachments) {
  const ids = (attachments || []).map((item) => item.attachment_id).filter(Boolean);
  if (assistantAttachmentIdsInput) assistantAttachmentIdsInput.value = ids.join(", ");
}

function updateAssistantDraftMeta(item) {
  currentAssistantAnalysisId = (item && item.analysis_id) || "";
  setAssistantDraftLocked(!!(item && item.quote_id));
  if (!item || !item.quote_id || !currentAssistantHandoff || currentAssistantHandoff.quote_id !== item.quote_id) {
    currentAssistantHandoff = null;
  }
  if (!assistantDraftMeta) return;
  if (!item) {
    assistantDraftMeta.textContent = "No screenshot intake guidance records yet.";
    return;
  }
  assistantDraftMeta.textContent = item.quote_id
    ? `Analysis ${item.analysis_id} • linked quote ${item.quote_id} • updated ${item.updated_at}`
    : `Analysis ${item.analysis_id} • ${item.status} • updated ${item.updated_at}`;
}

function formatMoney(value) {
  if (typeof value !== "number") return "—";
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" }).format(value);
}

function renderAssistantAutofillPanel(item) {
  const wrap = document.createElement("div");
  wrap.id = "assistantSuggestionPanel";
  wrap.className = "assistantAttachmentList";

  const title = document.createElement("strong");
  title.textContent = "Autofill Suggestions";
  wrap.appendChild(title);

  const suggestions = item.autofill_suggestions || {};
  const suggestionEntries = Object.entries(suggestions);
  if (suggestionEntries.length === 0) {
    const empty = document.createElement("div");
    empty.className = "small muted";
    empty.textContent = "No message/OCR-based intake suggestions detected.";
    wrap.appendChild(empty);
  } else {
    const helper = document.createElement("div");
    helper.className = "small muted";
    helper.textContent = "Read-only recommendation context for ops review. Customer quote changes remain in the quote intake flow.";
    wrap.appendChild(helper);

    suggestionEntries.forEach(([fieldName, meta]) => {
      const row = document.createElement("div");
      row.className = "rowToken";
      const label = document.createElement("strong");
      label.textContent = `${safeGet(assistantAutofillFieldConfig[fieldName], "label", fieldName)}:`;
      const value = document.createElement("span");
      value.textContent = ` ${safeGet(meta, "value", "—")}`;
      row.append(label, value);

      const detail = document.createElement("div");
      detail.className = "small muted";
      detail.textContent = `Confidence: ${safeGet(meta, "confidence", "low")} • Source: ${safeGet(meta, "source", "message")} • Review required`;
      wrap.append(row, detail);
    });
  }

  const missingFields = Array.isArray(item.autofill_missing_fields) ? item.autofill_missing_fields : [];
  const warnings = Array.isArray(item.autofill_warnings) ? item.autofill_warnings : [];

  if (missingFields.length > 0) {
    const missing = document.createElement("div");
    missing.id = "assistantAutofillMissingFields";
    missing.className = "small muted";
    missing.textContent = `Missing fields: ${missingFields.map((fieldName) => safeGet(assistantAutofillFieldConfig[fieldName], "label", fieldName)).join(", ")}`;
    wrap.appendChild(missing);
  }

  if (warnings.length > 0) {
    const warningList = document.createElement("div");
    warningList.id = "assistantAutofillWarnings";
    warningList.className = "small muted";
    warningList.textContent = `Warnings: ${warnings.join(" | ")}`;
    wrap.appendChild(warningList);
  }

  return wrap;
}

function renderScreenshotAssistantResult(item) {
  const box = document.getElementById("assistantResultBox");
  if (!item) {
    return addEmptyState(box, "No screenshot intake guidance record yet.");
  }
  clearNode(box);
  updateAssistantDraftMeta(item);
  syncAssistantAttachmentIds(item.attachments || []);

  const panel = document.createElement("div");
  panel.className = "assistantResultPanel";

  const title = document.createElement("h4");
  title.textContent = "Latest intake guidance snapshot";
  panel.appendChild(title);

  const meta = document.createElement("div");
  meta.className = "small muted";
  meta.textContent = `Analysis ${item.analysis_id} • ${item.status} • ${item.updated_at}`;
  panel.appendChild(meta);

  const keyGrid = document.createElement("div");
  keyGrid.className = "assistantKeyGrid";
  [
    ["Recommended Service", safeGet(item, "quote_guidance.service_type", "—")],
    ["Cash Guidance", formatMoney(safeGet(item, "quote_guidance.cash_total_cad", null))],
    ["EMT Guidance", formatMoney(safeGet(item, "quote_guidance.emt_total_cad", null))]
  ].forEach(([label, value]) => {
    const cell = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = label;
    const valueNode = document.createElement("div");
    valueNode.textContent = value;
    cell.append(strong, valueNode);
    keyGrid.appendChild(cell);
  });
  panel.appendChild(keyGrid);

  const rangeWrap = document.createElement("div");
  rangeWrap.className = "assistantAttachmentList";
  const rangeTitle = document.createElement("strong");
  rangeTitle.textContent = "Quote Range Guidance";
  rangeWrap.appendChild(rangeTitle);

  const rangeHelper = document.createElement("div");
  rangeHelper.className = "small muted";
  rangeHelper.textContent = "Recommended Target is the normal quoting recommendation. Minimum Safe is a protective lower bound, not the preferred quote.";
  rangeWrap.appendChild(rangeHelper);

  const rangeGrid = document.createElement("div");
  rangeGrid.className = "assistantKeyGrid";
  [
    ["Minimum Safe", formatMoney(safeGet(item, "quote_guidance.range.minimum_safe_cash_cad", null))],
    ["Recommended Target", formatMoney(safeGet(item, "quote_guidance.range.recommended_target_cash_cad", safeGet(item, "quote_guidance.cash_total_cad", null)))],
    ["Upper Reasonable", formatMoney(safeGet(item, "quote_guidance.range.upper_reasonable_cash_cad", null))],
    ["Confidence", safeGet(item, "quote_guidance.confidence", "—")]
  ].forEach(([label, value]) => {
    const cell = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = label;
    const valueNode = document.createElement("div");
    valueNode.textContent = value;
    cell.append(strong, valueNode);
    rangeGrid.appendChild(cell);
  });
  rangeWrap.appendChild(rangeGrid);

  const unknowns = safeGet(item, "quote_guidance.unknowns", []);
  const unknownsWrap = document.createElement("div");
  unknownsWrap.className = "small";
  unknownsWrap.textContent = Array.isArray(unknowns) && unknowns.length
    ? `Unknowns: ${unknowns.join(" | ")}`
    : "Unknowns: none flagged from the reviewed pricing inputs.";
  rangeWrap.appendChild(unknownsWrap);

  const riskNotes = safeGet(item, "quote_guidance.risk_notes", []);
  const riskWrap = document.createElement("div");
  riskWrap.className = "small";
  riskWrap.textContent = Array.isArray(riskNotes) && riskNotes.length
    ? `Risk Notes: ${riskNotes.join(" | ")}`
    : "Risk Notes: no extra margin warnings for the current reviewed draft.";
  rangeWrap.appendChild(riskWrap);

  panel.appendChild(rangeWrap);

  const disclaimer = document.createElement("div");
  disclaimer.className = "muted";
  disclaimer.textContent = safeGet(item, "quote_guidance.disclaimer", "");
  panel.appendChild(disclaimer);

  panel.appendChild(renderAssistantAutofillPanel(item));

  const attachmentWrap = document.createElement("div");
  attachmentWrap.className = "assistantAttachmentList";
  const attachmentTitle = document.createElement("strong");
  attachmentTitle.textContent = "Linked screenshots";
  attachmentWrap.appendChild(attachmentTitle);
  const attachmentBody = document.createElement("div");
  attachmentBody.className = "small";
  attachmentBody.textContent = (item.attachments || []).map((att) => att.filename || att.attachment_id).join(", ") || "None linked";
  attachmentWrap.appendChild(attachmentBody);
  panel.appendChild(attachmentWrap);

  const quoteWrap = document.createElement("div");
  quoteWrap.className = "assistantAttachmentList";
  const quoteTitle = document.createElement("strong");
  quoteTitle.textContent = "Linked quote context";
  quoteWrap.appendChild(quoteTitle);
  const quoteBody = document.createElement("div");
  quoteBody.className = "small";
  quoteBody.textContent = item.quote_id || "No linked quote.";
  quoteWrap.appendChild(quoteBody);
  panel.appendChild(quoteWrap);

  if (item.quote_id) {
    const lockNotice = document.createElement("div");
    lockNotice.className = "small muted";
    lockNotice.textContent = "Quote linkage is shown for operations context only. Quote drafting and handoff are not available in admin.";
    panel.appendChild(lockNotice);
  }

  box.appendChild(panel);
}

function renderScreenshotAssistantUploads(attachments) {
  const box = document.getElementById("assistantUploadList");
  if (!box) return;
  if (!attachments || attachments.length === 0) return addEmptyState(box, "No screenshots uploaded for this draft yet.");
  clearNode(box);

  const { table, tbody } = createTable(["Attachment", "Filename", "Type", "Size", "Uploaded", "OCR Status", "OCR Preview"]);
  attachments.forEach((item) => {
    const tr = document.createElement("tr");
    const ocrMeta = item.ocr_json || {};
    const ocrStatus = safeGet(ocrMeta, "status", "skipped");
    const ocrPreview = safeGet(ocrMeta, "preview", "");
    const ocrWarning = safeGet(ocrMeta, "warning", "");
    [
      item.attachment_id || "",
      item.filename || "",
      item.mime_type || "",
      item.size_bytes || 0,
      item.created_at || "",
      ocrStatus,
      ocrWarning ? `${ocrPreview || "—"} (${ocrWarning})` : (ocrPreview || "—"),
    ].forEach((value) => {
      const td = document.createElement("td");
      td.textContent = String(value);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  box.appendChild(table);
}

function renderScreenshotAssistantHistory(items) {
  const box = document.getElementById("assistantHistoryBox");
  if (!items || items.length === 0) return addEmptyState(box, "No screenshot intake analyses yet.");
  clearNode(box);

  const { table, tbody } = createTable(["Analysis", "Updated", "Service", "Cash", "Quote", "Attachments", "Mode"]);
  items.forEach((item) => {
    const tr = document.createElement("tr");
    const attachmentIds = safeGet(item, "intake.screenshot_attachment_ids", []);
    [
      item.analysis_id || "",
      item.updated_at || "",
      safeGet(item, "quote_guidance.service_type", ""),
      formatMoney(safeGet(item, "quote_guidance.cash_total_cad", null)),
      item.quote_id || "—",
      Array.isArray(attachmentIds) ? attachmentIds.length : 0,
      item.recommendation_only ? "Recommendation only" : "—"
    ].forEach((value) => {
      const td = document.createElement("td");
      td.textContent = String(value);
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  box.appendChild(table);
}

async function refreshAll() {
  const { username, password } = getAdminCreds();
  if (!username || !password) {
    resetProtectedDashboard();
    setLine(statusLine, "bad", "Enter both admin username and password, then press Enter or click Log In & Load Data.");
    return;
  }

  try {

    adminSessionReady = false;
    closeScheduleModal();
    setProtectedDashboardVisible(false);
    setLoading(true);
    statusLine.textContent = "Authenticating and loading admin data...";

    const quotes = await fetchJSON("/admin/api/quotes");
    renderQuotes((quotes.items || []));

    const reqs = await fetchJSON("/admin/api/quote-requests");
    renderRequests((reqs.items || []));

    const jobs = await fetchJSON("/admin/api/jobs");
    renderJobs((jobs.items || []));

    const auditLog = await fetchJSON("/admin/api/audit-log");
    renderAuditLog((auditLog.items || []));

    adminSessionReady = true;
    const analyses = await fetchJSON("/admin/api/screenshot-assistant/analyses");
    const analysisItems = analyses.items || [];
    renderScreenshotAssistantHistory(analysisItems);
    if (analysisItems[0] && analysisItems[0].analysis_id) {
      const latestAnalysis = await fetchJSON(`/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisItems[0].analysis_id)}`);
      renderScreenshotAssistantResult(latestAnalysis);
      renderScreenshotAssistantUploads(latestAnalysis.attachments || []);
    } else {
      renderScreenshotAssistantResult(null);
      renderScreenshotAssistantUploads([]);
    }

    setProtectedDashboardVisible(true);
    setLine(statusLine, "ok", "Admin data loaded successfully.");
  } catch (err) {
    adminSessionReady = false;
    closeScheduleModal();
    resetProtectedDashboard();
    const parsed = parseApiError(err);
    const detail = safeGet(parsed, "data.detail", "");

    if (parsed.status === 401 && String(detail).toLowerCase().includes("not configured")) {
      setLine(statusLine, "bad", "Admin login is not configured on the server. Set ADMIN_USERNAME and ADMIN_PASSWORD.", "HTTP 401");
    } else if (parsed.status === 401) {
      setLine(statusLine, "bad", "Login failed. Check admin username/password and try again.", "HTTP 401");
    } else if (parsed.status === 429) {
      setLine(statusLine, "bad", "Too many failed login attempts. Wait a few minutes, then try again.", "HTTP 429");
    } else if (parsed.status) {
      setLine(statusLine, "bad", "Admin API error. " + (detail || "Please try again."), "HTTP " + parsed.status);
    } else {
      setLine(statusLine, "bad", "Admin API error. " + parsed.raw);
    }
  } finally {
    setLoading(false);
  }
}

function handleCredsKeydown(e) {
  if (e.key !== "Enter") return;
  e.preventDefault();
  refreshAll();
}

refreshBtn.addEventListener("click", refreshAll);
adminUsernameInput.addEventListener("keydown", handleCredsKeydown);
adminPasswordInput.addEventListener("keydown", handleCredsKeydown);
if (scheduleCloseBtn) scheduleCloseBtn.addEventListener("click", closeScheduleModal);
if (scheduleCancelBtn) scheduleCancelBtn.addEventListener("click", closeScheduleModal);

resetProtectedDashboard();
closeScheduleModal();
setLoading(false);

// On first load, we don't auto-refresh with empty creds.
setLine(statusLine, "bad", "Enter admin username/password, then press Enter or click Log In & Load Data.");
