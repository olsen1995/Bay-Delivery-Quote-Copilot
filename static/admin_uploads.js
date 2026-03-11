const el = (id) => document.getElementById(id);

function authHeaders() {
  const headers = {};
  const username = (el("adminUsername").value || "").trim();
  const password = (el("adminPassword").value || "").trim();
  if (username && password) {
    headers.Authorization = "Basic " + btoa(username + ":" + password);
  }
  return headers;
}

function showResults(items) {
  const card = el("resultsCard");
  const out = el("results");
  card.classList.remove("resultsHidden");
  out.textContent = "";

  if (!items || items.length === 0) {
    out.textContent = "No uploads found for that quote_id.";
    return;
  }

  for (const item of items) {
    const row = document.createElement("div");
    row.className = "resultRow";

    const name = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = item.filename || "file";
    const mime = document.createElement("span");
    mime.className = "muted";
    mime.textContent = " (" + (item.mime_type || "") + ")";
    name.append(strong, mime);

    const link = document.createElement("a");
    link.href = item.drive_web_view_link || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = item.drive_web_view_link ? "Open in Drive" : "No link";

    const meta = document.createElement("div");
    meta.className = "muted";
    meta.textContent = "Uploaded: " + (item.created_at || "") + " • Size: " + (item.size_bytes || 0) + " bytes";

    row.appendChild(name);
    row.appendChild(link);
    row.appendChild(meta);
    out.appendChild(row);
  }
}

async function searchUploads() {
  const quoteId = (el("quote_id").value || "").trim();
  if (!quoteId) {
    return;
  }

  const response = await fetch("/admin/api/uploads?quote_id=" + encodeURIComponent(quoteId), {
    headers: authHeaders()
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      el("resultsCard").classList.remove("resultsHidden");
      el("results").textContent = "Unauthorized — enter Admin Username/Password above (Basic Auth) and try again.";
      return;
    }
    throw new Error(JSON.stringify(data));
  }

  showResults(data.items || []);
}

el("btnSearch").addEventListener("click", searchUploads);