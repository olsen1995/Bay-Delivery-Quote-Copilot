from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Annotated
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.storage import (
    init_db,
    save_quote,
    get_quote,
    list_quotes,
    search_quotes,
    save_job,
    get_job,
    list_jobs,
    update_job_fields,
)

app = FastAPI(
    title="Bay Delivery Quote Copilot API",
    version="0.6.1",
    description="Backend for Bay Delivery Quotes & Ops: quote calculator + job tracking.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

CAD = "CAD"

# --- Global Business Rules (tunable defaults) ---
MINIMUM_CHARGE_CAD = 50.00

MIN_GAS_CAD = 20.00
MIN_WEAR_CAD = 20.00

DEFAULT_TRAVEL_PER_KM_CAD = 0.35
DEFAULT_TRAVEL_FREE_KM = 10.0

# Towing is normally ON for jobs (your rule)
DEFAULT_TOWING_MODE = "open"  # "none" | "open" | "enclosed"
DEFAULT_TOWING_PER_KM_OPEN_CAD = 0.10
DEFAULT_TOWING_PER_KM_ENCLOSED_CAD = 0.15

HST_RATE_EMT = 0.13

# Disposal / specialty
MATTRESS_FEE_EACH_CAD = 50.00

# Scrap pickup special-case
CURBSIDE_SCRAP_EASY_CAD = 0.00
CURBSIDE_SCRAP_EASY_NOT_FREE_CAD = 30.00

# Labour defaults (you + helper typical)
DEFAULT_PRIMARY_WORKER_RATE_CAD = 20.00
DEFAULT_ADDITIONAL_WORKER_RATE_CAD = 16.00  # typical helper 15–17/hr avg

# For 2-worker jobs: your INTERNAL cost floor is $40, but you charge above cost.
DEFAULT_TWO_WORKER_COST_FLOOR_CAD = 40.00
DEFAULT_TWO_WORKER_CHARGE_FLOOR_CAD = 60.00  # recommended starting point (cost+margin)

DEFAULT_COMPLEXITY_MULTIPLIER = 1.0


# =========================
# Enums / Types
# =========================

class ServiceType(str, Enum):
    dump_run = "dump_run"
    scrap_pickup = "scrap_pickup"
    small_move = "small_move"
    item_delivery = "item_delivery"
    demolition = "demolition"


class TruckType(str, Enum):
    ram_2015 = "2015_ram_1500_5_7"
    ram_2019 = "2019_ram_1500_warlock_5_7"


class PaymentMethod(str, Enum):
    cash = "cash"
    emt = "emt"  # e-transfer / EMT


class TowingMode(str, Enum):
    none = "none"
    open = "open"
    enclosed = "enclosed"


NonNegFloat = Annotated[float, Field(ge=0)]
NonNegInt = Annotated[int, Field(ge=0)]
ComplexityMult = Annotated[float, Field(ge=0.5, le=3.0)]


# =========================
# Schemas
# =========================

class QuoteLineItem(BaseModel):
    code: str
    label: str
    amount_cad: NonNegFloat = 0.0
    notes: Optional[str] = None


class CustomerSummaryItem(BaseModel):
    """
    Customer-facing summary:
      - Most items show label only (no amount)
      - Only select items show amounts (mattress/box spring disposal)
    """
    label: str
    show_amount: bool = False
    amount_cad: Optional[NonNegFloat] = None


class QuoteRequest(BaseModel):
    # Customer-facing choice
    service_type: ServiceType = ServiceType.dump_run

    # Core inputs
    distance_km: NonNegFloat = 0.0
    estimated_hours: NonNegFloat = 0.0

    # Labour rules
    requires_two_workers: bool = False  # big/heavy item rule
    primary_worker_rate_cad: NonNegFloat = DEFAULT_PRIMARY_WORKER_RATE_CAD
    additional_worker_rate_cad: NonNegFloat = DEFAULT_ADDITIONAL_WORKER_RATE_CAD

    two_worker_cost_floor_cad: NonNegFloat = DEFAULT_TWO_WORKER_COST_FLOOR_CAD
    two_worker_charge_floor_cad: NonNegFloat = DEFAULT_TWO_WORKER_CHARGE_FLOOR_CAD

    # Disposal / fees
    dump_fees_cad: NonNegFloat = 0.0
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0

    # Scrap extras
    is_scrap_pickup: bool = False
    curbside_easy: bool = False
    curbside_easy_but_charge_30: bool = False
    scrap_difficult_surcharge_cad: NonNegFloat = 0.0

    # Complexity / extras
    complexity_multiplier: ComplexityMult = DEFAULT_COMPLEXITY_MULTIPLIER
    stairs_surcharge_cad: NonNegFloat = 0.0
    heavy_items_surcharge_cad: NonNegFloat = 0.0

    # Travel rules
    min_gas_cad: NonNegFloat = MIN_GAS_CAD
    min_wear_cad: NonNegFloat = MIN_WEAR_CAD
    travel_per_km_cad: NonNegFloat = DEFAULT_TRAVEL_PER_KM_CAD
    travel_free_km: NonNegFloat = DEFAULT_TRAVEL_FREE_KM

    # Internal ops: towing is normally on; frontend can omit and it defaults to open
    towing_mode: TowingMode = TowingMode(DEFAULT_TOWING_MODE)
    towing_per_km_open_cad: NonNegFloat = DEFAULT_TOWING_PER_KM_OPEN_CAD
    towing_per_km_enclosed_cad: NonNegFloat = DEFAULT_TOWING_PER_KM_ENCLOSED_CAD

    truck_type: TruckType = TruckType.ram_2015
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD

    subtotal_cad: float
    minimum_applied: bool

    total_cash_cad: float
    hst_rate: float
    hst_cad: float
    total_emt_cad: float

    # helpful metadata
    service_type: ServiceType
    crew_size: int
    towing_mode: TowingMode

    # internal + customer views
    line_items_internal: List[QuoteLineItem]
    customer_summary: List[CustomerSummaryItem]

    assumptions: List[str]


# =========================
# Jobs
# =========================

class JobStatus(str, Enum):
    new = "new"
    booked = "booked"
    in_progress = "in_progress"
    completed = "completed"
    paid = "paid"
    cancelled = "cancelled"


class JobCreateFromQuoteRequest(BaseModel):
    customer_name: Optional[str] = None
    job_address: Optional[str] = None
    scheduled_start: Optional[str] = Field(None, description="ISO preferred, e.g. 2026-02-16T14:00:00-05:00")
    scheduled_end: Optional[str] = Field(None, description="ISO preferred")
    deposit_paid_cad: NonNegFloat = 0.0
    payment_method: PaymentMethod = PaymentMethod.cash
    notes: Optional[str] = None


class JobUpdateRequest(BaseModel):
    status: Optional[JobStatus] = None
    customer_name: Optional[str] = None
    job_address: Optional[str] = None
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None
    paid_cad: Optional[NonNegFloat] = None
    notes: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    created_at: str
    quote_id: str
    status: JobStatus

    customer_name: Optional[str] = None
    job_address: Optional[str] = None
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None

    payment_method: PaymentMethod

    total_cad: NonNegFloat
    paid_cad: NonNegFloat
    owing_cad: NonNegFloat

    notes: Optional[str] = None
    quote_snapshot: Dict[str, Any]


# =========================
# Quote Engine
# =========================

@dataclass
class CalcResult:
    line_items: List[QuoteLineItem]
    assumptions: List[str]
    subtotal: float
    minimum_applied: bool
    total_cash: float
    hst_rate: float
    hst: float
    total_emt: float
    crew_size: int
    towing_mode: TowingMode
    # for customer summary decisions
    has_dump: bool
    has_stairs_or_heavy: bool
    has_complexity: bool
    mattresses_count: int
    box_springs_count: int


def _round_money(x: float) -> float:
    return float(f"{x:.2f}")


def _calc_travel(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float, float]:
    """
    Returns: (items, assumptions, travel_total, variable_km)
    """
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []

    gas = float(req.min_gas_cad)
    wear = float(req.min_wear_cad)

    items.append(QuoteLineItem(code="travel_gas_min", label="Gas (minimum)", amount_cad=_round_money(gas)))
    items.append(QuoteLineItem(code="travel_wear_min", label="Wear & tear (minimum)", amount_cad=_round_money(wear)))

    variable_km = max(0.0, float(req.distance_km) - float(req.travel_free_km))
    variable_cost = variable_km * float(req.travel_per_km_cad)

    if variable_cost > 0:
        items.append(
            QuoteLineItem(
                code="travel_variable",
                label=f"Distance surcharge ({_round_money(variable_km)} km @ ${_round_money(req.travel_per_km_cad)}/km)",
                amount_cad=_round_money(variable_cost),
            )
        )
        assumptions.append(f"Distance surcharge applies after first {_round_money(req.travel_free_km)} km.")
    else:
        assumptions.append(f"No distance surcharge (within {_round_money(req.travel_free_km)} km buffer).")

    travel_total = gas + wear + variable_cost
    return items, assumptions, _round_money(travel_total), variable_km


def _calc_towing(req: QuoteRequest, variable_km: float) -> Tuple[List[QuoteLineItem], List[str], float]:
    """
    Applies towing surcharge on variable km (after free km buffer).
    Default towing is ON (open). Frontend can omit and you still get towing cost reflected.
    """
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []

    if req.towing_mode == TowingMode.none or variable_km <= 0:
        if req.towing_mode != TowingMode.none:
            assumptions.append("Towing assumed but no variable km beyond buffer; no towing surcharge.")
        else:
            assumptions.append("No towing surcharge applied.")
        return items, assumptions, 0.0

    per_km = float(req.towing_per_km_open_cad) if req.towing_mode == TowingMode.open else float(req.towing_per_km_enclosed_cad)
    towing_cost = variable_km * per_km

    label_mode = "open trailer" if req.towing_mode == TowingMode.open else "enclosed trailer"
    items.append(
        QuoteLineItem(
            code="towing",
            label=f"Towing surcharge ({label_mode}) ({_round_money(variable_km)} km @ ${_round_money(per_km)}/km)",
            amount_cad=_round_money(towing_cost),
            notes="Towing increases fuel + wear; applied on distance beyond the free-km buffer.",
        )
    )
    assumptions.append("Towing surcharge applied because jobs normally tow a trailer.")
    return items, assumptions, _round_money(towing_cost)


def _calc_labor(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float, int]:
    """
    Labour pricing:
      - Small items: 1 worker
      - Big/heavy item: requires 2 workers
      - 2-worker labour has a CHARGED floor (above cost), so quick heavy jobs don't undercharge.
    """
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []

    hours = float(req.estimated_hours)
    crew_size = 2 if req.requires_two_workers else 1

    if hours <= 0:
        assumptions.append("Labour hours not provided; labour line item omitted (quote may be low).")
        return items, assumptions, 0.0, crew_size

    if crew_size == 1:
        labor = hours * float(req.primary_worker_rate_cad)
        items.append(
            QuoteLineItem(
                code="labor",
                label=f"Labour (1 worker) ({_round_money(hours)} hrs @ ${_round_money(req.primary_worker_rate_cad)}/hr)",
                amount_cad=_round_money(labor),
            )
        )
        return items, assumptions, _round_money(labor), crew_size

    # crew_size == 2
    labor_calc = hours * (float(req.primary_worker_rate_cad) + float(req.additional_worker_rate_cad))

    # Apply charged floor (NOT at-cost)
    charged_floor = float(req.two_worker_charge_floor_cad)
    if labor_calc < charged_floor:
        items.append(
            QuoteLineItem(
                code="labor",
                label="Labour (2 workers) minimum",
                amount_cad=_round_money(charged_floor),
                notes=f"Charged minimum for 2-person jobs (above internal cost floor ${_round_money(req.two_worker_cost_floor_cad)}).",
            )
        )
        assumptions.append("2-worker labour minimum applied (big/heavy item rule).")
        return items, assumptions, _round_money(charged_floor), crew_size

    items.append(
        QuoteLineItem(
            code="labor",
            label=f"Labour (2 workers) ({_round_money(hours)} hrs @ ${_round_money(req.primary_worker_rate_cad)}/hr + ${_round_money(req.additional_worker_rate_cad)}/hr)",
            amount_cad=_round_money(labor_calc),
        )
    )
    assumptions.append("2 workers required for big/heavy items (as flagged).")
    return items, assumptions, _round_money(labor_calc), crew_size


def _calc_disposal(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float]:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []

    dump_fees = float(req.dump_fees_cad)
    if dump_fees > 0:
        items.append(QuoteLineItem(code="dump_fees", label="Dump / landfill fees (pass-through)", amount_cad=_round_money(dump_fees)))
    else:
        assumptions.append("Dump fees set to $0 (confirm actual landfill/dump cost).")

    count_total = int(req.mattresses_count) + int(req.box_springs_count)
    mattress_total = count_total * MATTRESS_FEE_EACH_CAD
    if mattress_total > 0:
        items.append(
            QuoteLineItem(
                code="mattress_fees",
                label=f"Mattress/box spring disposal ({count_total} × ${MATTRESS_FEE_EACH_CAD:.0f})",
                amount_cad=_round_money(mattress_total),
            )
        )

    return items, assumptions, _round_money(dump_fees + mattress_total)


def _calc_scrap(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float]:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []
    total = 0.0

    if not req.is_scrap_pickup and req.service_type != ServiceType.scrap_pickup:
        return items, assumptions, 0.0

    if req.curbside_easy and not req.curbside_easy_but_charge_30 and float(req.scrap_difficult_surcharge_cad) == 0.0:
        items.append(QuoteLineItem(code="scrap_curbside", label="Curbside scrap pickup (easy)", amount_cad=_round_money(CURBSIDE_SCRAP_EASY_CAD)))
        assumptions.append("Curbside scrap marked as easy (no pickup fee).")
        total += CURBSIDE_SCRAP_EASY_CAD
    elif req.curbside_easy_but_charge_30:
        items.append(QuoteLineItem(code="scrap_curbside", label="Curbside scrap pickup (easy)", amount_cad=_round_money(CURBSIDE_SCRAP_EASY_NOT_FREE_CAD)))
        assumptions.append("Curbside scrap marked as easy (charged $30).")
        total += CURBSIDE_SCRAP_EASY_NOT_FREE_CAD

    if float(req.scrap_difficult_surcharge_cad) > 0:
        items.append(QuoteLineItem(code="scrap_difficult", label="Scrap pickup difficulty surcharge", amount_cad=_round_money(float(req.scrap_difficult_surcharge_cad))))
        assumptions.append("Difficulty surcharge provided (confirm site conditions).")
        total += float(req.scrap_difficult_surcharge_cad)

    return items, assumptions, _round_money(total)


def _calc_surcharges(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float, bool]:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []
    s = 0.0
    has_any = False

    if float(req.stairs_surcharge_cad) > 0:
        items.append(QuoteLineItem(code="stairs", label="Stairs surcharge", amount_cad=_round_money(float(req.stairs_surcharge_cad))))
        s += float(req.stairs_surcharge_cad)
        has_any = True
    if float(req.heavy_items_surcharge_cad) > 0:
        items.append(QuoteLineItem(code="heavy_items", label="Heavy items surcharge", amount_cad=_round_money(float(req.heavy_items_surcharge_cad))))
        s += float(req.heavy_items_surcharge_cad)
        has_any = True

    if not has_any:
        assumptions.append("No stairs/heavy-item surcharge included (confirm if applicable).")

    return items, assumptions, _round_money(s), has_any


def _build_customer_summary(
    *,
    has_labor: bool,
    has_travel_or_towing: bool,
    has_dump: bool,
    has_stairs_or_heavy: bool,
    has_complexity: bool,
    mattresses_count: int,
    box_springs_count: int,
) -> List[CustomerSummaryItem]:
    summary: List[CustomerSummaryItem] = []

    if has_labor:
        summary.append(CustomerSummaryItem(label="Labour included"))
    if has_travel_or_towing:
        summary.append(CustomerSummaryItem(label="Travel & towing included"))
    if has_dump:
        summary.append(CustomerSummaryItem(label="Dump/landfill handling included"))

    if has_stairs_or_heavy:
        summary.append(CustomerSummaryItem(label="Stairs/heavy-item handling included"))
    if has_complexity:
        summary.append(CustomerSummaryItem(label="Complexity/handling included"))

    # Show disposal counts WITH amounts (your exception)
    if mattresses_count > 0:
        summary.append(
            CustomerSummaryItem(
                label=f"Mattress disposal ({mattresses_count} × ${int(MATTRESS_FEE_EACH_CAD):d})",
                show_amount=True,
                amount_cad=_round_money(mattresses_count * MATTRESS_FEE_EACH_CAD),
            )
        )
    if box_springs_count > 0:
        summary.append(
            CustomerSummaryItem(
                label=f"Box spring disposal ({box_springs_count} × ${int(MATTRESS_FEE_EACH_CAD):d})",
                show_amount=True,
                amount_cad=_round_money(box_springs_count * MATTRESS_FEE_EACH_CAD),
            )
        )

    return summary


def calculate_quote(req: QuoteRequest) -> CalcResult:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []

    travel_items, travel_assumptions, travel_total, variable_km = _calc_travel(req)
    towing_items, towing_assumptions, towing_total = _calc_towing(req, variable_km)
    labor_items, labor_assumptions, labor_total, crew_size = _calc_labor(req)
    disposal_items, disposal_assumptions, disposal_total = _calc_disposal(req)
    scrap_items, scrap_assumptions, scrap_total = _calc_scrap(req)
    surcharge_items, surcharge_assumptions, surcharge_total, has_stairs_or_heavy = _calc_surcharges(req)

    items += travel_items + towing_items + labor_items + disposal_items + scrap_items + surcharge_items
    assumptions += travel_assumptions + towing_assumptions + labor_assumptions + disposal_assumptions + scrap_assumptions + surcharge_assumptions

    pre_multiplier = travel_total + towing_total + labor_total + disposal_total + scrap_total + surcharge_total

    # Complexity multiplier applies to handling/labour-ish stuff (not dump fees)
    complexity = float(req.complexity_multiplier)
    multiplier_base = travel_total + towing_total + labor_total + scrap_total + surcharge_total
    multiplier_delta = 0.0
    has_complexity = False

    if complexity != 1.0 and multiplier_base > 0:
        multiplied = multiplier_base * complexity
        multiplier_delta = multiplied - multiplier_base
        items.append(
            QuoteLineItem(
                code="complexity",
                label=f"Complexity multiplier ({complexity:.2f}× applied to handling/labour)",
                amount_cad=_round_money(multiplier_delta),
                notes="Does not multiply dump fees.",
            )
        )
        assumptions.append("Complexity multiplier applied to handling/labour/travel (not dump fees).")
        has_complexity = True

    subtotal = pre_multiplier + multiplier_delta

    # Apply overall minimum charge
    minimum_applied = False
    total_cash = subtotal
    if total_cash < MINIMUM_CHARGE_CAD:
        minimum_applied = True
        items.append(
            QuoteLineItem(
                code="minimum",
                label=f"Minimum charge adjustment (to ${MINIMUM_CHARGE_CAD:.0f})",
                amount_cad=_round_money(MINIMUM_CHARGE_CAD - total_cash),
            )
        )
        total_cash = MINIMUM_CHARGE_CAD

    # Dual totals: cash (no tax) and EMT (HST included)
    hst_rate = HST_RATE_EMT
    hst = _round_money(total_cash * hst_rate)
    total_emt = _round_money(total_cash + hst)

    assumptions.append("Cash payments are tax-free in this system.")
    assumptions.append("EMT/e-transfer adds 13% HST to the cash total.")

    has_dump = float(req.dump_fees_cad) > 0
    mattresses_count = int(req.mattresses_count)
    box_springs_count = int(req.box_springs_count)

    return CalcResult(
        line_items=items,
        assumptions=assumptions,
        subtotal=_round_money(subtotal),
        minimum_applied=minimum_applied,
        total_cash=_round_money(total_cash),
        hst_rate=float(f"{hst_rate:.2f}"),
        hst=hst,
        total_emt=total_emt,
        crew_size=crew_size,
        towing_mode=req.towing_mode,
        has_dump=has_dump,
        has_stairs_or_heavy=has_stairs_or_heavy,
        has_complexity=has_complexity,
        mattresses_count=mattresses_count,
        box_springs_count=box_springs_count,
    )


# =========================
# Routes
# =========================

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "time": datetime.utcnow().isoformat() + "Z", "version": app.version}


@app.post("/quote/calculate", response_model=QuoteResponse)
def quote_calculate(req: QuoteRequest) -> QuoteResponse:
    result = calculate_quote(req)
    quote_id = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    # Customer summary (minimal words, minimal $; exception: mattress/box spring show amounts)
    has_labor = any(li.code in {"labor"} for li in result.line_items)
    has_travel_or_towing = any(li.code in {"travel_gas_min", "travel_wear_min", "travel_variable", "towing"} for li in result.line_items)

    customer_summary = _build_customer_summary(
        has_labor=has_labor,
        has_travel_or_towing=has_travel_or_towing,
        has_dump=result.has_dump,
        has_stairs_or_heavy=result.has_stairs_or_heavy,
        has_complexity=result.has_complexity,
        mattresses_count=result.mattresses_count,
        box_springs_count=result.box_springs_count,
    )

    resp = QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        subtotal_cad=result.subtotal,
        minimum_applied=result.minimum_applied,
        total_cash_cad=result.total_cash,
        hst_rate=result.hst_rate,
        hst_cad=result.hst,
        total_emt_cad=result.total_emt,
        service_type=req.service_type,
        crew_size=result.crew_size,
        towing_mode=result.towing_mode,
        line_items_internal=result.line_items,
        customer_summary=customer_summary,
        assumptions=result.assumptions,
    )

    # Store cash base as "total_cad" for sorting/search (stable baseline)
    save_quote(
        quote_id=quote_id,
        created_at=created_at,
        job_type=req.service_type.value,
        total_cad=resp.total_cash_cad,
        request_obj=req.model_dump(),
        response_obj=resp.model_dump(),
    )
    return resp


@app.get("/quote/{quote_id}", response_model=QuoteResponse)
def quote_get(quote_id: str) -> QuoteResponse:
    data = get_quote(quote_id)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteResponse(**data)


@app.get("/quote", response_model=List[Dict[str, Any]])
def quote_list(limit: int = 50) -> List[Dict[str, Any]]:
    return list_quotes(limit=limit)


@app.get("/quote/search", response_model=List[Dict[str, Any]])
def quote_search(
    limit: int = 50,
    job_type: Optional[str] = None,
    min_total: Optional[float] = None,
    max_total: Optional[float] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return search_quotes(
        limit=limit,
        job_type=job_type,
        min_total=min_total,
        max_total=max_total,
        after=after,
        before=before,
    )


@app.post("/job/from-quote/{quote_id}", response_model=JobResponse)
def job_from_quote(quote_id: str, req: JobCreateFromQuoteRequest) -> JobResponse:
    quote = get_quote(quote_id)
    if not quote:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Quote not found")

    job_id = str(uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"

    # Choose job total based on payment method (cash vs EMT)
    if req.payment_method == PaymentMethod.emt:
        total = float(quote["total_emt_cad"])
    else:
        total = float(quote["total_cash_cad"])

    paid = float(req.deposit_paid_cad)
    owing = max(0.0, total - paid)

    job = {
        "job_id": job_id,
        "created_at": created_at,
        "quote_id": quote_id,
        "status": JobStatus.booked.value,
        "customer_name": req.customer_name,
        "job_address": req.job_address,
        "scheduled_start": req.scheduled_start,
        "scheduled_end": req.scheduled_end,
        "payment_method": req.payment_method.value,
        "total_cad": _round_money(total),
        "paid_cad": _round_money(paid),
        "owing_cad": _round_money(owing),
        "notes": req.notes,
        "quote_snapshot": quote,
    }

    save_job(
        {
            "job_id": job_id,
            "created_at": created_at,
            "quote_id": quote_id,
            "status": job["status"],
            "customer_name": req.customer_name,
            "job_address": req.job_address,
            "scheduled_start": req.scheduled_start,
            "scheduled_end": req.scheduled_end,
            "total_cad": float(job["total_cad"]),
            "paid_cad": float(job["paid_cad"]),
            "owing_cad": float(job["owing_cad"]),
            "notes": req.notes,
            "job_json": job,
        }
    )

    return JobResponse(
        job_id=job_id,
        created_at=created_at,
        quote_id=quote_id,
        status=JobStatus(job["status"]),
        customer_name=req.customer_name,
        job_address=req.job_address,
        scheduled_start=req.scheduled_start,
        scheduled_end=req.scheduled_end,
        payment_method=req.payment_method,
        total_cad=float(job["total_cad"]),
        paid_cad=float(job["paid_cad"]),
        owing_cad=float(job["owing_cad"]),
        notes=req.notes,
        quote_snapshot=quote,
    )


@app.get("/job/{job_id}", response_model=JobResponse)
def job_get(job_id: str) -> JobResponse:
    data = get_job(job_id)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    pm_raw = data.get("payment_method", "cash")
    pm = PaymentMethod.emt if pm_raw == "emt" else PaymentMethod.cash

    return JobResponse(
        job_id=data["job_id"],
        created_at=data["created_at"],
        quote_id=data["quote_id"],
        status=JobStatus(data["status"]),
        customer_name=data.get("customer_name"),
        job_address=data.get("job_address"),
        scheduled_start=data.get("scheduled_start"),
        scheduled_end=data.get("scheduled_end"),
        payment_method=pm,
        total_cad=float(data["total_cad"]),
        paid_cad=float(data["paid_cad"]),
        owing_cad=float(data["owing_cad"]),
        notes=data.get("notes"),
        quote_snapshot=data["quote_snapshot"],
    )


@app.get("/job", response_model=List[Dict[str, Any]])
def job_list(
    limit: int = 50,
    status: Optional[JobStatus] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return list_jobs(
        limit=limit,
        status=status.value if status else None,
        after=after,
        before=before,
    )


@app.patch("/job/{job_id}", response_model=JobResponse)
def job_update(job_id: str, req: JobUpdateRequest) -> JobResponse:
    updated = update_job_fields(
        job_id,
        status=req.status.value if req.status else None,
        customer_name=req.customer_name,
        job_address=req.job_address,
        scheduled_start=req.scheduled_start,
        scheduled_end=req.scheduled_end,
        paid_cad=float(req.paid_cad) if req.paid_cad is not None else None,
        notes=req.notes,
    )

    if not updated:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    pm_raw = updated.get("payment_method", "cash")
    pm = PaymentMethod.emt if pm_raw == "emt" else PaymentMethod.cash

    return JobResponse(
        job_id=updated["job_id"],
        created_at=updated["created_at"],
        quote_id=updated["quote_id"],
        status=JobStatus(updated["status"]),
        customer_name=updated.get("customer_name"),
        job_address=updated.get("job_address"),
        scheduled_start=updated.get("scheduled_start"),
        scheduled_end=updated.get("scheduled_end"),
        payment_method=pm,
        total_cad=float(updated["total_cad"]),
        paid_cad=float(updated["paid_cad"]),
        owing_cad=float(updated["owing_cad"]),
        notes=updated.get("notes"),
        quote_snapshot=updated["quote_snapshot"],
    )
