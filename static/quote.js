const el = (id) => document.getElementById(id);
let lastQuoteId = null;
let lastAcceptToken = null;
let lastBookingToken = null;
let persistedReviewMode = false;
let quoteCalculationInFlight = false;
const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const persistedReviewHelperText = "You are reviewing a saved estimate prepared for you. Review the pricing and request details here, and contact Bay Delivery if anything needs to be updated.";

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

const requiredFieldLabels = {
  customer_name: "Customer name",
  customer_phone: "Customer phone",
  job_address: "Job address",
  description: "Description",
  pickup_address: "Pickup address",
  dropoff_address: "Dropoff address"
};

function serviceTypeLabel(serviceType) {
  const option = el("service_type")?.querySelector(`option[value="${serviceType}"]`);
  return option ? option.textContent : "this service";
}

function setInvalidState(field, isInvalid) {
  if (!field) return;
  if (isInvalid) {
    field.setAttribute("aria-invalid", "true");
  } else {
    field.removeAttribute("aria-invalid");
  }
}

function clearInvalidState(fieldId) {
  setInvalidState(el(fieldId), false);
}

function clearQuoteValidationState() {
  Object.keys(requiredFieldLabels).forEach((fieldId) => {
    clearInvalidState(fieldId);
  });
}

function validateRequiredFields(serviceType) {
  const requiredIds = ["customer_name", "customer_phone", "job_address", "description"];
  if (requiresRouteFields(serviceType)) {
    requiredIds.push("pickup_address", "dropoff_address");
  }

  const missing = [];
  requiredIds.forEach((fieldId) => {
    const field = el(fieldId);
    const value = ((field && field.value) || "").trim();
    const isMissing = !value;
    setInvalidState(field, isMissing);
    if (isMissing) {
      missing.push({ id: fieldId, label: requiredFieldLabels[fieldId] || fieldId });
    }
  });

  return missing;
}

function getSelectedTrailerFillEstimate() {
  return (el("trailer_fill_estimate").value || "").trim();
}

function getSelectedBagType() {
  return (el("bag_type").value || "").trim();
}

function optionalSelectValue(id) {
  const value = (el(id).value || "").trim();
  return value || null;
}

function optionalNonNegativeInt(id) {
  const value = (el(id).value || "").trim();
  if (!value) return null;
  const parsed = parseInt(value, 10);
  if (Number.isNaN(parsed) || parsed < 0) return null;
  return parsed;
}

function addOptionalInt(payload, field) {
  const value = optionalNonNegativeInt(field);
  if (value !== null) payload[field] = value;
}

function addOptionalSelect(payload, field) {
  const value = optionalSelectValue(field);
  if (value) payload[field] = value;
}

function addCheckedFlag(payload, field) {
  if (el(field).checked) payload[field] = true;
}

function hasHaulAwayStructuredLoadDetail() {
  return (
    parseInt(el("garbage_bag_count").value || "0", 10) > 0 ||
    parseInt(el("mattresses_count").value || "0", 10) > 0 ||
    parseInt(el("box_springs_count").value || "0", 10) > 0 ||
    el("has_dense_materials").checked ||
    Boolean(getSelectedTrailerFillEstimate())
  );
}

function haulAwayLoadDetailMessage() {
  return "Please add at least one load detail so we can quote your junk removal. Examples: bags, trailer space used, mattresses, box springs, or heavy materials.";
}

function trailerFillLabel(value) {
  const select = el("trailer_fill_estimate");
  if (!select) return "";
  const option = Array.from(select.options).find((candidate) => candidate.value === value);
  return option ? option.textContent : "";
}

function missingFieldSummary(missing) {
  if (!missing || missing.length === 0) return "";
  const missingIds = missing.map((field) => field.id);
  const routeMissing = missingIds.includes("pickup_address") || missingIds.includes("dropoff_address");
  const lines = ["Please fill in the required fields:"];
  missing.forEach((field) => {
    lines.push("- " + field.label);
  });
  if (routeMissing) {
    lines.push("");
    lines.push("Pickup and dropoff addresses are required for moves and deliveries.");
  }
  return lines.join("\n");
}

function friendlyQuoteErrorMessage(detail) {
  if (!detail) return "Unknown error";
  if (detail === "pickup_address and dropoff_address are required") {
    return "Pickup address and dropoff address are required for moves and deliveries. Add both locations in the job details section and try again.";
  }
  if (detail === "Please enter a valid 10-digit phone number. You can include spaces, dashes, parentheses, or +1.") {
    return detail + " We use it for estimate and booking follow-up only.";
  }
  return detail;
}

function manualQuoteFallbackMessage(reason) {
  return reason + "\n\nIf the online quote does not come through, call or text Dan at (705) 303-4409, or email BayDeliveryNB@gmail.com with your job details. Bay Delivery can review the job manually.";
}

function focusFirstInvalidField(missing) {
  if (!missing || missing.length === 0) return;
  const first = el(missing[0].id);
  if (first && typeof first.focus === "function") {
    first.focus();
  }
}

function attachValidationClearHandlers() {
  Object.keys(requiredFieldLabels).forEach((fieldId) => {
    const field = el(fieldId);
    if (!field) return;

    const maybeClear = () => {
      if (((field.value || "").trim())) {
        setInvalidState(field, false);
      }
    };

    field.addEventListener("input", maybeClear);
    field.addEventListener("change", maybeClear);
  });
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

function getTodayDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function enforceBookingDateMin() {
  const bookingDateInput = el("bookingDate");
  if (!bookingDateInput) return;
  bookingDateInput.min = getTodayDateString();
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

function createTextBlock(title, body, className) {
  const block = document.createElement("div");
  block.className = className || "";

  const heading = document.createElement("h3");
  heading.textContent = title;

  const paragraph = document.createElement("p");
  paragraph.className = "muted";
  paragraph.textContent = body;

  block.append(heading, paragraph);
  return block;
}

function setFieldValue(id, value, fallback = "") {
  const node = el(id);
  if (!node) return;
  if (node.type === "checkbox") {
    node.checked = Boolean(value);
    return;
  }
  node.value = value ?? fallback;
}

function persistedReviewFields() {
  return [
    "customer_name",
    "customer_phone",
    "job_address",
    "description",
    "service_type",
    "pickup_address",
    "dropoff_address",
    "estimated_hours",
    "crew_size",
    "access_difficulty",
    "has_dense_materials",
    "garbage_bag_count",
    "mattresses_count",
    "box_springs_count",
    "scrap_pickup_location",
    "bag_type",
    "trailer_fill_estimate",
    "stairs_count",
    "floor_count",
    "basement_or_inside_removal",
    "demolition_ripout",
    "construction_debris_type",
    "dense_material_type",
    "mixed_load",
    "contains_scrap",
    "contains_garbage",
    "has_refrigerant_appliance",
    "appliance_type",
    "weather_protection_required"
  ].map((id) => el(id)).filter(Boolean);
}

function setPersistedReviewMode(isActive) {
  persistedReviewMode = Boolean(isActive);
  const clearBtn = el("btnClear");
  syncQuoteCalculateActionState();
  if (clearBtn) clearBtn.disabled = persistedReviewMode;
  persistedReviewFields().forEach((field) => {
    field.disabled = persistedReviewMode;
  });
}

function syncQuoteCalculateActionState() {
  const calcBtn = el("btnCalc");
  if (calcBtn) calcBtn.disabled = persistedReviewMode || quoteCalculationInFlight;
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

function syncBagCountNudge() {
  const serviceType = el("service_type").value;
  const showLoadCounts = serviceType === "haul_away" || serviceType === "demolition";
  const nudge = el("bagCountNudge");
  const bagCount = parseInt(el("garbage_bag_count").value || "0", 10);
  nudge.classList.toggle("hidden", !showLoadCounts || Number.isNaN(bagCount) || bagCount > 3);
}

function buildEstimateDetails() {
  const serviceType = el("service_type").value;
  const serviceLabel = el("service_type").selectedOptions[0].textContent;
  const access = el("access_difficulty").value;
  const hasDenseMaterials = el("has_dense_materials").checked;
  const bagCount = parseInt(el("garbage_bag_count").value || "0", 10);
  const trailerFillEstimate = getSelectedTrailerFillEstimate();
  const mattresses = parseInt(el("mattresses_count").value || "0", 10);
  const boxSprings = parseInt(el("box_springs_count").value || "0", 10);
  const details = [];

  if (serviceType === "haul_away" || serviceType === "demolition") {
    const loadType = serviceType === "demolition" ? "demolition debris load" : "junk load";
    if (bagCount > 0) {
      const loadSize = getLoadSizeLabel(bagCount);
      details.push(loadSize + " " + loadType + " (" + bagCount + " " + pluralize(bagCount, "bag", "bags") + ")");
    } else if (serviceType === "haul_away" && trailerFillEstimate) {
      details.push("Estimated junk load (" + trailerFillLabel(trailerFillEstimate) + ")");
    } else if (serviceType === "haul_away") {
      details.push("Load size not specified");
    }

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
    details.push("Curbside or main-floor access");
  } else if (access === "difficult") {
    details.push("Apartment/stairs/basement or longer carry");
  } else {
    details.push("Complex access conditions");
  }

  if (hasDenseMaterials) {
    details.push("Heavy materials included");
  }

  if (serviceType === "haul_away" || serviceType === "demolition" || serviceType === "scrap_pickup") {
    details.push("Disposal included");
  }

  if (requiresRouteFields(serviceType)) {
    details.push("Route details included from your pickup and dropoff locations");
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
  subtitle.textContent = "Review your totals and what is included, then decide if you want to continue.";
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
    createInfoBlock("Cash (no HST)", "$" + Number(quoteResponse.cash_total_cad).toFixed(2) + " CAD", "quoteAmountCard highlight cashOption"),
    createInfoBlock("EMT / e-transfer (+13% HST)", "$" + Number(quoteResponse.emt_total_cad).toFixed(2) + " CAD", "quoteAmountCard emtOption")
  );
  const amountHint = document.createElement("p");
  amountHint.className = "quoteAmountHint muted";
  amountHint.textContent = "Cash has no HST. EMT / e-transfer includes 13% HST. Totals are based on the details you entered.";
  breakdown.append(breakdownTitle, amountGrid, amountHint);

  const included = document.createElement("div");
  included.className = "quoteResultIncluded";
  included.append(
    createTextBlock("What this estimate includes", "This estimate reflects the details you shared, including local travel, labour, handling, and disposal where applicable.", "quoteInfoCard"),
    createTextBlock("What happens next", "If this estimate works for you, choose Accept Estimate & Continue. Then share your preferred date and time window, and Bay Delivery will review and confirm before booking.", "quoteInfoCard")
  );

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

  estimateDetails.append(estimateDetailsTitle, estimateDetailsList);

  const note = document.createElement("div");
  note.className = "quoteResultNote";
  const noteTitle = document.createElement("h3");
  noteTitle.textContent = "About this estimate";
  const noteBody = document.createElement("p");
  noteBody.className = "muted";
  noteBody.textContent = (quoteResponse.disclaimer || "") + " Photos are optional after your booking request if they help Bay Delivery confirm scope.";
  note.append(noteTitle, noteBody);

  const nextStep = document.createElement("div");
  nextStep.className = "nextStepCallout";
  nextStep.textContent = "Next step: decide whether this estimate works for you. Accept Estimate & Continue opens the booking request form. Bay Delivery confirms details before anything is booked.";

  wrapper.append(header, breakdown, included, nextStep, estimateDetails, note);
  box.appendChild(wrapper);
}

function clearForm() {
  el("quoteForm").reset();
  syncRouteFields();
  syncServiceFields();
  const servicePanel = el("serviceDetailsPanel");
  if (servicePanel) {
    servicePanel.open = requiresRouteFields(el("service_type").value);
  }
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
  setPersistedReviewMode(false);
  el("photos").value = "";
  el("decisionNotes").value = "";
  el("bookingDate").value = "";
  el("bookingWindow").value = "";
  el("bookingNotes").value = "";
  syncBagCountNudge();
}

function resetInapplicableServiceFields(serviceType) {
  const isScrap = serviceType === "scrap_pickup";
  const usesLoadCounts = serviceType === "haul_away" || serviceType === "demolition";
  const isHaulAway = serviceType === "haul_away";
  const isDemolition = serviceType === "demolition";
  const showRoute = serviceType === "small_move" || serviceType === "item_delivery";

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
    el("construction_debris_type").value = "";
    el("dense_material_type").value = "";
    el("mixed_load").checked = false;
    el("contains_scrap").checked = false;
    el("contains_garbage").checked = false;
  }

  if (!isDemolition) {
    el("demolition_ripout").checked = false;
  }

  if (!isHaulAway) {
    el("bag_type").value = "";
    el("trailer_fill_estimate").value = "";
    el("has_refrigerant_appliance").checked = false;
    el("appliance_type").value = "";
  }

  if (!showRoute) {
    el("weather_protection_required").checked = false;
  }
}

function syncServiceFields() {
  const serviceType = el("service_type").value;
  const showHaulAwayDetails = serviceType === "haul_away";
  const showRoute = serviceType === "small_move" || serviceType === "item_delivery";
  const showScrap = serviceType === "scrap_pickup";
  const showLoadCounts = serviceType === "haul_away" || serviceType === "demolition";
  const showDenseMaterials = showLoadCounts;
  const showLabor = !showScrap;
  const showDemolitionRipout = serviceType === "demolition";

  resetInapplicableServiceFields(serviceType);

  el("estimatedHoursGroup").classList.toggle("hidden", !showLabor);
  el("crewSizeGroup").classList.toggle("hidden", !showLabor);
  el("scrapLocationGroup").classList.toggle("hidden", !showScrap);
  el("loadCountRow").classList.toggle("hidden", !showLoadCounts);
  el("haulAwayDetailsRow").classList.toggle("hidden", !showHaulAwayDetails);
  el("applianceDetailsRow").classList.toggle("hidden", !showHaulAwayDetails);
  el("denseMaterialsGroup").classList.toggle("hidden", !showDenseMaterials);
  el("structuredMaterialsRow").classList.toggle("hidden", !showLoadCounts);
  el("structuredLoadFlagsRow").classList.toggle("hidden", !showLoadCounts);
  el("demolitionRipoutGroup").classList.toggle("hidden", !showDemolitionRipout);
  el("weatherProtectionGroup").classList.toggle("hidden", !showRoute);
  el("scrap_pickup_location").disabled = !showScrap;
  el("bag_type").disabled = !showHaulAwayDetails;
  el("trailer_fill_estimate").disabled = !showHaulAwayDetails;
  el("has_refrigerant_appliance").disabled = !showHaulAwayDetails;
  el("appliance_type").disabled = !showHaulAwayDetails;
  el("has_dense_materials").disabled = !showDenseMaterials;
  el("construction_debris_type").disabled = !showLoadCounts;
  el("dense_material_type").disabled = !showLoadCounts;
  el("mixed_load").disabled = !showLoadCounts;
  el("contains_scrap").disabled = !showLoadCounts;
  el("contains_garbage").disabled = !showLoadCounts;
  el("demolition_ripout").disabled = !showDemolitionRipout;
  el("weather_protection_required").disabled = !showRoute;
  if (!showDenseMaterials) {
    el("has_dense_materials").checked = false;
  }

  const help = el("serviceHelp");
  const detailsSummary = el("serviceDetailsSummary");
  const detailsLead = el("serviceDetailsLead");
  if (showScrap) {
    help.textContent = "Scrap pickup is usually quick to quote. Tell us whether the scrap is curbside or inside/on-property.";
    detailsSummary.textContent = "Details for your scrap pickup quote";
    detailsLead.textContent = "Answer what you can. Not sure is okay. Open this section if scrap location or access details would help.";
  } else if (showRoute) {
    help.textContent = "For moves and deliveries, add both pickup and dropoff addresses so we can quote the route.";
    detailsSummary.textContent = "Pickup and dropoff details";
    detailsLead.textContent = "Enter both pickup and dropoff addresses. These fields are required for " + serviceTypeLabel(serviceType).toLowerCase() + " jobs.";
  } else if (showLoadCounts) {
    help.textContent = "Use rough counts, location/access details, and special-item notes. Best estimates are fine.";
    detailsSummary.textContent = "Load, access, and item details";
    detailsLead.textContent = "Add the closest counts, access details, and service-specific items like mattresses or box springs. For loose junk, use regular bags or choose the closest space estimate.";
  } else {
    help.textContent = "Pick the closest match. We will only show the details needed for that job.";
    detailsSummary.textContent = "Job details for your estimate";
    detailsLead.textContent = "Open this section for location, access, and item details that help Bay Delivery prepare an accurate estimate.";
  }

  syncBagCountNudge();
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
    setInvalidState(pickup, false);
    setInvalidState(dropoff, false);
    pickup.value = "";
    dropoff.value = "";
    if (servicePanel) {
      servicePanel.open = false;
    }
  }
}

function populateQuoteFormFromRequest(requestData) {
  if (!requestData || typeof requestData !== "object") return;

  setFieldValue("customer_name", requestData.customer_name || "");
  setFieldValue("customer_phone", requestData.customer_phone || "");
  setFieldValue("job_address", requestData.job_address || "");
  setFieldValue("description", requestData.job_description_customer || requestData.description || "");
  setFieldValue("service_type", requestData.service_type || "haul_away");
  setFieldValue("pickup_address", requestData.pickup_address || "");
  setFieldValue("dropoff_address", requestData.dropoff_address || "");
  setFieldValue("estimated_hours", requestData.estimated_hours ?? "1.0");
  setFieldValue("crew_size", requestData.crew_size ?? "1");
  setFieldValue("access_difficulty", requestData.access_difficulty || "normal");
  setFieldValue("garbage_bag_count", requestData.garbage_bag_count ?? 0);
  setFieldValue("mattresses_count", requestData.mattresses_count ?? 0);
  setFieldValue("box_springs_count", requestData.box_springs_count ?? 0);
  setFieldValue("scrap_pickup_location", requestData.scrap_pickup_location || "curbside");
  setFieldValue("bag_type", requestData.bag_type || "");
  setFieldValue("trailer_fill_estimate", requestData.trailer_fill_estimate || "");
  setFieldValue("has_dense_materials", Boolean(requestData.has_dense_materials));
  setFieldValue("stairs_count", requestData.stairs_count ?? "");
  setFieldValue("floor_count", requestData.floor_count ?? "");
  setFieldValue("basement_or_inside_removal", Boolean(requestData.basement_or_inside_removal));
  setFieldValue("demolition_ripout", Boolean(requestData.demolition_ripout));
  setFieldValue("construction_debris_type", requestData.construction_debris_type || "");
  setFieldValue("dense_material_type", requestData.dense_material_type || "");
  setFieldValue("mixed_load", Boolean(requestData.mixed_load));
  setFieldValue("contains_scrap", Boolean(requestData.contains_scrap));
  setFieldValue("contains_garbage", Boolean(requestData.contains_garbage));
  setFieldValue("has_refrigerant_appliance", Boolean(requestData.has_refrigerant_appliance));
  setFieldValue("appliance_type", requestData.appliance_type || "");
  setFieldValue("weather_protection_required", Boolean(requestData.weather_protection_required));
  syncRouteFields();
  syncServiceFields();
}

function showPersistedQuoteReview(data, acceptToken) {
  const requestData = data.request || {};
  lastQuoteId = data.quote_id || null;
  lastAcceptToken = acceptToken || null;
  lastBookingToken = null;

  populateQuoteFormFromRequest(requestData);
  setPersistedReviewMode(true);

  revealCard("decisionCard");
  revealCard("quoteSummaryCard");
  const hasSubmittedBooking = Boolean(
    data.requested_job_date ||
    data.requested_time_window ||
    data.booking_submitted ||
    ["admin_approved", "rejected"].includes((data.quote_request_status || "").toLowerCase())
  );
  if (hasSubmittedBooking) {
    revealCard("uploadCard", true);
  }
  setFlowStage(3);

  el("summaryService").textContent = el("service_type").selectedOptions[0].textContent;
  el("summaryCustomer").textContent = `${requestData.customer_name || ""} • ${requestData.customer_phone || ""}`.trim();
  el("summaryLocation").textContent = requestData.job_address || "";

  renderQuoteResult(
    {
      quote_id: data.quote_id,
      created_at: data.created_at,
      request: requestData,
      response: data.response || {}
    },
    data.response || {}
  );

  const statusText = data.quote_request_status ? ` Current status: ${data.quote_request_status}.` : "";
  const followupText = " Booking preferences remain subject to Bay Delivery review and final confirmation.";
  showBox("flowStatus", persistedReviewHelperText + statusText + followupText, "info");
  scrollToElement("resultBox");
}

async function loadPersistedQuoteReview() {
  const params = new URLSearchParams(window.location.search);
  const hashParams = new URLSearchParams((window.location.hash || "").replace(/^#/, ""));
  const quoteId = (params.get("quote_id") || hashParams.get("quote_id") || "").trim();
  const acceptToken = (hashParams.get("accept_token") || "").trim();
  if (!quoteId || !acceptToken) return;

  hideBox("resultBox");
  hideBox("decisionStatus");
  hideBox("bookingStatus");
  showBox("flowStatus", "Loading your saved estimate...", "info");

  try {
    const res = await fetch(`/quote/${encodeURIComponent(quoteId)}/view`, {
      headers: { Authorization: `Bearer ${acceptToken}` },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      showBox("resultBox", "Error:\n" + (data.detail || "Unable to load saved estimate."));
      return;
    }

    showPersistedQuoteReview(data, acceptToken);
  } catch (_err) {
    showBox("resultBox", "Error:\nFailed to load saved estimate.");
  }
}

async function submitBooking() {
  hideBox("bookingStatus");
  enforceBookingDateMin();

  if (!lastQuoteId || !lastBookingToken) {
    showBox("bookingStatus", "No booking token available. Accept the estimate first to open the booking request form.");
    return;
  }

  const selectedDate = (el("bookingDate").value || "").trim();
  const today = getTodayDateString();
  if (selectedDate && selectedDate < today) {
    showBox("bookingStatus", "Please choose today or a future date for your booking.");
    return;
  }

  const payload = {
    booking_token: lastBookingToken,
    requested_job_date: selectedDate,
    requested_time_window: el("bookingWindow").value,
    notes: el("bookingNotes").value || null,
  };

  showBox("bookingStatus", "Submitting booking request...");

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

    showBox("bookingStatus", "Booking submitted successfully.\nRequest ID: " + data.request_id + "\n\nYour preferred timing has been sent to Bay Delivery. We will follow up to confirm the final schedule.");
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
    showBox("decisionStatus", "No estimate or token available. Generate an estimate first.");
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
      showBox("flowStatus", confirmation + "\n\nYour estimate is marked accepted. Please share your booking preferences below so Bay Delivery can review and confirm details with you. The job is not booked yet.");
      el("decisionCard").classList.add("hidden");
      revealCard("bookingCard", true);
      enforceBookingDateMin();
      setFlowStage(4);
      el("bookingNameDisplay").textContent = el("customer_name").value;
      el("bookingPhoneDisplay").textContent = el("customer_phone").value;
    } else {
      showBox("decisionStatus", confirmation + "\n\nYou declined this estimate. No booking request will be created.");
    }
  } catch (err) {
    showBox("decisionStatus", "Error:\nFailed to contact server.");
  }
}

el("btnClear").addEventListener("click", (e) => {
  e.preventDefault();
  if (persistedReviewMode) {
    showBox("flowStatus", persistedReviewHelperText, "info");
    return;
  }
  clearForm();
});

el("btnAccept").addEventListener("click", () => submitDecision("accept"));
el("btnDecline").addEventListener("click", () => submitDecision("decline"));
el("btnSubmitBooking").addEventListener("click", submitBooking);
el("service_type").addEventListener("change", () => {
  syncRouteFields();
  syncServiceFields();
});
el("garbage_bag_count").addEventListener("input", syncBagCountNudge);
el("garbage_bag_count").addEventListener("change", syncBagCountNudge);

attachValidationClearHandlers();
enforceBookingDateMin();

el("btnCalc").addEventListener("click", async () => {
  if (persistedReviewMode) {
    showBox("flowStatus", persistedReviewHelperText, "info");
    return;
  }
  if (quoteCalculationInFlight) return;

  quoteCalculationInFlight = true;
  syncQuoteCalculateActionState();

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
    clearQuoteValidationState();

    const serviceType = el("service_type").value;
    const missing = validateRequiredFields(serviceType);
    if (missing.length > 0) {
      if (requiresRouteFields(serviceType) && missing.some((field) => field.id === "pickup_address" || field.id === "dropoff_address")) {
        const servicePanel = el("serviceDetailsPanel");
        if (servicePanel) servicePanel.open = true;
      }
      showBox("resultBox", missingFieldSummary(missing), "error");
      scrollToElement("resultBox");
      focusFirstInvalidField(missing);
      return;
    }

    if (serviceType === "haul_away" && !hasHaulAwayStructuredLoadDetail()) {
      const servicePanel = el("serviceDetailsPanel");
      if (servicePanel) servicePanel.open = true;
      showBox("resultBox", haulAwayLoadDetailMessage(), "error");
      scrollToElement("resultBox");
      el("garbage_bag_count").focus();
      return;
    }

    const customerName = (el("customer_name").value || "").trim();
    const customerPhone = (el("customer_phone").value || "").trim();
    const jobAddress = (el("job_address").value || "").trim();
    const description = (el("description").value || "").trim();
    const leadSource = (el("lead_source").value || "").trim();

    const isHaulAway = serviceType === "haul_away";
    const isScrap = serviceType === "scrap_pickup";
    const usesLoadCounts = serviceType === "haul_away" || serviceType === "demolition";
    const usesLabor = !isScrap;
    const pickupAddress = (el("pickup_address").value || "").trim();
    const dropoffAddress = (el("dropoff_address").value || "").trim();

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
      scrap_pickup_location: isScrap ? el("scrap_pickup_location").value : "curbside",
      lead_source: leadSource || "unknown"
    };

    if (isHaulAway) {
      const bagType = getSelectedBagType();
      const trailerFillEstimate = getSelectedTrailerFillEstimate();
      if (bagType) {
        payload.bag_type = bagType;
      }
      if (trailerFillEstimate) {
        payload.trailer_fill_estimate = trailerFillEstimate;
      }
    }

    addOptionalInt(payload, "stairs_count");
    addOptionalInt(payload, "floor_count");
    addCheckedFlag(payload, "basement_or_inside_removal");
    if (usesLoadCounts) {
      addOptionalSelect(payload, "construction_debris_type");
      addOptionalSelect(payload, "dense_material_type");
      addCheckedFlag(payload, "mixed_load");
      addCheckedFlag(payload, "contains_scrap");
      addCheckedFlag(payload, "contains_garbage");
    }
    if (serviceType === "demolition") {
      addCheckedFlag(payload, "demolition_ripout");
    }
    if (isHaulAway) {
      addCheckedFlag(payload, "has_refrigerant_appliance");
      addOptionalSelect(payload, "appliance_type");
    }
    if (requiresRouteFields(serviceType)) {
      addCheckedFlag(payload, "weather_protection_required");
    }

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
      showBox("resultBox", "Error:\n" + friendlyQuoteErrorMessage(data.detail), "error");
      return;
    }

    const quoteResponse = extractQuoteResponse(data);
    if (!quoteResponse) {
      showBox("resultBox", "Error:\nQuote response was empty.");
      return;
    }

    lastQuoteId = data.quote_id;
    lastAcceptToken = data.accept_token;
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
      showBox("resultBox", "Error:\n" + manualQuoteFallbackMessage("Request timed out. Please try again in a moment."));
    } else {
      showBox("resultBox", "Error:\n" + manualQuoteFallbackMessage("Failed to contact server."));
    }
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    quoteCalculationInFlight = false;
    syncQuoteCalculateActionState();
    el("loadingState").classList.add("hidden");
  }
});

el("btnUpload").addEventListener("click", async () => {
  hideBox("uploadStatus");

  if (!lastQuoteId || !lastAcceptToken) {
    showBox("uploadStatus", "No upload authorization available yet. Generate an estimate first.");
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
  formData.append("accept_token", lastAcceptToken);
  for (const f of input.files) formData.append("files", f);

  showBox("uploadStatus", "Uploading photos...");

  try {
    const res = await fetch("/quote/upload-photos", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      showBox("uploadStatus", "Error:\n" + (data.detail || "Unknown error"));
      return;
    }
    showBox("uploadStatus", "Photos uploaded successfully. Bay Delivery will review them with your request.");
    setFlowStage(5);
  } catch (err) {
    showBox("uploadStatus", "Error:\nFailed to contact server.");
  }
});

syncRouteFields();
syncServiceFields();
syncBagCountNudge();
setPersistedReviewMode(false);
setFlowStage(1);
loadPersistedQuoteReview();
