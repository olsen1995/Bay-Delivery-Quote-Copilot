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
    tdRec.appendChild(createAdminIdCode(entry.record_id));
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

function formatAdminDisplayId(value) {
  const normalized = String(value || "").trim();
  if (!normalized) return "";
  if (normalized.length <= 8) return normalized;
  return `${normalized.slice(0, 8)}…`;
}

function createAdminIdCode(value) {
  const code = document.createElement("code");
  const normalized = String(value || "").trim();
  code.className = "adminDisplayId";
  code.textContent = formatAdminDisplayId(normalized);
  if (normalized) {
    code.title = normalized;
    code.dataset.fullId = normalized;
  }
  return code;
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
const followupMessageScenarioSelect = document.getElementById("followupMessageScenario");
const followupMessageFormatSelect = document.getElementById("followupMessageFormat");
const followupMessageContextSelect = document.getElementById("followupMessageContext");
const followupMessageContextSummary = document.getElementById("followupMessageContextSummary");
const followupMessageDraftInput = document.getElementById("followupMessageDraft");
const followupMessageCopyBtn = document.getElementById("followupMessageCopyBtn");
const followupMessageStatusLine = document.getElementById("followupMessageStatusLine");
const refreshButtonLabel = "Log In & Load Data";
let adminSessionReady = false;
let currentAssistantAnalysisId = "";
let currentAssistantHandoff = null;
let currentRequestItems = [];
let currentJobItems = [];
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
const quoteRequestFollowupOptions = [
  ["needs_followup", "Needs follow-up"],
  ["contacted", "Contacted"],
  ["waiting_on_customer", "Waiting on customer"],
  ["not_ready", "Not ready"],
  ["closed_no_followup", "Closed - no follow-up"]
];
const followupMessageFormatOptions = [
  ["text", "Text message"],
  ["email", "Email"]
];
const followupMessageScenarioCatalog = [
  { key: "need_photos", label: "Need photos", audience: "customer" },
  { key: "no_reply", label: "No reply / gentle follow-up", audience: "customer" },
  { key: "accepted_not_booked", label: "Accepted but not booked", audience: "customer" },
  { key: "need_access_details", label: "Need access details", audience: "customer" },
  { key: "price_concern", label: "Price concern / customer asking cheaper", audience: "customer" },
  { key: "completed_followup", label: "Completed job follow-up", audience: "customer" },
  { key: "review_request", label: "Review request", audience: "customer" },
  { key: "manual_review", label: "Manual review / unclear job", audience: "customer" },
  { key: "missing_completed_job_cost_info", label: "Missing completed-job cost info", audience: "admin" }
];
const dailyOpsBoardCardKeys = [
  "new_requests",
  "needs_followup",
  "accepted_not_booked",
  "upcoming_jobs",
  "completed_missing_costs",
  "owner_review",
  "stale_quotes"
];
const structuredIntakeFields = [
  ["stairs_count", "Stairs"],
  ["floor_count", "Floors above/below entry"],
  ["basement_or_inside_removal", "Basement/inside removal"],
  ["demolition_ripout", "Demolition/rip-out"],
  ["construction_debris_type", "Construction debris"],
  ["dense_material_type", "Dense material"],
  ["mixed_load", "Mixed load"],
  ["contains_scrap", "Contains scrap"],
  ["contains_garbage", "Contains garbage"],
  ["has_refrigerant_appliance", "Refrigerant appliance"],
  ["appliance_type", "Appliance type"],
  ["weather_protection_required", "Weather protection"]
];
const structuredIntakeLabels = {
  drywall: "Drywall",
  wood: "Wood",
  tile: "Tile",
  concrete: "Concrete",
  shingles: "Shingles",
  soil: "Soil",
  brick: "Brick",
  stone: "Stone",
  mixed: "Mixed",
  other: "Other",
  fridge: "Fridge",
  freezer: "Freezer",
  air_conditioner: "Air conditioner",
  dehumidifier: "Dehumidifier",
  washer: "Washer",
  dryer: "Dryer",
  stove: "Stove",
  dishwasher: "Dishwasher",
  water_heater: "Water heater",
  double_axle_open_aluminum: "Double axle open aluminum",
  newer_enclosed: "Newer enclosed"
};

const friendlyServiceLabels = {
  haul_away: "junk removal job",
  scrap_pickup: "scrap pickup",
  small_move: "move",
  item_delivery: "delivery",
  demolition: "demolition job",
  dump_run: "junk removal job",
  delivery: "delivery"
};

function populateSelectOptions(select, options, selectedValue) {
  if (!select) return;
  clearNode(select);
  options.forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  });
  if (selectedValue && options.some(([value]) => value === selectedValue)) {
    select.value = selectedValue;
  } else if (options[0]) {
    select.value = options[0][0];
  }
}

function sentenceCase(value) {
  const normalized = String(value || "").trim();
  if (!normalized) return "";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function firstName(value) {
  return String(value || "").trim().split(/\s+/)[0] || "";
}

function friendlyServiceLabel(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return friendlyServiceLabels[normalized] || (normalized ? normalized.replace(/_/g, " ") : "job");
}

function friendlyWindowLabel(value) {
  const normalized = String(value || "").trim().toLowerCase();
  const map = {
    morning: "morning",
    afternoon: "afternoon",
    evening: "evening",
    flexible: "a flexible time"
  };
  return map[normalized] || normalized.replace(/_/g, " ");
}

function formatIsoDate(dateValue) {
  const normalized = String(dateValue || "").trim();
  if (!normalized) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
    const date = new Date(`${normalized}T12:00:00`);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    }
  }
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return normalized;
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function safeTrimmed(value) {
  return String(value || "").trim();
}

function normalizeBooleanLike(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "yes", "y", "1", "on"].includes(normalized)) return true;
    if (["false", "no", "n", "0", "off", ""].includes(normalized)) return false;
    return false;
  }
  return false;
}

function compactContextCustomerName(context) {
  return safeTrimmed(context.customer_name) || "";
}

function buildFollowupGreeting(context) {
  const name = firstName(compactContextCustomerName(context));
  return name ? `Hi ${name},` : "Hi,";
}

function buildFollowupClosing(format) {
  return format === "email" ? "Thanks,\nBay Delivery" : "Thanks, Bay Delivery";
}

function describeDraftContext(context) {
  const parts = [];
  if (context.kind === "request") parts.push("Booking request context");
  if (context.kind === "job") parts.push("Job context");
  if (context.kind === "general") parts.push("General draft");
  if (context.customer_name) parts.push(context.customer_name);
  if (context.service_type) parts.push(sentenceCase(friendlyServiceLabel(context.service_type)));
  if (context.job_address) parts.push(context.job_address);
  if (context.requested_job_date) {
    const dateLabel = formatIsoDate(context.requested_job_date);
    const windowLabel = friendlyWindowLabel(context.requested_time_window);
    if (dateLabel && windowLabel) parts.push(`${dateLabel} (${windowLabel})`);
    else if (dateLabel) parts.push(dateLabel);
  } else if (context.scheduled_start) {
    parts.push(`Scheduled ${formatIsoDate(context.scheduled_start)}`);
  } else if (context.completed_at) {
    parts.push(`Completed ${formatIsoDate(context.completed_at)}`);
  }
  return parts.join(" • ") || "Using a general draft. Load requests or jobs to reuse existing admin context.";
}

function buildPhotosPrompt(requestJson) {
  const request = requestJson && typeof requestJson === "object" ? requestJson : {};
  const prompts = [];
  const stairsCount = Number(request.stairs_count || 0);
  const floorCount = Number(request.floor_count || 0);
  const hasInsideRemoval = normalizeBooleanLike(request.basement_or_inside_removal);
  if (stairsCount > 0 || floorCount > 0 || hasInsideRemoval) {
    prompts.push("stairs, basement or inside access");
  }
  if (safeTrimmed(request.access_difficulty) === "difficult" || safeTrimmed(request.access_difficulty) === "extreme") {
    prompts.push("apartment, elevator, or long-carry details");
  }
  return prompts;
}

function buildAccessPrompt(requestJson) {
  const request = requestJson && typeof requestJson === "object" ? requestJson : {};
  const prompts = [];
  const stairsCount = Number(request.stairs_count || 0);
  const floorCount = Number(request.floor_count || 0);
  const hasInsideRemoval = normalizeBooleanLike(request.basement_or_inside_removal);
  if (stairsCount > 0) prompts.push(`${stairsCount} stair set${stairsCount === 1 ? "" : "s"}`);
  if (floorCount > 0) prompts.push(`${floorCount} floor${floorCount === 1 ? "" : "s"} from entry`);
  if (hasInsideRemoval) prompts.push("inside or basement removal");
  if (!prompts.length) {
    prompts.push("stairs, apartment or elevator access, basement access, long carry, and parking/loading details");
  }
  return prompts;
}

function getMissingCompletedCostFields(context) {
  const fields = [];
  if (context.kind !== "job") return fields;
  if (nullableNumber(context.actual_labor_cost_cad) === null) fields.push("actual labour cost");
  if (nullableNumber(context.actual_disposal_cost_cad) === null) fields.push("actual disposal cost");
  if (nullableNumber(context.actual_fuel_cost_cad) === null) fields.push("actual fuel cost");
  if (nullableNumber(context.actual_other_costs_cad) === null) fields.push("actual other costs");
  if (nullableNumber(context.final_amount_collected_cad) === null) fields.push("final amount collected");
  if (!safeTrimmed(context.payment_status)) fields.push("payment status");
  return fields;
}

function joinList(values) {
  const items = values.filter((value) => safeTrimmed(value));
  if (!items.length) return "";
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

function createFollowupContextOptions() {
  const options = [{ value: "general", label: "General / no selected context" }];
  currentRequestItems.forEach((item) => {
    const labelParts = [compactContextCustomerName(item) || item.request_id || "Request", sentenceCase(friendlyServiceLabel(item.service_type))];
    if (item.requested_job_date) labelParts.push(formatIsoDate(item.requested_job_date));
    options.push({ value: `request:${item.request_id || ""}`, label: `Request: ${labelParts.filter(Boolean).join(" • ")}` });
  });
  currentJobItems.forEach((item) => {
    const labelParts = [compactContextCustomerName(item) || item.job_id || "Job", sentenceCase(friendlyServiceLabel(item.service_type))];
    if (item.completed_at) labelParts.push(`Completed ${formatIsoDate(item.completed_at)}`);
    else if (item.scheduled_start) labelParts.push(`Scheduled ${formatIsoDate(item.scheduled_start)}`);
    else labelParts.push(statusLabel(item.status));
    options.push({ value: `job:${item.job_id || ""}`, label: `Job: ${labelParts.filter(Boolean).join(" • ")}` });
  });
  return options;
}

function getFollowupContextByValue(value) {
  const normalized = safeTrimmed(value);
  if (!normalized || normalized === "general") {
    return { kind: "general" };
  }
  const [kind, id] = normalized.split(":", 2);
  if (kind === "request") {
    const item = currentRequestItems.find((entry) => entry.request_id === id);
    return item ? { kind: "request", ...item } : { kind: "general" };
  }
  if (kind === "job") {
    const item = currentJobItems.find((entry) => entry.job_id === id);
    return item ? { kind: "job", ...item } : { kind: "general" };
  }
  return { kind: "general" };
}

function buildCustomerDraft(scenarioKey, format, context) {
  const greeting = buildFollowupGreeting(context);
  const closing = buildFollowupClosing(format);
  const serviceLabel = friendlyServiceLabel(context.service_type);
  const dateLabel = formatIsoDate(context.requested_job_date);
  const windowLabel = friendlyWindowLabel(context.requested_time_window);
  const photoPrompts = buildPhotosPrompt(context.request_json);
  const accessPrompts = buildAccessPrompt(context.request_json);

  if (scenarioKey === "need_photos") {
    const extraPrompt = photoPrompts.length ? ` If you can, please also mention ${joinList(photoPrompts)}.` : " If you can, please also mention whether the items are inside or outside and any stairs or access details.";
    if (format === "email") {
      return `${greeting}\n\nThanks for reaching out to Bay Delivery about your ${serviceLabel}. To give you a solid quote, could you send 2-4 clear photos of the items or area when you have a minute?${extraPrompt}\n\n${closing}`;
    }
    return `${greeting} Thanks for reaching out to Bay Delivery about your ${serviceLabel}. Could you send 2-4 clear photos of the items or area?${extraPrompt} ${closing}`;
  }

  if (scenarioKey === "no_reply") {
    if (format === "email") {
      return `${greeting}\n\nJust checking in on your Bay Delivery estimate for the ${serviceLabel}. If you still want to move ahead, send a quick reply and we will take the next step from there. No rush.\n\n${closing}`;
    }
    return `${greeting} Just checking in on your Bay Delivery estimate for the ${serviceLabel}. If you still want to move ahead, send a quick reply and we will take the next step from there. No rush. ${closing}`;
  }

  if (scenarioKey === "accepted_not_booked") {
    const timePrompt = dateLabel && windowLabel ? `You mentioned ${dateLabel} in the ${windowLabel}.` : "If you still want to book it, send a couple of days and times that work best for you.";
    if (format === "email") {
      return `${greeting}\n\nThanks for accepting the estimate for your ${serviceLabel}. ${timePrompt} We can confirm the booking once we have the timing details from you.\n\n${closing}`;
    }
    return `${greeting} Thanks for accepting the estimate for your ${serviceLabel}. ${timePrompt} We can confirm the booking once we have the timing details from you. ${closing}`;
  }

  if (scenarioKey === "need_access_details") {
    const accessSummary = joinList(accessPrompts);
    if (format === "email") {
      return `${greeting}\n\nBefore we lock this in, could you confirm a couple of access details for the ${serviceLabel}? Please let us know about ${accessSummary}. That helps Bay Delivery plan the right crew and timing.\n\n${closing}`;
    }
    return `${greeting} Before we lock this in, could you confirm a couple of access details for the ${serviceLabel}? Please let us know about ${accessSummary}. That helps Bay Delivery plan the right crew and timing. ${closing}`;
  }

  if (scenarioKey === "price_concern") {
    if (format === "email") {
      return `${greeting}\n\nThanks for the note. If you would like to bring the price down, the best option is usually to reduce the scope, set a few items aside, or have more of the load ready ahead of time. If you want, send over the changes you have in mind and Bay Delivery can take another look.\n\n${closing}`;
    }
    return `${greeting} Thanks for the note. If you would like to bring the price down, the best option is usually to reduce the scope, set a few items aside, or have more of the load ready ahead of time. If you want, send over the changes you have in mind and Bay Delivery can take another look. ${closing}`;
  }

  if (scenarioKey === "completed_followup") {
    if (format === "email") {
      return `${greeting}\n\nThanks again for choosing Bay Delivery. We are following up to make sure the ${serviceLabel} was completed the way you expected. If anything was missed, reply here and we will take care of it.\n\n${closing}`;
    }
    return `${greeting} Thanks again for choosing Bay Delivery. Just checking that the ${serviceLabel} was completed the way you expected. If anything was missed, reply here and we will take care of it. ${closing}`;
  }

  if (scenarioKey === "review_request") {
    if (format === "email") {
      return `${greeting}\n\nThanks again for choosing Bay Delivery. If you were happy with the job, we would really appreciate a short Google or Facebook review when you have a minute. It helps local customers find us.\n\n${closing}`;
    }
    return `${greeting} Thanks again for choosing Bay Delivery. If you were happy with the job, we would really appreciate a short Google or Facebook review when you have a minute. ${closing}`;
  }

  if (scenarioKey === "manual_review") {
    const extraPrompt = photoPrompts.length ? `A few photos and any extra access details will help us confirm it.` : "A few photos and any extra access details will help us confirm it.";
    if (format === "email") {
      return `${greeting}\n\nThanks for sending this over. Before we confirm the final price for the ${serviceLabel}, we need to double-check a few details so there are no surprises on the day of the job. ${extraPrompt}\n\n${closing}`;
    }
    return `${greeting} Thanks for sending this over. Before we confirm the final price for the ${serviceLabel}, we need to double-check a few details so there are no surprises on the day of the job. ${extraPrompt} ${closing}`;
  }

  return `${greeting} Thanks for reaching out to Bay Delivery. Reply here when you are ready and we will take the next step from there. ${closing}`;
}

function buildAdminDraft(context) {
  const missingFields = getMissingCompletedCostFields(context);
  const missingSummary = missingFields.length ? joinList(missingFields) : "actual labour cost, actual disposal cost, actual fuel cost, actual other costs, final amount collected, and payment status";
  const label = context.kind === "job"
    ? `${context.customer_name || "job"} (${context.job_id || ""})`
    : "this completed job";
  return `Internal follow-up: please enter missing completed-job closeout details for ${label}. Still needed: ${missingSummary}. This helper is copy-only and does not update job status.`;
}

function buildFollowupMessageDraft(scenarioKey, format, context) {
  if (scenarioKey === "missing_completed_job_cost_info") {
    return buildAdminDraft(context);
  }
  return buildCustomerDraft(scenarioKey, format, context);
}

function updateFollowupMessageDraft() {
  if (!followupMessageScenarioSelect || !followupMessageFormatSelect || !followupMessageContextSelect || !followupMessageDraftInput || !followupMessageCopyBtn) return;
  const scenarioKey = followupMessageScenarioSelect.value || followupMessageScenarioCatalog[0].key;
  const format = followupMessageFormatSelect.value || "text";
  const context = getFollowupContextByValue(followupMessageContextSelect.value || "general");
  const draft = buildFollowupMessageDraft(scenarioKey, format, context);
  followupMessageDraftInput.value = draft;
  followupMessageCopyBtn.disabled = !safeTrimmed(draft);
  if (followupMessageContextSummary) {
    followupMessageContextSummary.textContent = describeDraftContext(context);
  }
  if (followupMessageStatusLine) {
    followupMessageStatusLine.textContent = "Copy-only helper. Review the draft before using it.";
    followupMessageStatusLine.className = "statusNotice muted";
  }
}

function renderFollowupMessageHelper() {
  if (!followupMessageScenarioSelect || !followupMessageFormatSelect || !followupMessageContextSelect) return;
  const selectedScenario = followupMessageScenarioSelect.value;
  const selectedFormat = followupMessageFormatSelect.value;
  const selectedContext = followupMessageContextSelect.value;
  populateSelectOptions(
    followupMessageScenarioSelect,
    followupMessageScenarioCatalog.map((item) => [item.key, item.label]),
    selectedScenario || followupMessageScenarioCatalog[0].key,
  );
  populateSelectOptions(
    followupMessageFormatSelect,
    followupMessageFormatOptions,
    selectedFormat || followupMessageFormatOptions[0][0],
  );
  populateSelectOptions(
    followupMessageContextSelect,
    createFollowupContextOptions().map((item) => [item.value, item.label]),
    selectedContext || "general",
  );
  updateFollowupMessageDraft();
}

async function copyFollowupMessageDraft() {
  if (!followupMessageDraftInput || !followupMessageStatusLine) return;
  const draft = safeTrimmed(followupMessageDraftInput.value);
  if (!draft) {
    setLine(followupMessageStatusLine, "bad", "No draft to copy yet. Choose a scenario first.");
    return;
  }

  try {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      await navigator.clipboard.writeText(draft);
      setLine(followupMessageStatusLine, "ok", "Message copied to clipboard.");
      return;
    }
  } catch {
    // Fall back to manual copy guidance below.
  }

  followupMessageDraftInput.focus();
  followupMessageDraftInput.select();
  setLine(followupMessageStatusLine, "bad", "Clipboard access was blocked. The draft is selected so you can copy it manually.");
}

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
      adminProtectedDashboard.style.display = "";
      adminProtectedDashboard.removeAttribute("hidden");
      adminProtectedDashboard.setAttribute("aria-hidden", "false");
    } else {
      adminProtectedDashboard.style.display = "none";
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
  const boxIds = ["opsQueueBox", "quotesBox", "requestsBox", "jobsBox", "profitReportBox", "assistantResultBox", "assistantHistoryBox", "assistantUploadList"];
  boxIds.forEach((id) => {
    const box = document.getElementById(id);
    if (box) clearNode(box);
  });
  currentAssistantAnalysisId = "";
  currentAssistantHandoff = null;
  currentRequestItems = [];
  currentJobItems = [];
  currentJobsById = {};
  currentQuoteItems = [];
  currentQuoteDetailId = "";
  currentQuoteDetailLoading = false;
  currentQuoteDetailError = "";
  currentQuoteDetailsById = {};
  setAssistantDraftLocked(false);
  if (assistantDraftMeta) assistantDraftMeta.textContent = "No screenshot intake guidance records yet.";
  renderFollowupMessageHelper();
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

async function fetchJSON(path, options = {}) {
  const headers = Object.assign({}, authHeaders(), options.headers || {});
  const res = await fetch(path, Object.assign({}, options, { headers }));

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
    rejected: "Rejected",
    expired: "Expired"
  };
  return map[(status || "").toLowerCase()] || (status || "unknown");
}

function followupStatusLabel(status) {
  const map = Object.fromEntries(quoteRequestFollowupOptions);
  return map[(status || "").toLowerCase()] || "Unmarked";
}

function money(n) {
  const x = Number(n || 0);
  return "$" + x.toFixed(2);
}

const formatMoneyOrDash = (value) =>
  value == null || value === "" ? "-" : money(value);

function nullableNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatInputNumber(value) {
  return value === null || value === undefined || value === "" ? "" : String(value);
}

function selectedValue(value) {
  return value === null || value === undefined ? "" : String(value);
}

const costingCostFields = [
  ["actual_labor_cost_cad", "labor"],
  ["actual_disposal_cost_cad", "disposal"],
  ["actual_fuel_cost_cad", "fuel"],
  ["actual_other_costs_cad", "other"]
];

function costingKnownCosts(job) {
  return costingCostFields.reduce((total, [field]) => {
    const value = nullableNumber(job[field]);
    return total + (value || 0);
  }, 0);
}

function missingCostLabels(job) {
  return costingCostFields
    .filter(([field]) => nullableNumber(job[field]) === null)
    .map(([, label]) => label);
}

function advisoryKnownCostProfit(job) {
  const collected = nullableNumber(job.final_amount_collected_cad);
  if (collected === null) return null;
  return collected - costingKnownCosts(job);
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

const opsBoardShortcutsByKey = {
  new_requests: [
    { label: "Open requests", targetId: "adminRequestsSection" }
  ],
  needs_followup: [
    { label: "Open follow-up controls", targetId: "adminRequestsSection" }
  ],
  accepted_not_booked: [
    { label: "Open requests", targetId: "adminRequestsSection" },
    { label: "Open jobs", targetId: "adminJobsSection" }
  ],
  upcoming_jobs: [
    { label: "Open jobs", targetId: "adminJobsSection" }
  ],
  completed_missing_costs: [
    { label: "Open job costing", targetId: "adminJobsSection" }
  ],
  owner_review: [
    { label: "Open estimates", targetId: "adminQuotesSection" },
    { label: "Open requests", targetId: "adminRequestsSection" }
  ],
  stale_quotes: [
    { label: "Open estimates", targetId: "adminQuotesSection" }
  ]
};

function focusAdminSection(targetId, label) {
  const target = document.getElementById(targetId);
  if (!target) {
    setLine(statusLine, "bad", "Daily Ops Board shortcut target is not available. Refresh admin data and try again.");
    return;
  }

  if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  target.focus({ preventScroll: true });
  target.classList.add("adminSectionFocus");
  window.setTimeout(() => target.classList.remove("adminSectionFocus"), 1800);
  setLine(statusLine, "ok", "Daily Ops Board shortcut opened:", label || "section");
}

function createOpsQueueShortcutButton(shortcut) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "opsQueueShortcut";
  button.setAttribute("data-ops-shortcut", shortcut.targetId || "");
  button.textContent = shortcut.label || "Open";
  button.addEventListener("click", () => focusAdminSection(shortcut.targetId || "", shortcut.label || ""));
  return button;
}

function renderOpsQueue(queue) {
  const box = document.getElementById("opsQueueBox");
  if (!box) return;
  clearNode(box);

  const cards = Array.isArray(queue && queue.cards) ? queue.cards : [];
  if (!cards.length) {
    return addEmptyState(box, "No Daily Ops Board cards available.");
  }

  const grid = document.createElement("div");
  grid.className = "opsQueueGrid";

  const orderedCards = cards
    .slice()
    .sort((a, b) => dailyOpsBoardCardKeys.indexOf(a.key) - dailyOpsBoardCardKeys.indexOf(b.key));

  orderedCards.forEach((item) => {
    const card = document.createElement("section");
    card.className = "opsQueueSummaryCard";

    const header = document.createElement("div");
    header.className = "opsQueueCardHeader";

    const title = document.createElement("div");
    title.className = "opsQueueCardTitle";
    title.textContent = item.label || item.key || "Daily ops";

    const count = document.createElement("span");
    count.className = "opsQueueCount";
    count.textContent = String(item.count || 0);

    header.append(title, count);
    card.appendChild(header);

    const description = document.createElement("div");
    description.className = "small muted opsQueueCardDescription";
    description.textContent = item.description || "Read-only operational count from existing admin data.";
    card.appendChild(description);

    const shortcuts = opsBoardShortcutsByKey[item.key] || [];
    if (shortcuts.length) {
      const actions = document.createElement("div");
      actions.className = "opsQueueActions";
      shortcuts.forEach((shortcut) => actions.appendChild(createOpsQueueShortcutButton(shortcut)));
      card.appendChild(actions);
    }

    grid.appendChild(card);
  });

  box.appendChild(grid);
}

function renderOpsQueueError() {
  const box = document.getElementById("opsQueueBox");
  if (!box) return;
  clearNode(box);
  const div = document.createElement("div");
  div.className = "emptyState";
  const msg = document.createElement("span");
  msg.className = "bad";
  msg.textContent = "Daily Ops Board could not load. Core admin data is still available.";
  div.appendChild(msg);
  box.appendChild(div);
}

function friendlyMissingSchedulingField(field) {
  const labels = {
    job_id: "job record",
    requested_job_date: "requested date",
    requested_time_window: "requested time window",
    scheduled_start: "scheduled start",
    scheduled_end: "scheduled end"
  };
  return labels[field] || String(field || "").replace(/_/g, " ");
}

function shouldOpenAcceptedNotBookedItemInRescheduleMode(item) {
  const normalizedStatus = String(item?.status || "").trim().toLowerCase();
  const hasCalendarEvent = Boolean(String(item?.google_calendar_event_id || "").trim());
  return normalizedStatus === "scheduled" && hasCalendarEvent;
}

function renderAcceptedNotBookedQueue(payload) {
  const box = document.getElementById("acceptedNotBookedQueueBox");
  if (!box) return;
  clearNode(box);

  const items = Array.isArray(payload?.accepted_not_booked_items) ? payload.accepted_not_booked_items : [];
  const totalCount = Number(payload?.counts?.accepted_not_booked || items.length || 0);

  if (!items.length) {
    return addEmptyState(box, totalCount ? "Accepted-not-booked detail is temporarily unavailable." : "No accepted or approved work is waiting on scheduling.");
  }

  const summary = document.createElement("div");
  summary.className = "acceptedNotBookedQueueSummary";
  summary.textContent = items.length < totalCount
    ? `Showing latest ${items.length} of ${totalCount} accepted or approved items waiting on scheduling.`
    : `${totalCount} accepted or approved item${totalCount === 1 ? "" : "s"} waiting on scheduling.`;
  box.appendChild(summary);

  const list = document.createElement("div");
  list.className = "acceptedNotBookedList";

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "acceptedNotBookedItem";

    const header = document.createElement("div");
    header.className = "acceptedNotBookedHeader";

    const titleWrap = document.createElement("div");
    titleWrap.className = "acceptedNotBookedTitleWrap";
    const title = document.createElement("strong");
    title.className = "acceptedNotBookedTitle";
    const titleBits = [item.customer_name || item.item_id || "Unassigned item"];
    if (item.service_type) titleBits.push(String(item.service_type).replace(/_/g, " "));
    title.textContent = titleBits.join(" • ");
    titleWrap.appendChild(title);

    const sub = document.createElement("div");
    sub.className = "small muted";
    const subBits = [];
    if (item.job_address) subBits.push(item.job_address);
    if (item.submitted_at) subBits.push(`Submitted ${item.submitted_at}`);
    else if (item.created_at) subBits.push(`Created ${item.created_at}`);
    sub.textContent = subBits.join(" • ");
    titleWrap.appendChild(sub);

    const badgeWrap = document.createElement("div");
    badgeWrap.className = "acceptedNotBookedBadgeWrap";
    badgeWrap.appendChild(makeStatusBadge(item.status || item.item_type || "pending"));

    const readiness = document.createElement("span");
    readiness.className = `acceptedNotBookedReadinessBadge ${item.scheduling_ready ? "is-ready" : "is-blocked"}`;
    readiness.textContent = item.scheduling_ready ? "Ready to schedule" : "Needs workflow step";
    badgeWrap.appendChild(readiness);

    header.append(titleWrap, badgeWrap);
    card.appendChild(header);

    const detailGrid = document.createElement("div");
    detailGrid.className = "acceptedNotBookedDetailGrid";
    [
      ["Type", item.item_type === "job" ? "Job" : "Request"],
      ["Quote", item.quote_id || "-"],
      ["Request", item.request_id || "-"],
      ["Job", item.job_id || "-"],
      ["Preferred date", item.requested_job_date ? formatIsoDate(item.requested_job_date) : "Not provided"],
      ["Preferred window", item.preferred_window_label || "Not provided"],
      ["Phone", item.customer_phone || "-"]
    ].forEach(([label, value]) => {
      const row = document.createElement("div");
      row.className = "acceptedNotBookedDetailRow";
      const name = document.createElement("span");
      name.className = "acceptedNotBookedDetailLabel";
      name.textContent = label;
      const val = document.createElement("span");
      if (["Quote", "Request", "Job"].includes(label) && value !== "-") {
        val.appendChild(createAdminIdCode(value));
      } else {
        val.textContent = value;
      }
      row.append(name, val);
      detailGrid.appendChild(row);
    });
    card.appendChild(detailGrid);

    const summaryText = document.createElement("div");
    summaryText.className = "acceptedNotBookedSummary";
    summaryText.textContent = item.scheduling_summary || "Scheduling review pending.";
    card.appendChild(summaryText);

    const missingFields = Array.isArray(item.missing_scheduling_fields) ? item.missing_scheduling_fields : [];
    const missing = document.createElement("div");
    missing.className = "acceptedNotBookedMissingFields";
    const missingLabel = document.createElement("strong");
    missingLabel.textContent = "Missing scheduling fields:";
    const missingValue = document.createElement("span");
    missingValue.textContent = missingFields.length ? missingFields.map(friendlyMissingSchedulingField).join(", ") : "None";
    missing.append(missingLabel, missingValue);
    card.appendChild(missing);

    if (item.notes) {
      const notes = document.createElement("div");
      notes.className = "small muted acceptedNotBookedNotes";
      notes.textContent = `Notes: ${item.notes}`;
      card.appendChild(notes);
    }

    const actionRow = document.createElement("div");
    actionRow.className = "acceptedNotBookedActions";
    if (item.job_id) {
      const openInRescheduleMode = shouldOpenAcceptedNotBookedItemInRescheduleMode(item);
      const scheduleBtn = document.createElement("button");
      scheduleBtn.type = "button";
      scheduleBtn.className = "actionBtn acceptedNotBookedScheduleBtn";
      scheduleBtn.textContent = openInRescheduleMode ? "Open Reschedule" : "Open Schedule";
      scheduleBtn.addEventListener("click", () => showScheduleModal(item.job_id, openInRescheduleMode));
      actionRow.appendChild(scheduleBtn);
    } else {
      const actionHint = document.createElement("div");
      actionHint.className = "small muted";
      actionHint.textContent = item.recommended_action === "approve_request"
        ? "Approve this request from the Booking Requests section before scheduling."
        : "Create or restore a job record before opening the schedule workflow.";
      actionRow.appendChild(actionHint);
    }
    card.appendChild(actionRow);

    list.appendChild(card);
  });

  box.appendChild(list);
}

function renderAcceptedNotBookedQueueError() {
  const box = document.getElementById("acceptedNotBookedQueueBox");
  if (!box) return;
  clearNode(box);
  addEmptyState(box, "Accepted, Not Booked could not load. Core admin data is still available.");
}

async function refreshOpsQueueBestEffort() {
  try {
    const opsQueue = await fetchJSON("/admin/api/ops-queue");
    renderOpsQueue(opsQueue);
    renderAcceptedNotBookedQueue(opsQueue);
  } catch {
    renderOpsQueueError();
    renderAcceptedNotBookedQueueError();
  }
}

function renderProfitReport(report) {
  const box = document.getElementById("profitReportBox");
  if (!box) return;
  clearNode(box);

  if (!report || (!Array.isArray(report.jobs) && !Array.isArray(report.summary_cards))) {
    return addEmptyState(box, "No profit report data available.");
  }

  // Summary cards
  const cards = Array.isArray(report.summary_cards) ? report.summary_cards : [];
  if (cards.length) {
    const grid = document.createElement("div");
    grid.className = "profitReportSummaryGrid";
    cards.forEach((card) => {
      const section = document.createElement("section");
      section.className = "profitReportCard";

      const header = document.createElement("div");
      header.className = "profitReportCardHeader";

      const label = document.createElement("div");
      label.className = "profitReportCardLabel";
      label.textContent = card.label || card.key || "";

      const val = document.createElement("span");
      val.className = "profitReportCardValue";
      if (card.value === null || card.value === undefined) {
        val.textContent = "—";
      } else if (card.key === "known_profit_total_cad") {
        val.textContent = "$" + Number(card.value).toFixed(2);
      } else if (card.key === "avg_known_margin_pct") {
        val.textContent = Number(card.value).toFixed(1) + "%";
      } else {
        val.textContent = String(card.value);
      }

      header.append(label, val);
      section.appendChild(header);

      if (card.description) {
        const desc = document.createElement("div");
        desc.className = "small muted profitReportCardDescription";
        desc.textContent = card.description;
        section.appendChild(desc);
      }

      grid.appendChild(section);
    });
    box.appendChild(grid);
  }

  // Category breakdown
  const breakdown = Array.isArray(report.category_breakdown) ? report.category_breakdown : [];
  if (breakdown.length) {
    const h4 = document.createElement("h4");
    h4.className = "profitReportSubheading";
    h4.textContent = "Category Breakdown";
    box.appendChild(h4);

    const table = document.createElement("table");
    table.className = "profitReportTable";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Service Type", "Jobs", "Complete", "Incomplete", "Owner Review", "Underquoted/Painful", "Profit Total", "Avg Margin", "Avg Collected"].forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    breakdown.forEach((row) => {
      const tr = document.createElement("tr");
      const cells = [
        row.service_type || "unknown",
        String(row.total_jobs || 0),
        String(row.complete_rows || 0),
        String(row.incomplete_rows || 0),
        String(row.owner_review_count || 0),
        String(row.underquoted_painful_count || 0),
        row.known_profit_total_cad !== null && row.known_profit_total_cad !== undefined ? "$" + Number(row.known_profit_total_cad).toFixed(2) : "—",
        row.avg_known_margin_pct !== null && row.avg_known_margin_pct !== undefined ? Number(row.avg_known_margin_pct).toFixed(1) + "%" : "—",
        row.avg_collected_cad !== null && row.avg_collected_cad !== undefined ? "$" + Number(row.avg_collected_cad).toFixed(2) : "—",
      ];
      cells.forEach((cellText) => {
        const td = document.createElement("td");
        td.textContent = cellText;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    box.appendChild(table);
  }

  // Recent completed jobs table
  const jobs = Array.isArray(report.jobs) ? report.jobs : [];
  if (jobs.length) {
    const h4 = document.createElement("h4");
    h4.className = "profitReportSubheading";
    h4.textContent = "Recent Completed Jobs";
    box.appendChild(h4);

    const table = document.createElement("table");
    table.className = "profitReportTable";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Job ID", "Service", "Collected", "Known Cost", "Known Profit", "Margin", "Status", "Flags"].forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    jobs.forEach((job) => {
      const tr = document.createElement("tr");
      if (job.owner_review) tr.classList.add("profitReportRowReview");
      else if (!job.is_complete) tr.classList.add("profitReportRowIncomplete");

      const flags = [];
      if (!job.is_complete) flags.push("Missing cost data");
      if (job.owner_review) flags.push("Needs owner review");
      if (job.job_profit_status === "underquoted") flags.push("Underquoted");
      if (job.job_profit_status === "painful") flags.push("Painful job");
      if (job.trusted_margin && job.known_margin_pct !== null && job.known_margin_pct < 20) flags.push("Below 20% known margin");

      const cells = [
        String(job.job_id || "").slice(0, 8) + "…",
        job.service_type || "unknown",
        job.final_amount_collected_cad !== null && job.final_amount_collected_cad !== undefined ? "$" + Number(job.final_amount_collected_cad).toFixed(2) : "—",
        job.known_cost_cad !== null && job.known_cost_cad !== undefined ? "$" + Number(job.known_cost_cad).toFixed(2) : "—",
        job.known_profit_cad !== null && job.known_profit_cad !== undefined ? "$" + Number(job.known_profit_cad).toFixed(2) : "—",
        job.known_margin_pct !== null && job.known_margin_pct !== undefined ? Number(job.known_margin_pct).toFixed(1) + "%" : (job.is_complete ? "—" : "Incomplete closeout"),
        job.job_profit_status || "—",
        flags.join(", ") || "Profitable",
      ];
      cells.forEach((cellText) => {
        const td = document.createElement("td");
        td.textContent = cellText;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    box.appendChild(table);
  }

  if (!cards.length && !breakdown.length && !jobs.length) {
    addEmptyState(box, "No completed jobs found.");
  }
}

function renderProfitReportError() {
  const box = document.getElementById("profitReportBox");
  if (!box) return;
  clearNode(box);
  const div = document.createElement("div");
  div.className = "emptyState";
  const msg = document.createElement("span");
  msg.className = "bad";
  msg.textContent = "Profit review report could not load. Core admin data is still available.";
  div.appendChild(msg);
  box.appendChild(div);
}

async function refreshProfitReportBestEffort() {
  try {
    const report = await fetchJSON("/admin/api/completed-job-profit-report");
    renderProfitReport(report);
  } catch {
    renderProfitReportError();
  }
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

function makeQuoteRiskLevelBadge(riskLevel) {
  const normalized = String(riskLevel || "").trim().toLowerCase();
  const labels = {
    low: "Low risk",
    medium: "Medium risk",
    high: "High risk",
    owner_review: "Owner review",
  };
  const classes = {
    low: "quote-risk-level-low",
    medium: "quote-risk-level-medium",
    high: "quote-risk-level-high",
    owner_review: "quote-risk-level-owner-review",
  };
  const className = classes[normalized] || "quote-risk-level-unknown";
  const badge = document.createElement("span");
  badge.className = "statusBadge quoteRiskLevel " + className;
  badge.textContent = labels[normalized] || "Unknown risk";
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

function createLeadCustomerHistorySection(leadSource, customerHistory) {
  const hasLeadSource = leadSource && typeof leadSource === "object";
  const hasCustomerHistory = customerHistory && typeof customerHistory === "object";
  if (!hasLeadSource && !hasCustomerHistory) return null;

  const section = document.createElement("section");
  section.className = "quoteRiskSection leadCustomerHistorySection";

  const title = document.createElement("div");
  title.className = "quoteDetailTitle";
  title.textContent = "Lead & Customer History";
  section.appendChild(title);

  const leadLabel = hasLeadSource ? String(leadSource.label || "Unknown").trim() : "Unknown";
  section.appendChild(createQuoteMetaRow("Lead source", leadLabel || "Unknown"));

  if (hasCustomerHistory) {
    section.appendChild(createQuoteMetaRow("Customer history", customerHistory.label || "Customer history unavailable"));
    section.appendChild(createQuoteMetaRow("Previous requests", String(customerHistory.previous_requests ?? 0)));
    section.appendChild(createQuoteMetaRow("Previous jobs", String(customerHistory.previous_jobs ?? 0)));
    if (Number(customerHistory.previous_quotes || 0) > 0) {
      section.appendChild(createQuoteMetaRow("Previous quote-only matches", String(customerHistory.previous_quotes || 0)));
    }
    if (customerHistory.last_seen) {
      section.appendChild(createQuoteMetaRow("Last seen", formatIsoDate(customerHistory.last_seen)));
    }
  }

  return section;
}

function hasStructuredIntakeValue(request, field) {
  if (!Object.prototype.hasOwnProperty.call(request, field)) return false;
  const value = request[field];
  return value !== null && value !== undefined && value !== "";
}

function formatStructuredIntakeValue(value) {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  const normalized = String(value || "").trim();
  return structuredIntakeLabels[normalized] || normalized || "—";
}

function createStructuredIntakeSection(request) {
  const rows = structuredIntakeFields.filter(([field]) => hasStructuredIntakeValue(request, field));
  if (!rows.length) return null;

  const section = document.createElement("section");
  section.className = "quoteRiskSection";

  const title = document.createElement("div");
  title.className = "quoteDetailTitle";
  title.textContent = "Structured Intake";
  section.appendChild(title);

  rows.forEach(([field, label]) => {
    section.appendChild(createQuoteMetaRow(label, formatStructuredIntakeValue(request[field])));
  });

  return section;
}

function formatRiskAdvisoryLevel(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (!normalized) return "Unknown";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatRiskSummaryValue(value) {
  const normalized = String(value || "").trim();
  const labels = {
    low: "Low",
    medium: "Medium",
    high: "High",
    owner_review: "Owner review",
    approve: "Approve if the rest of the request looks right",
    ask_followup: "Ask follow-up before approving",
    request_photos: "Request photos before approving",
    owner_review_before_approving: "Owner review before approving",
    one_worker_likely: "One worker likely",
    two_workers_likely: "Two workers likely",
    truck_only: "Truck only",
    single_axle: "Single axle",
    double_axle: "Double axle",
    enclosed: "Enclosed",
    unknown: "Unknown",
    internal_advisory_only_no_price_change: "Internal advisory only - no quote total change",
    heavy_material_risk: "Heavy material risk",
    disposal_or_sorting_risk: "Disposal or sorting risk",
    access_or_stairs_risk: "Access, stairs, or inside removal risk",
    refrigerant_appliance_check: "Refrigerant appliance check",
    demolition_or_ripout_scope: "Demolition or rip-out scope",
    low_confidence_or_missing_scope: "Low confidence or missing scope",
    owner_review_recommended: "Owner review recommended",
    no_major_internal_risk_signals: "No major internal risk signals found",
    photos: "Photos",
    item_count: "Item count or load size",
    access_details: "Access details",
    disposal_type: "Disposal or heavy material type",
    preferred_date: "Preferred date",
    preferred_time_window: "Preferred time window",
  };
  return labels[normalized] || normalized.replaceAll("_", " ") || "Unknown";
}

function appendRiskSummaryList(section, label, values) {
  if (!Array.isArray(values) || !values.length) return;
  const row = document.createElement("div");
  row.className = "quoteDetailMetaRow";
  const rowLabel = document.createElement("strong");
  rowLabel.textContent = label;
  row.appendChild(rowLabel);

  const list = document.createElement("ul");
  list.className = "quoteRiskSummaryList";
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = formatRiskSummaryValue(value);
    list.appendChild(item);
  });
  row.appendChild(list);
  section.appendChild(row);
}

function createInternalRiskSummarySection(summary) {
  if (!summary || typeof summary !== "object") return null;

  const section = document.createElement("section");
  section.className = "quoteRiskSection";

  const title = document.createElement("div");
  title.className = "quoteDetailTitle";
  title.textContent = "Internal Risk Summary";
  section.appendChild(title);

  const riskLevel = String(summary.risk_level || "").trim();
  if (riskLevel) {
    section.appendChild(createQuoteMetaRow("Risk level", null, makeQuoteRiskLevelBadge(riskLevel)));
  }

  appendRiskSummaryList(section, "Reasons:", summary.reasons);
  appendRiskSummaryList(section, "Missing info:", summary.missing_info);

  section.appendChild(createQuoteMetaRow("Suggested action", formatRiskSummaryValue(summary.suggested_action)));
  section.appendChild(createQuoteMetaRow("Crew suggestion", formatRiskSummaryValue(summary.crew_suggestion)));
  section.appendChild(createQuoteMetaRow("Trailer suggestion", formatRiskSummaryValue(summary.trailer_suggestion)));
  section.appendChild(createQuoteMetaRow("Pricing caution", formatRiskSummaryValue(summary.pricing_caution)));

  return section;
}

function createQuoteRiskAdvisorySection(advisory) {
  if (!advisory || typeof advisory !== "object") return null;

  const flags = Array.isArray(advisory.risk_flags)
    ? advisory.risk_flags.filter((flag) => flag && typeof flag === "object" && String(flag.code || "").trim())
    : [];
  const actions = Array.isArray(advisory.suggested_actions)
    ? advisory.suggested_actions.filter((action) => String(action || "").trim())
    : [];
  const hasRecommendedTrailer = String(advisory.recommended_trailer || "").trim();
  if (!flags.length && !actions.length && !hasRecommendedTrailer) return null;

  const section = document.createElement("section");
  section.className = "quoteRiskSection";

  const title = document.createElement("div");
  title.className = "quoteDetailTitle";
  title.textContent = "Quote Risk Advisory";
  section.appendChild(title);

  section.appendChild(createQuoteMetaRow("Scope", "Internal advisory only - no pricing effect"));
  section.appendChild(createQuoteMetaRow("Risk level", formatRiskAdvisoryLevel(advisory.risk_level)));
  section.appendChild(
    createQuoteMetaRow("Manual review", advisory.manual_review_recommended ? "Recommended" : "Not flagged")
  );
  section.appendChild(createQuoteMetaRow("Pricing effect", advisory.pricing_effect || "none"));

  if (hasRecommendedTrailer) {
    section.appendChild(
      createQuoteMetaRow("Recommended trailer", formatStructuredIntakeValue(advisory.recommended_trailer))
    );
  }

  if (flags.length) {
    const flagsRow = document.createElement("div");
    flagsRow.className = "quoteDetailMetaRow";
    const flagsLabel = document.createElement("strong");
    flagsLabel.textContent = "Advisory flags:";
    flagsRow.appendChild(flagsLabel);

    const list = document.createElement("ul");
    list.className = "quoteRiskFlags";
    flags.forEach((flag) => {
      const item = document.createElement("li");
      const label = String(flag.label || flag.code || "").trim();
      const severity = formatRiskAdvisoryLevel(flag.severity);
      const note = String(flag.operator_note || "").trim();
      item.textContent = note ? `${label} (${severity}): ${note}` : `${label} (${severity})`;
      list.appendChild(item);
    });
    flagsRow.appendChild(list);
    section.appendChild(flagsRow);
  }

  if (actions.length) {
    const actionsRow = document.createElement("div");
    actionsRow.className = "quoteDetailMetaRow";
    const actionsLabel = document.createElement("strong");
    actionsLabel.textContent = "Suggested actions:";
    actionsRow.appendChild(actionsLabel);

    const list = document.createElement("ul");
    list.className = "quoteRiskFlags";
    actions.forEach((action) => {
      const item = document.createElement("li");
      item.textContent = String(action || "").trim();
      list.appendChild(item);
    });
    actionsRow.appendChild(list);
    section.appendChild(actionsRow);
  }

  return section;
}

function createQuoteRiskAssessmentSection(assessment) {
  const riskFlags = Array.isArray(safeGet(assessment, "risk_flags", null))
    ? assessment.risk_flags.filter((flag) => String(flag || "").trim())
    : [];

  if (!assessment || (!assessment.confidence_level && !riskFlags.length)) return null;

  const riskSection = document.createElement("section");
  riskSection.className = "quoteRiskSection quoteRawRiskSection";

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
  return riskSection;
}

function createRawRiskDataSection(...sections) {
  const visibleSections = sections.filter(Boolean);
  if (!visibleSections.length) return null;

  const details = document.createElement("details");
  details.className = "quoteRawRiskDetails";

  const summary = document.createElement("summary");
  summary.textContent = "Show raw risk data";
  details.appendChild(summary);

  const body = document.createElement("div");
  body.className = "quoteRawRiskBody";
  visibleSections.forEach((section) => {
    section.classList.add("quoteRawRiskSection");
    body.appendChild(section);
  });
  details.appendChild(body);

  return details;
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

  const structuredIntakeSection = createStructuredIntakeSection(safeRequest);
  const leadCustomerHistorySection = createLeadCustomerHistorySection(
    detail.lead_source || null,
    detail.customer_history || null
  );
  if (leadCustomerHistorySection) {
    panel.appendChild(leadCustomerHistorySection);
  }

  if (structuredIntakeSection) {
    panel.appendChild(structuredIntakeSection);
  }

  const assessment = detail.internal_risk_assessment || null;
  const internalRiskSummarySection = createInternalRiskSummarySection(detail.quote_risk_summary || null);
  if (internalRiskSummarySection) {
    panel.appendChild(internalRiskSummarySection);
  }

  const advisorySection = createQuoteRiskAdvisorySection(detail.quote_risk_advisory || null);
  const riskAssessmentSection = createQuoteRiskAssessmentSection(assessment);
  const rawRiskDataSection = createRawRiskDataSection(advisorySection, riskAssessmentSection);
  if (rawRiskDataSection) {
    panel.appendChild(rawRiskDataSection);
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

async function expireQuote(quoteId) {
  if (!quoteId) return;
  const confirmed = window.confirm("Mark this estimate expired? This keeps the record but removes it from active review.");
  if (!confirmed) return;

  statusLine.textContent = "Marking estimate expired...";

  try {
    await fetchJSON(`/admin/api/quotes/${encodeURIComponent(quoteId)}/expire`, {
      method: "POST"
    });
    setLine(statusLine, "ok", "Marked expired:", quoteId);
    await refreshAll();
  } catch (err) {
    const parsed = parseApiError(err);
    setLine(statusLine, "bad", "Could not mark expired:");
    statusLine.appendChild(document.createTextNode(" " + (safeGet(parsed, "data.detail", parsed.raw || JSON.stringify(parsed.data || {})))));
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
    code.className = "adminDisplayId";
    code.textContent = formatAdminDisplayId(q.quote_id || "");
    code.title = q.quote_id || "";
    const created = document.createElement("div");
    created.className = "small";
    created.textContent = q.created_at || "";
    tdId.append(code, created);

    const tdStatus = document.createElement("td");
    const quoteStatus = q.admin_status || safeGet(q, "request.status", q.status || "pending");
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

    if ((q.admin_status || "pending") !== "expired") {
      const expireBtn = document.createElement("button");
      expireBtn.type = "button";
      expireBtn.className = "secondaryAction btnSpacer";
      expireBtn.textContent = "Mark expired";
      expireBtn.disabled = !q.quote_id;
      expireBtn.addEventListener("click", () => expireQuote(q.quote_id || ""));
      tdActions.appendChild(expireBtn);
    }

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

async function updateQuoteRequestFollowupStatus(requestId, followupStatus) {
  if (!requestId) return;
  statusLine.textContent = "Updating follow-up marker...";

  try {
    await fetchJSON(`/admin/api/quote-requests/${encodeURIComponent(requestId)}/followup-status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ followup_status: followupStatus || null })
    });
    setLine(statusLine, "ok", "Follow-up marker saved:", followupStatusLabel(followupStatus));
    await refreshAll();
  } catch (err) {
    const parsed = parseApiError(err);
    setLine(statusLine, "bad", "Could not update follow-up marker:");
    statusLine.appendChild(document.createTextNode(" " + (safeGet(parsed, "data.detail", parsed.raw || JSON.stringify(parsed.data || {})))));
    await refreshAll();
  }
}

function createFollowupQuickActions(item) {
  const wrap = document.createElement("div");
  wrap.className = "followupQuickActions";

  quoteRequestFollowupOptions.forEach(([value, text]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "followupQuickAction";
    if (selectedValue(item.followup_status) === value) button.classList.add("isActive");
    button.textContent = text;
    button.addEventListener("click", () => {
      updateQuoteRequestFollowupStatus(item.request_id || "", value);
    });
    wrap.appendChild(button);
  });

  return wrap;
}

function createFollowupStatusControl(item) {
  const wrap = document.createElement("label");
  wrap.className = "followupStatusControl";

  const label = document.createElement("span");
  label.className = "small muted";
  label.textContent = "Admin follow-up";

  const select = document.createElement("select");
  select.name = "followup_status";
  select.dataset.requestId = item.request_id || "";
  select.className = "followupStatusSelect";

  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "Unmarked";
  select.appendChild(blank);

  quoteRequestFollowupOptions.forEach(([value, text]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.appendChild(option);
  });

  select.value = selectedValue(item.followup_status);
  select.addEventListener("change", () => {
    updateQuoteRequestFollowupStatus(item.request_id || "", select.value);
  });

  wrap.append(label, select);
  return wrap;
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
  currentRequestItems = items || [];
  if (!items || items.length === 0) return addEmptyState(box, "No booking requests yet.");
  clearNode(box);

  const { table, tbody } = createTable(["Request", "Customer", "Job", "Requested", "Follow-up", "Totals", "Actions"]);

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

    const tdFollowup = document.createElement("td");
    tdFollowup.appendChild(createFollowupStatusControl(r));
    tdFollowup.appendChild(createFollowupQuickActions(r));

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

    tr.append(tdReq, tdCustomer, tdJob, tdRequested, tdFollowup, tdTotals, actionCell(r));
    tbody.appendChild(tr);
  });

  box.appendChild(table);
  renderFollowupMessageHelper();
}

function createCostingField(label, field, type, value, options, config = {}) {
  const wrap = document.createElement("label");
  wrap.className = "jobCostingField";
  const labelText = document.createElement("span");
  labelText.textContent = label;
  wrap.appendChild(labelText);

  if (options && options.length) {
    const select = document.createElement("select");
    select.name = field;
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "Not recorded";
    select.appendChild(blank);
    options.forEach(([optionValue, optionLabel]) => {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionLabel;
      select.appendChild(option);
    });
    select.value = selectedValue(value);
    wrap.appendChild(select);
    if (config.helper) {
      const helper = document.createElement("small");
      helper.className = "jobCostingHelp";
      helper.textContent = config.helper;
      wrap.appendChild(helper);
    }
    return wrap;
  }

  const input = document.createElement("input");
  input.name = field;
  input.type = type || "text";
  input.value = formatInputNumber(value);
  if (config.placeholder) input.placeholder = config.placeholder;
  if (type === "number") {
    input.min = "0";
    input.step = field === "actual_crew_size" ? "1" : "0.01";
    input.inputMode = field === "actual_crew_size" ? "numeric" : "decimal";
  }
  wrap.appendChild(input);
  if (config.helper) {
    const helper = document.createElement("small");
    helper.className = "jobCostingHelp";
    helper.textContent = config.helper;
    wrap.appendChild(helper);
  }
  return wrap;
}

function createCostingGroup(title, description, fields) {
  const group = document.createElement("section");
  group.className = "jobCostingGroup";

  const header = document.createElement("div");
  header.className = "jobCostingGroupHeader";
  const heading = document.createElement("strong");
  heading.textContent = title;
  header.appendChild(heading);
  if (description) {
    const help = document.createElement("span");
    help.textContent = description;
    header.appendChild(help);
  }
  group.appendChild(header);

  const grid = document.createElement("div");
  grid.className = "jobCostingGroupGrid";
  fields.forEach((field) => grid.appendChild(field));
  group.appendChild(grid);
  return group;
}

function createJobCostingPanel(job) {
  const panel = document.createElement("div");
  panel.className = "jobCostingPanel";

  const title = document.createElement("div");
  title.className = "quoteDetailTitle";
  title.textContent = "Completed Job Costing";
  panel.appendChild(title);

  const collected = nullableNumber(job.final_amount_collected_cad);
  const knownCosts = costingKnownCosts(job);
  const profit = advisoryKnownCostProfit(job);
  const margin = collected && profit !== null ? `${((profit / collected) * 100).toFixed(1)}%` : "-";
  const missingCosts = missingCostLabels(job);

  const summary = document.createElement("div");
  summary.className = "jobCostingSummary";
  [
    ["Quoted totals", "Cash / EMT reference"],
    ["Quoted cash", formatMoneyOrDash(job.cash_total_cad)],
    ["Quoted EMT", formatMoneyOrDash(job.emt_total_cad)],
    ["Collected revenue", formatMoneyOrDash(job.final_amount_collected_cad)],
    ["Known costs", formatMoney(knownCosts)],
    ["Actual costs recorded", missingCosts.length ? `Missing: ${missingCosts.join(", ")}` : formatMoney(knownCosts)],
    ["Advisory profit", profit === null ? "Needs revenue and costs" : formatMoney(profit)],
    ["Advisory known-cost profit", profit === null ? "-" : formatMoney(profit)],
    ["Advisory known-cost margin", margin],
  ].forEach(([label, value]) => {
    const item = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = label;
    const text = document.createElement("span");
    text.textContent = value;
    item.append(strong, text);
    summary.appendChild(item);
  });
  panel.appendChild(summary);

  if (profit === null || missingCosts.length) {
    const missing = document.createElement("div");
    missing.className = "jobCostingState";
    missing.textContent = profit === null
      ? "Record final collected and actual costs to review known-cost profit."
      : `Missing actual cost fields reduce confidence in this advisory margin. Missing: ${missingCosts.join(", ")}.`;
    panel.appendChild(missing);
  }

  const note = document.createElement("div");
  note.className = "small muted";
  note.textContent = "Admin-only advisory feedback for completed jobs. Payment method is how the customer paid; payment status is whether the money is fully collected. Known-cost profit uses saved final collected, labor, disposal, fuel, and other costs only; quote calculation is unchanged.";
  panel.appendChild(note);

  const form = document.createElement("form");
  form.className = "jobCostingForm";
  form.append(
    createCostingGroup("Labor used", "Crew/time context for the completed job.", [
      createCostingField("Actual hours", "actual_hours", "number", job.actual_hours, null, {
        placeholder: "e.g. 2.5",
      }),
      createCostingField("Actual crew size", "actual_crew_size", "number", job.actual_crew_size, null, {
        placeholder: "e.g. 2",
      }),
      createCostingField("Labor cost CAD", "actual_labor_cost_cad", "number", job.actual_labor_cost_cad, null, {
        helper: "Admin-recorded actual labor cost for the completed job.",
        placeholder: "0.00",
      }),
    ]),
    createCostingGroup("Actual costs", "Out-of-pocket costs recorded after completion.", [
      createCostingField("Disposal cost CAD", "actual_disposal_cost_cad", "number", job.actual_disposal_cost_cad, null, {
        placeholder: "0.00",
      }),
      createCostingField("Fuel cost CAD", "actual_fuel_cost_cad", "number", job.actual_fuel_cost_cad, null, {
        placeholder: "0.00",
      }),
      createCostingField("Other costs CAD", "actual_other_costs_cad", "number", job.actual_other_costs_cad, null, {
        helper: "Miscellaneous actual costs not included in labor, disposal, or fuel.",
        placeholder: "0.00",
      }),
    ]),
    createCostingGroup("Payment collection", "Separate how the customer paid from whether money is fully collected.", [
      createCostingField("Final collected CAD", "final_amount_collected_cad", "number", job.final_amount_collected_cad, null, {
        helper: "Cash collected or EMT total actually received.",
        placeholder: "0.00",
      }),
      createCostingField("Payment method", "payment_method", "text", job.payment_method, [
        ["cash", "Cash"],
        ["emt", "EMT / e-transfer"],
        ["other", "Other"],
      ], {
        helper: "How they paid. This is separate from whether it is paid in full.",
      }),
      createCostingField("Payment status", "payment_status", "text", job.payment_status, [
        ["not_paid_yet", "Not paid yet"],
        ["partial_payment", "Partial payment"],
        ["paid_in_full", "Paid in full"],
      ], {
        helper: "Collection state. Use this even when the method is known.",
      }),
    ]),
    createCostingGroup("Profit and notes", "Operator feedback for future review; pricing is unchanged.", [
      createCostingField("Profit status", "job_profit_status", "text", job.job_profit_status, [
        ["underquoted", "Underquoted - should have charged more"],
        ["fair", "Fair - about right"],
        ["profitable", "Profitable - strong margin"],
        ["painful", "Painful - lost time or money"],
      ], {
        helper: "Operator gut check only. This does not change pricing.",
      }),
      createCostingField("Quote accuracy note", "quote_accuracy_note", "text", job.quote_accuracy_note, null, {
        placeholder: "What was different from the estimate?",
      }),
      createCostingField("Disposal receipt note", "disposal_receipt_note", "text", job.disposal_receipt_note, null, {
        placeholder: "Receipt number, dump note, or quick reminder.",
      }),
    ])
  );

  const actions = document.createElement("div");
  actions.className = "jobCostingActions";
  const saveBtn = document.createElement("button");
  saveBtn.type = "submit";
  saveBtn.className = "actionBtn";
  saveBtn.textContent = "Save Costing";
  actions.appendChild(saveBtn);
  form.appendChild(actions);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    saveJobCosting(job.job_id, form);
  });

  panel.appendChild(form);
  return panel;
}

function renderJobs(items) {
  const box = document.getElementById("jobsBox");
  currentJobItems = items || [];
  if (!items || items.length === 0) return addEmptyState(box, "No jobs yet.");
  clearNode(box);
  currentJobsById = Object.fromEntries((items || []).filter((item) => item && item.job_id).map((item) => [item.job_id, item]));

  const { table, tbody } = createTable(["Job", "Quote", "Status", "Customer", "Address", "Cash Total", "Scheduled", "Calendar Sync", "Actions"]);

  items.forEach((j) => {
    const tr = document.createElement("tr");

    const tdJob = document.createElement("td");
    const jobCode = document.createElement("code");
    jobCode.className = "adminDisplayId";
    jobCode.textContent = formatAdminDisplayId(j.job_id || "");
    jobCode.title = j.job_id || "";
    const created = document.createElement("div");
    created.className = "small";
    created.textContent = j.created_at || "";
    tdJob.append(jobCode, created);

    const tdQuote = document.createElement("td");
    const qCode = document.createElement("code");
    qCode.className = "adminDisplayId";
    qCode.textContent = formatAdminDisplayId(j.quote_id || "");
    qCode.title = j.quote_id || "";
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
    if (j.status === "completed") {
      const costingRow = document.createElement("tr");
      costingRow.className = "jobCostingRow";
      const costingCell = document.createElement("td");
      costingCell.colSpan = 9;
      costingCell.appendChild(createJobCostingPanel(j));
      costingRow.appendChild(costingCell);
      tbody.appendChild(costingRow);
    }
  });

  box.appendChild(table);
  renderFollowupMessageHelper();
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

function costingPayloadFromForm(form) {
  const data = new FormData(form);
  const numberField = (field) => {
    const value = String(data.get(field) || "").trim();
    return value ? Number(value) : null;
  };
  const textField = (field) => {
    const value = String(data.get(field) || "").trim();
    return value || null;
  };
  return {
    actual_hours: numberField("actual_hours"),
    actual_crew_size: numberField("actual_crew_size"),
    actual_labor_cost_cad: numberField("actual_labor_cost_cad"),
    actual_disposal_cost_cad: numberField("actual_disposal_cost_cad"),
    actual_fuel_cost_cad: numberField("actual_fuel_cost_cad"),
    actual_other_costs_cad: numberField("actual_other_costs_cad"),
    final_amount_collected_cad: numberField("final_amount_collected_cad"),
    payment_method: textField("payment_method"),
    payment_status: textField("payment_status"),
    job_profit_status: textField("job_profit_status"),
    quote_accuracy_note: textField("quote_accuracy_note"),
    disposal_receipt_note: textField("disposal_receipt_note")
  };
}

async function saveJobCosting(jobId, form) {
  try {
    const resp = await fetch(`/admin/api/jobs/${jobId}/costing`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(costingPayloadFromForm(form))
    });
    const text = await resp.text();
    if (resp.ok) {
      setLine(statusLine, "ok", "Saved job costing.");
      refreshAll();
      return;
    }
    alert("Error saving job costing: " + text);
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
    void refreshOpsQueueBestEffort();
    void refreshProfitReportBestEffort();
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
if (followupMessageScenarioSelect) followupMessageScenarioSelect.addEventListener("change", updateFollowupMessageDraft);
if (followupMessageFormatSelect) followupMessageFormatSelect.addEventListener("change", updateFollowupMessageDraft);
if (followupMessageContextSelect) followupMessageContextSelect.addEventListener("change", updateFollowupMessageDraft);
if (followupMessageCopyBtn) followupMessageCopyBtn.addEventListener("click", copyFollowupMessageDraft);

resetProtectedDashboard();
closeScheduleModal();
setLoading(false);

// On first load, we don't auto-refresh with empty creds.
setLine(statusLine, "bad", "Enter admin username/password, then press Enter or click Log In & Load Data.");
