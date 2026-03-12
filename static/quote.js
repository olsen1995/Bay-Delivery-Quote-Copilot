const el = (id) => document.getElementById(id);
let lastQuoteId = null;
let lastAcceptToken = null;
let lastBookingToken = null;
const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function setBoxState(box, state) {
  box.classList.remove("boxInfo", "boxSuccess", "boxError");
  if (state === "error") box.classList.add("boxError");
  else if (state === "success") box.classList.add("boxSuccess");
  else if (state === "info") box.classList.add("boxInfo");
}

function inferBoxState(text) {
  if ((text || "").startsWith("Error:")) return "error";
  if (/successfully|saved|submitted/i.test(text || "")) return "success";
  return "info";
}

function showBox(id, text, state) {
  const box = el(id);
  box.classList.remove("hidden");
  setBoxState(box, state || inferBoxState(text));
  box.textContent = text;
}
function hideBox(id) {
  const box = el(id);
  box.classList.add("hidden");
  setBoxState(box, null);
  box.textContent = "";
}

function scrollToElement(id) {
  const node = el(id);
  if (!node) return;
  node.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
}

function revealCard(id, shouldScroll) {
  const card = el(id);
  if (!card) return;
  const wasHidden = card.classList.contains("hidden");
  card.classList.remove("hidden");
  if (wasHidden) {
    card.classList.remove("stageReveal");
    void card.offsetWidth;
    card.classList.add("stageReveal");
  }
  if (shouldScroll) {
    scrollToElement(id);
  }
}

function setFlowStage(stage) {
  const steps = document.querySelectorAll("#flowProgress .flowStep");
  steps.forEach((stepEl, idx) => {
    const stepNumber = idx + 1;
    stepEl.classList.toggle("is-complete", stepNumber < stage);
    stepEl.classList.toggle("is-active", stepNumber === stage);
  });
}

function createInfoBlock(label, value, extraClass) {
  const block = document.createElement("div");
  if (extraClass) block.className = extraClass;

  const heading = document.createElement("span");
  heading.textContent = label;

  const strong = document.createElement("strong");
  strong.textContent = value;

  block.append(heading, strong);
  return block;
}

function getLoadSizeLabel(bagCount) {
  if (bagCount <= 0) return "Estimated";
  if (bagCount <= 5) return "Small";
  if (bagCount <= 12) return "Medium";
  if (bagCount <= 20) return "Large";
  return "Extra-large";
}

function pluralize(count, singular, plural) {
  return count === 1 ? singular : plural;
}

function buildEstimateDetails() {
  const serviceType = el("service_type").value;
  const serviceLabel = el("service_type").selectedOptions[0].textContent;
  const access = el("access_difficulty").value;
  const hasDenseMaterials = el("has_dense_materials").checked;
  const bagCount = parseInt(el("garbage_bag_count").value || "0", 10);
  const mattresses = parseInt(el("mattresses_count").value || "0", 10);
  const boxSprings = parseInt(el("box_springs_count").value || "0", 10);
  const details = [];

  if (serviceType === "haul_away" || serviceType === "demolition") {
    const loadType = serviceType === "demolition" ? "demolition debris load" : "junk load";
    const loadSize = getLoadSizeLabel(bagCount);
    details.push(loadSize + " " + loadType + " (" + bagCount + " " + pluralize(bagCount, "bag", "bags") + ")");

    if (mattresses > 0 || boxSprings > 0) {
      const pieces = [];
      if (mattresses > 0) {
        pieces.push(mattresses + " " + pluralize(mattresses, "mattress", "mattresses"));
      }
      if (boxSprings > 0) {
        pieces.push(boxSprings + " " + pluralize(boxSprings, "box spring", "box springs"));
      }
      details.push("Bulk items included: " + pieces.join(" and "));
    }
  }

  details.push("Service selected: " + serviceLabel);

  if (access === "normal") {
    details.push("Easy access");
  } else if (access === "difficult") {
    details.push("Difficult access (stairs, basement, or long carry)");
  } else {
    details.push("Extreme access conditions");
  }

  if (hasDenseMaterials) {
    details.push("Heavy or dense materials included");
  }

  if (serviceType === "haul_away" || serviceType === "demolition" || serviceType === "scrap_pickup") {
    details.push("Disposal included");
  }

  if (requiresRouteFields(serviceType)) {
    details.push("Travel included based on your local pickup and dropoff details");
  } else {
    details.push("Local service area");
  }

  return details;
}

function renderQuoteResult(data, quoteResponse) {
  const box = el("resultBox");
  box.classList.remove("hidden");
  setBoxState(box, "success");
  box.classList.remove("stageReveal");
  void box.offsetWidth;
  box.classList.add("stageReveal");
  box.replaceChildren();

  const wrapper = document.createElement("div");
  wrapper.className = "quoteResult";

  const header = document.createElement("div");
  header.className = "quoteResultHeader";

  const titleWrap = document.createElement("div");
  const title = document.createElement("h2");
  title.textContent = "Your Estimate";
  const subtitle = document.createElement("p");
  subtitle.className = "muted";
  subtitle.textContent = "Review the totals below, then accept the quote to continue with booking.";
  titleWrap.append(title, subtitle);

  const meta = document.createElement("div");
  meta.className = "quoteResultMeta";
  const quoteId = document.createElement("div");
  quoteId.textContent = "Quote ID: " + (data.quote_id || "");
  const created = document.createElement("div");
  created.textContent = "Created: " + (data.created_at || "");
  meta.append(quoteId, created);

  header.append(titleWrap, meta);

  const breakdown = document.createElement("div");
  breakdown.className = "quoteResultBreakdown";
  const breakdownTitle = document.createElement("h3");
  breakdownTitle.textContent = "Pricing Breakdown";
  const amountGrid = document.createElement("div");
  amountGrid.className = "quoteAmountGrid";
  amountGrid.append(
    createInfoBlock("Cash total (no HST)", "$" + Number(quoteResponse.cash_total_cad).toFixed(2) + " CAD", "quoteAmountCard"),
    createInfoBlock("EMT total (+13% HST)", "$" + Number(quoteResponse.emt_total_cad).toFixed(2) + " CAD", "quoteAmountCard highlight")
  );
  breakdown.append(breakdownTitle, amountGrid);

  const estimateDetails = document.createElement("div");
  estimateDetails.className = "estimateDetails";

  const estimateDetailsTitle = document.createElement("h3");
  estimateDetailsTitle.textContent = "Estimate Details";

  const estimateDetailsList = document.createElement("ul");
  estimateDetailsList.className = "estimateDetailsList";
  buildEstimateDetails().forEach((detail) => {
    const item = document.createElement("li");
    item.textContent = detail;
    estimateDetailsList.appendChild(item);
  });

  const estimateDetailsReassurance = document.createElement("p");
  estimateDetailsReassurance.className = "muted estimateDetailsReassurance";
  estimateDetailsReassurance.textContent = "No obligation estimate. Final price is confirmed before work begins if conditions differ from the details provided.";

  estimateDetails.append(estimateDetailsTitle, estimateDetailsList, estimateDetailsReassurance);

  const note = document.createElement("div");
  note.className = "quoteResultNote";
  const noteTitle = document.createElement("h3");
  noteTitle.textContent = "Important Note";
  const noteBody = document.createElement("p");
  noteBody.className = "muted";
  noteBody.textContent = quoteResponse.disclaimer || "";
  note.append(noteTitle, noteBody);

  wrapper.append(header, breakdown, estimateDetails, note);
  box.appendChild(wrapper);
}

function clearForm() {
  el("quoteForm").reset();
  const servicePanel = el("serviceDetailsPanel");
  if (servicePanel) servicePanel.open = false;
  syncRouteFields();
  syncServiceFields();
  hideBox("resultBox");
  hideBox("uploadStatus");
  hideBox("decisionStatus");
  hideBox("bookingStatus");
  hideBox("flowStatus");
  el("uploadCard").classList.add("hidden");
  el("decisionCard").classList.add("hidden");
  el("bookingCard").classList.add("hidden");
  el("quoteSummaryCard").classList.add("hidden");
  el("loadingState").classList.add("hidden");
  setFlowStage(1);
  lastQuoteId = null;
  lastAcceptToken = null;
  lastBookingToken = null;
  el("photos").value = "";
  el("decisionNotes").value = "";
  el("bookingDate").value = "";
  el("bookingWindow").value = "";
  el("bookingNotes").value = "";
}

function resetInapplicableServiceFields(serviceType) {
  const isScrap = serviceType === "scrap_pickup";
  const usesLoadCounts = serviceType === "haul_away" || serviceType === "demolition";

  if (isScrap) {
    el("estimated_hours").value = "0";
    el("crew_size").value = "1";
  }

  if (!isScrap) {
    el("scrap_pickup_location").value = "curbside";
  }

  if (!usesLoadCounts) {
    el("garbage_bag_count").value = "0";
    el("mattresses_count").value = "0";
    el("box_springs_count").value = "0";
  }
}

function syncServiceFields() {
  const serviceType = el("service_type").value;
  const showRoute = serviceType === "small_move" || serviceType === "item_delivery";
  const showScrap = serviceType === "scrap_pickup";
  const showLoadCounts = serviceType === "haul_away" || serviceType === "demolition";
  const showDenseMaterials = showLoadCounts;
  const showLabor = !showScrap;

  resetInapplicableServiceFields(serviceType);

  el("estimatedHoursGroup").classList.toggle("hidden", !showLabor);
  el("crewSizeGroup").classList.toggle("hidden", !showLabor);
  el("scrapLocationGroup").classList.toggle("hidden", !showScrap);
  el("loadCountRow").classList.toggle("hidden", !showLoadCounts);
  el("denseMaterialsGroup").classList.toggle("hidden", !showDenseMaterials);
  el("scrap_pickup_location").disabled = !showScrap;
  el("has_dense_materials").disabled = !showDenseMaterials;
  if (!showDenseMaterials) {
    el("has_dense_materials").checked = false;
  }

  const help = el("serviceHelp");
  if (showScrap) {
    help.textContent = "Scrap pickup uses location-based pricing. Labor and bulk-item fields are hidden.";
  } else if (showRoute) {
    help.textContent = "Route details are required for this service. Pickup/dropoff fields are now visible.";
  } else if (showLoadCounts) {
    help.textContent = "Tell us your item counts and estimated labor for best pricing accuracy.";
  } else {
    help.textContent = "Select a service to show only the fields needed for that job type.";
  }
}

function requiresRouteFields(serviceType) {
  return serviceType === "small_move" || serviceType === "item_delivery";
}

function extractQuoteResponse(data) {
  if (!data || typeof data !== "object") {
    return null;
  }
  if (data.response && typeof data.response === "object") {
    return data.response;
  }
  return data;
}

function syncRouteFields() {
  const needRoutes = requiresRouteFields(el("service_type").value);
  const routeRow = el("routeRow");
  const pickup = el("pickup_address");
  const dropoff = el("dropoff_address");
  const servicePanel = el("serviceDetailsPanel");

  if (servicePanel && needRoutes) {
    servicePanel.open = true;
  }

  routeRow.classList.toggle("hidden", !needRoutes);
  pickup.required = needRoutes;
  dropoff.required = needRoutes;

  if (!needRoutes) {
    pickup.value = "";
    dropoff.value = "";
  }
}

async function submitBooking() {
  hideBox("bookingStatus");

  if (!lastQuoteId || !lastBookingToken) {
    showBox("bookingStatus", "No booking token available. Accept the quote first.");
    return;
  }

  const payload = {
    booking_token: lastBookingToken,
    requested_job_date: el("bookingDate").value,
    requested_time_window: el("bookingWindow").value,
    notes: el("bookingNotes").value || null,
  };

  showBox("bookingStatus", "Submitting booking...");

  try {
    const res = await fetch("/quote/" + encodeURIComponent(lastQuoteId) + "/booking", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      showBox("bookingStatus", "Error:\n" + (data.detail || "Unknown error"));
      return;
    }

    showBox("bookingStatus", "Booking submitted successfully.\nRequest ID: " + data.request_id + "\n\nWe will follow up to confirm scheduling.");
    setFlowStage(5);
    revealCard("uploadCard", true);
  } catch (err) {
    showBox("bookingStatus", "Error:\nFailed to contact server.");
  }
}

async function submitDecision(action) {
  hideBox("decisionStatus");
  hideBox("flowStatus");

  if (!lastQuoteId || !lastAcceptToken) {
    showBox("decisionStatus", "No quote or token available. Calculate quote first.");
    return;
  }

  const payload = {
    action,
    accept_token: lastAcceptToken,
    notes: el("decisionNotes").value || null
  };

  showBox("decisionStatus", "Submitting decision...");

  try {
    const res = await fetch("/quote/" + encodeURIComponent(lastQuoteId) + "/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      showBox("decisionStatus", "Error:\n" + (data.detail || "Unknown error"));
      return;
    }

    const confirmation =
      "Decision saved successfully.\n" +
      "Request ID: " + data.request_id + "\n" +
      "Status: " + data.status;

    if (action === "accept") {
      lastBookingToken = data.booking_token;
      showBox("flowStatus", confirmation + "\n\nPlease provide your booking details below.");
      el("decisionCard").classList.add("hidden");
      revealCard("bookingCard", true);
      setFlowStage(4);
      el("bookingNameDisplay").textContent = el("customer_name").value;
      el("bookingPhoneDisplay").textContent = el("customer_phone").value;
    } else {
      showBox("decisionStatus", confirmation + "\n\nYou declined this quote. No booking will be created.");
    }
  } catch (err) {
    showBox("decisionStatus", "Error:\nFailed to contact server.");
  }
}

el("btnClear").addEventListener("click", (e) => {
  e.preventDefault();
  clearForm();
});

el("btnAccept").addEventListener("click", () => submitDecision("accept"));
el("btnDecline").addEventListener("click", () => submitDecision("decline"));
el("btnSubmitBooking").addEventListener("click", submitBooking);
el("service_type").addEventListener("change", () => {
  syncRouteFields();
  syncServiceFields();
});

el("btnCalc").addEventListener("click", async () => {
  hideBox("resultBox");
  hideBox("uploadStatus");
  hideBox("decisionStatus");
  hideBox("flowStatus");
  el("uploadCard").classList.add("hidden");
  el("decisionCard").classList.add("hidden");
  el("bookingCard").classList.add("hidden");
  el("quoteSummaryCard").classList.add("hidden");
  el("loadingState").classList.remove("hidden");
  setFlowStage(1);
  lastQuoteId = null;
  let timeoutId = null;

  try {
    const customerName = (el("customer_name").value || "").trim();
    const customerPhone = (el("customer_phone").value || "").trim();
    const jobAddress = (el("job_address").value || "").trim();
    const description = (el("description").value || "").trim();

    if (!customerName || !customerPhone || !jobAddress || !description) {
      showBox("resultBox", "Please fill in all required fields (name, phone, address, and description).");
      return;
    }

    const serviceType = el("service_type").value;
    const isScrap = serviceType === "scrap_pickup";
    const usesLoadCounts = serviceType === "haul_away" || serviceType === "demolition";
    const usesLabor = !isScrap;
    const pickupAddress = (el("pickup_address").value || "").trim();
    const dropoffAddress = (el("dropoff_address").value || "").trim();

    if (requiresRouteFields(serviceType) && (!pickupAddress || !dropoffAddress)) {
      const servicePanel = el("serviceDetailsPanel");
      if (servicePanel) servicePanel.open = true;
      showBox("resultBox", "Error:\nPickup and dropoff addresses are required for small moves and item delivery.");
      return;
    }

    const payload = {
      service_type: serviceType,
      customer_name: customerName,
      customer_phone: customerPhone,
      job_address: jobAddress,
      pickup_address: pickupAddress || null,
      dropoff_address: dropoffAddress || null,
      description,
      estimated_hours: usesLabor ? parseFloat(el("estimated_hours").value || "0") : 0,
      crew_size: usesLabor ? parseInt(el("crew_size").value || "1", 10) : 1,
      access_difficulty: el("access_difficulty").value || "normal",
      has_dense_materials: usesLoadCounts ? el("has_dense_materials").checked : false,
      garbage_bag_count: usesLoadCounts ? parseInt(el("garbage_bag_count").value || "0", 10) : 0,
      mattresses_count: usesLoadCounts ? parseInt(el("mattresses_count").value || "0", 10) : 0,
      box_springs_count: usesLoadCounts ? parseInt(el("box_springs_count").value || "0", 10) : 0,
      scrap_pickup_location: isScrap ? el("scrap_pickup_location").value : "curbside"
    };

    const controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), 30000);

    const res = await fetch("/quote/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    let data = {};
    try {
      data = await res.json();
    } catch (_jsonErr) {
      data = {};
    }

    if (!res.ok) {
      showBox("resultBox", "Error:\n" + (data.detail || "Unknown error"));
      return;
    }

    const quoteResponse = extractQuoteResponse(data);
    if (!quoteResponse) {
      showBox("resultBox", "Error:\nQuote response was empty.");
      return;
    }

    lastQuoteId = data.quote_id;
    lastAcceptToken = data.accept_token;
    revealCard("uploadCard");
    revealCard("decisionCard");
    revealCard("quoteSummaryCard");
    setFlowStage(3);
    el("summaryService").textContent = el("service_type").selectedOptions[0].textContent;
    el("summaryCustomer").textContent = customerName + " • " + customerPhone;
    el("summaryLocation").textContent = jobAddress;

    renderQuoteResult(data, quoteResponse);
    scrollToElement("resultBox");
  } catch (err) {
    if (err.name === "AbortError") {
      showBox("resultBox", "Error:\nRequest timed out. Please try again in a moment.");
    } else {
      showBox("resultBox", "Error:\nFailed to contact server.");
    }
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    el("loadingState").classList.add("hidden");
  }
});

el("btnUpload").addEventListener("click", async () => {
  hideBox("uploadStatus");

  if (!lastQuoteId) {
    showBox("uploadStatus", "No quote_id available yet. Calculate quote first.");
    return;
  }

  const input = el("photos");
  if (!input.files || input.files.length === 0) {
    showBox("uploadStatus", "No photos selected.");
    return;
  }
  if (input.files.length > 5) {
    showBox("uploadStatus", "Too many photos selected (max 5).");
    return;
  }

  const formData = new FormData();
  formData.append("quote_id", lastQuoteId);
  for (const f of input.files) formData.append("files", f);

  showBox("uploadStatus", "Uploading photos...");

  try {
    const res = await fetch("/quote/upload-photos", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      showBox("uploadStatus", "Error:\n" + (data.detail || "Unknown error"));
      return;
    }
    showBox("uploadStatus", "Uploaded successfully. Admin will review your photos.");
    setFlowStage(5);
  } catch (err) {
    showBox("uploadStatus", "Error:\nFailed to contact server.");
  }
});

syncRouteFields();
syncServiceFields();
setFlowStage(1);
