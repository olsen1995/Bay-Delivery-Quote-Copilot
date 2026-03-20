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
const assistantStartDraftBtn = document.getElementById("assistantStartDraftBtn");
const assistantUploadBtn = document.getElementById("assistantUploadBtn");
const assistantAnalyzeBtn = document.getElementById("assistantAnalyzeBtn");
const assistantStatusLine = document.getElementById("assistantStatusLine");
const assistantDraftMeta = document.getElementById("assistantDraftMeta");
const assistantAttachmentIdsInput = document.getElementById("assistantAttachmentIds");
const assistantScreenshotFilesInput = document.getElementById("assistantScreenshotFiles");
const assistantMessageInput = document.getElementById("assistantMessage");
const assistantServiceTypeInput = document.getElementById("assistantServiceType");
const assistantEstimatedHoursInput = document.getElementById("assistantEstimatedHours");
const assistantCrewSizeInput = document.getElementById("assistantCrewSize");
const assistantJobAddressInput = document.getElementById("assistantJobAddress");
const assistantPickupAddressInput = document.getElementById("assistantPickupAddress");
const assistantDropoffAddressInput = document.getElementById("assistantDropoffAddress");
const refreshButtonLabel = "Log In & Load Data";
let adminSessionReady = false;
let currentAssistantAnalysisId = "";
let currentAssistantLocked = false;
let currentAssistantHandoff = null;
let currentJobsById = {};

function assistantDraftFields() {
  return [
    assistantMessageInput,
    assistantAttachmentIdsInput,
    assistantScreenshotFilesInput,
    assistantServiceTypeInput,
    assistantEstimatedHoursInput,
    assistantCrewSizeInput,
    assistantJobAddressInput,
    assistantPickupAddressInput,
    assistantDropoffAddressInput
  ].filter(Boolean);
}

function setAssistantDraftLocked(isLocked) {
  currentAssistantLocked = !!isLocked;
  if (assistantUploadBtn) assistantUploadBtn.disabled = currentAssistantLocked;
  if (assistantAnalyzeBtn) assistantAnalyzeBtn.disabled = currentAssistantLocked;
  assistantDraftFields().forEach((field) => {
    field.disabled = currentAssistantLocked;
  });
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
  if (assistantStartDraftBtn) assistantStartDraftBtn.disabled = isLoading;
  if (assistantUploadBtn) assistantUploadBtn.disabled = isLoading || currentAssistantLocked;
  if (assistantAnalyzeBtn) assistantAnalyzeBtn.disabled = isLoading || currentAssistantLocked;
  assistantDraftFields().forEach((field) => {
    field.disabled = isLoading || currentAssistantLocked;
  });
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
  setAssistantDraftLocked(false);
  if (assistantDraftMeta) assistantDraftMeta.textContent = "No draft analysis yet. Uploading screenshots will create one automatically.";
  if (assistantAttachmentIdsInput) assistantAttachmentIdsInput.value = "";
  if (assistantScreenshotFilesInput) assistantScreenshotFilesInput.value = "";
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

function renderQuotes(items) {
  const box = document.getElementById("quotesBox");
  if (!items || items.length === 0) return addEmptyState(box, "No quotes yet.");
  clearNode(box);

  const { table, tbody } = createTable(["Quote", "Status", "Customer", "Service", "Address", "Estimated"]);

  items.forEach((q) => {
    const tr = document.createElement("tr");

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
    tr.append(tdId, tdStatus, tdCustomer, tdSvc, tdAddress, tdTotal);
    tbody.appendChild(tr);
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
    if (j.status !== "cancelled") {
      if (!j.scheduled_start) {
        // Schedule button
        const scheduleBtn = document.createElement("button");
        scheduleBtn.type = "button";
        scheduleBtn.className = "actionBtn";
        scheduleBtn.textContent = "Schedule";
        scheduleBtn.addEventListener("click", () => showScheduleModal(j.job_id, false));
        tdActions.appendChild(scheduleBtn);
      } else {
        // Reschedule and Cancel buttons
        const rescheduleBtn = document.createElement("button");
        rescheduleBtn.type = "button";
        rescheduleBtn.className = "actionBtn";
        rescheduleBtn.textContent = "Reschedule";
        rescheduleBtn.addEventListener("click", () => showScheduleModal(j.job_id, true));
        tdActions.appendChild(rescheduleBtn);

        const cancelBtn = document.createElement("button");
        cancelBtn.type = "button";
        cancelBtn.textContent = "Cancel";
        cancelBtn.className = "danger btnSpacer actionBtn";
        cancelBtn.addEventListener("click", () => cancelJob(j.job_id));
        tdActions.appendChild(cancelBtn);
      }
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
    summary.textContent = "Load a job to view customer booking preferences and calendar sync details.";
    return;
  }

  const schedulingContext = job.scheduling_context || {};
  const missingFields = Array.isArray(schedulingContext.missing_fields) ? schedulingContext.missing_fields : [];
  const syncStatus = job.calendar_sync_status || "not_configured";
  const readinessLabel = schedulingContext.scheduling_ready ? "Scheduling-ready" : "Review booking preferences";
  summary.textContent = `${readinessLabel} • Calendar sync: ${syncStatus}`;

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
    missing.textContent = `Missing booking preference fields: ${missingFields.join(", ")}`;
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

async function cancelJob(jobId) {
  if (!confirm("Are you sure you want to cancel this job?")) return;
  try {
    const resp = await fetch(`/admin/api/jobs/${jobId}/cancel`, {
      method: "POST",
      headers: { "Authorization": `Basic ${btoa(`${document.getElementById("adminUsername").value}:${document.getElementById("adminPassword").value}`)}` }
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
    assistantDraftMeta.textContent = "No draft analysis yet. Uploading screenshots will create one automatically.";
    return;
  }
  assistantDraftMeta.textContent = item.quote_id
    ? `Analysis ${item.analysis_id} • locked to quote ${item.quote_id} • updated ${item.updated_at}`
    : `Analysis ${item.analysis_id} • ${item.status} • updated ${item.updated_at}`;
}

function beginNewScreenshotAssistantDraft() {
  currentAssistantAnalysisId = "";
  currentAssistantHandoff = null;
  setAssistantDraftLocked(false);
  updateAssistantDraftMeta(null);
  if (assistantAttachmentIdsInput) assistantAttachmentIdsInput.value = "";
  if (assistantScreenshotFilesInput) assistantScreenshotFilesInput.value = "";
  const resultBox = document.getElementById("assistantResultBox");
  const uploadList = document.getElementById("assistantUploadList");
  if (resultBox) clearNode(resultBox);
  if (uploadList) clearNode(uploadList);
  setLine(assistantStatusLine, "ok", "Fresh screenshot draft ready. Analyze intake or upload screenshots to create it.");
}

function collectAssistantPayload() {
  const candidate = {};
  const serviceType = (document.getElementById("assistantServiceType").value || "").trim();
  const estimatedHours = (document.getElementById("assistantEstimatedHours").value || "").trim();
  const crewSize = (document.getElementById("assistantCrewSize").value || "").trim();
  const jobAddress = (document.getElementById("assistantJobAddress").value || "").trim();
  const pickupAddress = (document.getElementById("assistantPickupAddress").value || "").trim();
  const dropoffAddress = (document.getElementById("assistantDropoffAddress").value || "").trim();

  if (serviceType) candidate.service_type = serviceType;
  if (estimatedHours) candidate.estimated_hours = Number(estimatedHours);
  if (crewSize) candidate.crew_size = Number(crewSize);
  if (jobAddress) candidate.job_address = jobAddress;
  if (pickupAddress) candidate.pickup_address = pickupAddress;
  if (dropoffAddress) candidate.dropoff_address = dropoffAddress;

  return {
    analysis_id: currentAssistantAnalysisId || undefined,
    message: (document.getElementById("assistantMessage").value || "").trim(),
    screenshot_attachment_ids: parseAttachmentIds(assistantAttachmentIdsInput ? assistantAttachmentIdsInput.value : ""),
    candidate_inputs: candidate,
    operator_overrides: {}
  };
}

function formatMoney(value) {
  if (typeof value !== "number") return "—";
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" }).format(value);
}

function renderScreenshotAssistantResult(item) {
  const box = document.getElementById("assistantResultBox");
  if (!item) return addEmptyState(box, "No screenshot analysis yet.");
  clearNode(box);
  updateAssistantDraftMeta(item);
  syncAssistantAttachmentIds(item.attachments || []);

  const panel = document.createElement("div");
  panel.className = "assistantResultPanel";

  const title = document.createElement("h4");
  title.textContent = "Latest draft analysis";
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

  const disclaimer = document.createElement("div");
  disclaimer.className = "muted";
  disclaimer.textContent = safeGet(item, "quote_guidance.disclaimer", "");
  panel.appendChild(disclaimer);

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
  quoteTitle.textContent = "Linked quote draft";
  quoteWrap.appendChild(quoteTitle);
  const quoteBody = document.createElement("div");
  quoteBody.className = "small";
  quoteBody.textContent = item.quote_id || "No quote draft created yet.";
  quoteWrap.appendChild(quoteBody);
  panel.appendChild(quoteWrap);

  if (item.quote_id) {
    const lockNotice = document.createElement("div");
    lockNotice.className = "small muted";
    lockNotice.textContent = "This analysis is locked because a quote draft has already been created.";
    panel.appendChild(lockNotice);

    const handoffRow = document.createElement("div");
    handoffRow.className = "rowToken mt10 assistantActions";
    const handoffHelper = document.createElement("div");
    handoffHelper.className = "small";
    handoffHelper.textContent = "Prepare a normal customer handoff only after the quote draft is final.";
    const handoffBtn = document.createElement("button");
    handoffBtn.id = "assistantPrepareHandoffBtn";
    handoffBtn.className = "secondaryAction";
    handoffBtn.type = "button";
    handoffBtn.textContent = "Prepare Customer Handoff";
    handoffBtn.disabled = !adminSessionReady;
    handoffBtn.addEventListener("click", () => prepareCustomerHandoff(item.quote_id || ""));
    handoffRow.append(handoffHelper, handoffBtn);
    panel.appendChild(handoffRow);

    if (currentAssistantHandoff && currentAssistantHandoff.quote_id === item.quote_id) {
      const handoffWrap = document.createElement("div");
      handoffWrap.className = "assistantAttachmentList";
      const handoffTitle = document.createElement("strong");
      handoffTitle.textContent = "Customer handoff";
      handoffWrap.appendChild(handoffTitle);

      const handoffMeta = document.createElement("div");
      handoffMeta.className = "small";
      handoffMeta.textContent = `Request ${currentAssistantHandoff.request_id} • ${currentAssistantHandoff.status}${currentAssistantHandoff.already_existed ? " • existing request reused" : ""}`;
      handoffWrap.appendChild(handoffMeta);

      const handoffUrl = document.createElement("code");
      handoffUrl.textContent = currentAssistantHandoff.handoff_url || "";
      handoffWrap.appendChild(handoffUrl);
      panel.appendChild(handoffWrap);
    }
  }

  if (!item.quote_id) {
    const actionRow = document.createElement("div");
    actionRow.className = "rowToken mt10 assistantActions";
    const helper = document.createElement("div");
    helper.className = "small";
    helper.textContent = "Create a real quote draft only after reviewing the recommendation.";
    const button = document.createElement("button");
    button.id = "assistantCreateQuoteDraftBtn";
    button.className = "secondaryAction";
    button.type = "button";
    button.textContent = "Create Quote Draft";
    button.disabled = !adminSessionReady;
    button.addEventListener("click", () => createQuoteDraftFromAnalysis(item.analysis_id || ""));
    actionRow.append(helper, button);
    panel.appendChild(actionRow);
  }

  box.appendChild(panel);
}

function renderScreenshotAssistantUploads(attachments) {
  const box = document.getElementById("assistantUploadList");
  if (!box) return;
  if (!attachments || attachments.length === 0) return addEmptyState(box, "No screenshots uploaded for this draft yet.");
  clearNode(box);

  const { table, tbody } = createTable(["Attachment", "Filename", "Type", "Size", "Uploaded"]);
  attachments.forEach((item) => {
    const tr = document.createElement("tr");
    [
      item.attachment_id || "",
      item.filename || "",
      item.mime_type || "",
      item.size_bytes || 0,
      item.created_at || ""
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
  if (!items || items.length === 0) return addEmptyState(box, "No screenshot assistant drafts yet.");
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

async function saveScreenshotAssistantDraft() {
  if (!adminSessionReady) {
    setLine(assistantStatusLine, "bad", "Authenticate and load admin data before using Screenshot Quote Assistant.");
    throw new Error("admin auth required");
  }

  const resp = await fetch("/admin/api/screenshot-assistant/analyses/intake", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(collectAssistantPayload())
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw { status: resp.status, data, raw: JSON.stringify(data) };
  renderScreenshotAssistantResult(data);
  renderScreenshotAssistantUploads(data.attachments || []);
  return data;
}

async function submitScreenshotAssistantAnalysis() {
  try {
    setLoading(true);
    setLine(assistantStatusLine, "ok", "Analyzing intake draft...");
    await saveScreenshotAssistantDraft();
    setLine(assistantStatusLine, "ok", "Draft analysis saved. Pricing guidance reused the existing quote engine.");

    const analyses = await fetchJSON("/admin/api/screenshot-assistant/analyses");
    renderScreenshotAssistantHistory((analyses.items || []));
  } catch (err) {
    const parsed = parseApiError(err);
    const detail = safeGet(parsed, "data.detail", "Please review the intake fields and try again.");
    setLine(assistantStatusLine, "bad", "Screenshot assistant error. " + detail, parsed.status ? `HTTP ${parsed.status}` : undefined);
  } finally {
    setLoading(false);
  }
}

async function uploadScreenshotAssistantFiles() {
  if (!adminSessionReady) {
    setLine(assistantStatusLine, "bad", "Authenticate and load admin data before uploading screenshots.");
    return;
  }

  const selectedFiles = Array.from((assistantScreenshotFilesInput && assistantScreenshotFilesInput.files) || []);
  if (selectedFiles.length === 0) {
    setLine(assistantStatusLine, "bad", "Choose at least one screenshot before uploading.");
    return;
  }

  try {
    setLoading(true);
    setLine(assistantStatusLine, "ok", "Preparing screenshot upload...");

    let analysisId = currentAssistantAnalysisId;
    if (!analysisId) {
      const draft = await saveScreenshotAssistantDraft();
      analysisId = draft.analysis_id || "";
    }

    const formData = new FormData();
    selectedFiles.forEach((file) => formData.append("files", file));

    const resp = await fetch(`/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisId)}/attachments`, {
      method: "POST",
      headers: authHeaders(),
      body: formData
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw { status: resp.status, data, raw: JSON.stringify(data) };

    syncAssistantAttachmentIds(data.attachments || []);
    renderScreenshotAssistantUploads(data.attachments || []);
    if (assistantScreenshotFilesInput) assistantScreenshotFilesInput.value = "";

    const refreshed = await fetchJSON(`/admin/api/screenshot-assistant/analyses/${encodeURIComponent(data.analysis_id)}`);
    renderScreenshotAssistantResult(refreshed);

    const analyses = await fetchJSON("/admin/api/screenshot-assistant/analyses");
    renderScreenshotAssistantHistory((analyses.items || []));
    setLine(assistantStatusLine, "ok", `Uploaded ${Array.isArray(data.uploaded) ? data.uploaded.length : 0} screenshot(s) to the current draft.`);
  } catch (err) {
    const parsed = parseApiError(err);
    const detail = safeGet(parsed, "data.detail", "Please review the files and try again.");
    setLine(assistantStatusLine, "bad", "Screenshot upload failed. " + detail, parsed.status ? `HTTP ${parsed.status}` : undefined);
  } finally {
    setLoading(false);
  }
}

async function createQuoteDraftFromAnalysis(analysisId) {
  if (!adminSessionReady) {
    setLine(assistantStatusLine, "bad", "Authenticate and load admin data before creating a quote draft.");
    return;
  }
  if (!analysisId) {
    setLine(assistantStatusLine, "bad", "Create or load a screenshot analysis before creating a quote draft.");
    return;
  }

  try {
    setLoading(true);
    setLine(assistantStatusLine, "ok", "Creating quote draft from reviewed analysis...");

    const resp = await fetch(`/admin/api/screenshot-assistant/analyses/${encodeURIComponent(analysisId)}/quote-draft`, {
      method: "POST",
      headers: authHeaders()
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw { status: resp.status, data, raw: JSON.stringify(data) };

    renderScreenshotAssistantResult(data.analysis || null);
    renderScreenshotAssistantUploads((data.analysis && data.analysis.attachments) || []);

    const analyses = await fetchJSON("/admin/api/screenshot-assistant/analyses");
    renderScreenshotAssistantHistory((analyses.items || []));

    const quotes = await fetchJSON("/admin/api/quotes");
    renderQuotes((quotes.items || []));

    const createdQuoteId = safeGet(data, "quote.quote_id", "");
    setLine(assistantStatusLine, "ok", `Quote draft ${createdQuoteId || "created"} linked to the current analysis.`);
  } catch (err) {
    const parsed = parseApiError(err);
    const detail = safeGet(parsed, "data.detail", "Please review the draft and try again.");
    setLine(assistantStatusLine, "bad", "Quote draft creation failed. " + detail, parsed.status ? `HTTP ${parsed.status}` : undefined);
  } finally {
    setLoading(false);
  }
}

async function prepareCustomerHandoff(quoteId) {
  if (!adminSessionReady) {
    setLine(assistantStatusLine, "bad", "Authenticate and load admin data before preparing customer handoff.");
    return;
  }
  if (!quoteId) {
    setLine(assistantStatusLine, "bad", "Create a linked quote draft before preparing customer handoff.");
    return;
  }

  try {
    setLoading(true);
    setLine(assistantStatusLine, "ok", "Preparing customer handoff...");

    const resp = await fetch(`/admin/api/quotes/${encodeURIComponent(quoteId)}/handoff`, {
      method: "POST",
      headers: authHeaders()
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw { status: resp.status, data, raw: JSON.stringify(data) };

    currentAssistantHandoff = data;

    if (currentAssistantAnalysisId) {
      const refreshed = await fetchJSON(`/admin/api/screenshot-assistant/analyses/${encodeURIComponent(currentAssistantAnalysisId)}`);
      renderScreenshotAssistantResult(refreshed);
    }

    const reqs = await fetchJSON("/admin/api/quote-requests");
    renderRequests((reqs.items || []));

    setLine(assistantStatusLine, "ok", `Customer handoff ready for request ${data.request_id}.`, data.handoff_url || undefined);
  } catch (err) {
    const parsed = parseApiError(err);
    const detail = safeGet(parsed, "data.detail", "Please review the quote draft and try again.");
    setLine(assistantStatusLine, "bad", "Customer handoff failed. " + detail, parsed.status ? `HTTP ${parsed.status}` : undefined);
  } finally {
    setLoading(false);
  }
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

    const analyses = await fetchJSON("/admin/api/screenshot-assistant/analyses");
    const analysisItems = analyses.items || [];
    renderScreenshotAssistantHistory(analysisItems);
    renderScreenshotAssistantResult(analysisItems[0] || null);
    renderScreenshotAssistantUploads((analysisItems[0] && analysisItems[0].attachments) || []);

    adminSessionReady = true;
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
if (assistantStartDraftBtn) assistantStartDraftBtn.addEventListener("click", beginNewScreenshotAssistantDraft);
if (assistantUploadBtn) assistantUploadBtn.addEventListener("click", uploadScreenshotAssistantFiles);
if (assistantAnalyzeBtn) assistantAnalyzeBtn.addEventListener("click", submitScreenshotAssistantAnalysis);

resetProtectedDashboard();
closeScheduleModal();
setLoading(false);

// On first load, we don't auto-refresh with empty creds.
setLine(statusLine, "bad", "Enter admin username/password, then press Enter or click Log In & Load Data.");
