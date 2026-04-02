const state = {
  authHeader: "",
  username: "",
  currentScreen: "homeScreen",
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
const requestsList = document.getElementById("requestsList");
const jobsList = document.getElementById("jobsList");
const homeOpsSummary = document.getElementById("homeOpsSummary");
const requestCount = document.getElementById("requestCount");
const upcomingCount = document.getElementById("upcomingCount");
const navButtons = Array.from(document.querySelectorAll(".navButton"));
const appScreens = Array.from(document.querySelectorAll(".appScreen"));

const fields = {
  username: document.getElementById("mobileAdminUsername"),
  password: document.getElementById("mobileAdminPassword")
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
  button.disabled = isLoading;
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

function formatDateTime(value) {
  if (!value) return "—";
  return String(value).replace("T", " ");
}

function statusLabel(status) {
  const labels = {
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

function hasAuthenticatedSession() {
  return Boolean(state.authHeader) && loginScreen.hidden && !authenticatedShell.hidden;
}

function renderHomeSummary() {
  clearNode(homeOpsSummary);
  const card = document.createElement("article");
  card.className = "cardItem";
  card.innerHTML = `
    <strong>Operational workflow</strong>
    <div class="muted">Use Requests for review context and Jobs for scheduling visibility/actions.</div>
    <div class="inlineMeta mt12">
      <span class="pill">No quote drafting</span>
      <span class="pill">No customer handoff authoring</span>
    </div>
  `;
  homeOpsSummary.appendChild(card);
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

function updateQueueMetrics() {
  const openRequests = state.requests.filter((item) => ["customer_pending", "customer_accepted", "admin_approved"].includes(String(item.status || "").toLowerCase()));
  const upcomingJobs = state.jobs.filter((item) => ["approved", "scheduled", "in_progress"].includes(String(item.status || "").toLowerCase()));
  requestCount.textContent = String(openRequests.length);
  upcomingCount.textContent = String(upcomingJobs.length);
}

async function loadDashboardData() {
  if (!hasAuthenticatedSession()) {
    return;
  }

  const [requests, jobs] = await Promise.all([
    fetchJSON("/admin/api/quote-requests?limit=20"),
    fetchJSON("/admin/api/jobs?limit=20")
  ]);

  state.requests = requests.items || [];
  state.jobs = jobs.items || [];

  renderHomeSummary();
  renderRequests();
  renderJobs();
  updateQueueMetrics();
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
    setAuthenticated(true);
    showScreen("homeScreen");
    await loadDashboardData();
    setStatus(loginStatus, "ok", "Mobile admin loaded.");
  } catch (err) {
    const parsed = parseApiError(err);
    state.authHeader = "";
    state.username = "";
    setAuthenticated(false);
    setStatus(loginStatus, "bad", `Login failed. ${parsed.data?.detail || parsed.raw || "Check your credentials and try again."}`, parsed.status ? `HTTP ${parsed.status}` : "");
  } finally {
    setLoading(loginBtn, false, "Logging In...");
  }
}

async function refreshAllData(statusTarget) {
  if (!hasAuthenticatedSession()) {
    if (statusTarget) {
      setStatus(statusTarget, "warn", "Log in to refresh mobile admin data.");
    }
    return;
  }

  try {
    await loadDashboardData();
    if (statusTarget) {
      setStatus(statusTarget, "ok", "Data refreshed.");
    }
  } catch (err) {
    const parsed = parseApiError(err);
    if (statusTarget) {
      setStatus(statusTarget, "bad", `Refresh failed. ${parsed.data?.detail || parsed.raw || "Please try again."}`, parsed.status ? `HTTP ${parsed.status}` : "");
    }
  }
}

function logout() {
  state.authHeader = "";
  state.username = "";
  state.requests = [];
  state.jobs = [];
  setAuthenticated(false);
  renderEmptyState(homeOpsSummary, "Log in to load mobile ops context.");
  renderEmptyState(requestsList, "Log in to load requests.");
  renderEmptyState(jobsList, "Log in to load upcoming jobs.");
  requestCount.textContent = "0";
  upcomingCount.textContent = "0";
  setStatus(loginStatus, "warn", "Enter admin username/password, then log in.");
  showScreen("homeScreen");
}

loginForm.addEventListener("submit", handleLogin);
logoutBtn.addEventListener("click", logout);
refreshHomeBtn.addEventListener("click", () => refreshAllData(loginStatus));
refreshRequestsBtn.addEventListener("click", () => refreshAllData(loginStatus));
refreshJobsBtn.addEventListener("click", () => refreshAllData(loginStatus));

navButtons.forEach((button) => {
  button.addEventListener("click", () => showScreen(button.dataset.screen));
});

renderEmptyState(homeOpsSummary, "Log in to load mobile ops context.");
renderEmptyState(requestsList, "Log in to load requests.");
renderEmptyState(jobsList, "Log in to load upcoming jobs.");
setStatus(loginStatus, "warn", "Enter admin username/password, then log in.");
showScreen("homeScreen");
