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
    version="0.5.0",
    description="Backend for Bay Delivery Quotes & Ops: quote calculator + customer messaging helpers.",
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

MINIMUM_CHARGE_CAD = 50.00
MIN_GAS_CAD = 20.00
MIN_WEAR_CAD = 20.00

MATTRESS_FEE_EACH_CAD = 50.00
CURBSIDE_SCRAP_EASY_CAD = 0.00
CURBSIDE_SCRAP_EASY_NOT_FREE_CAD = 30.00

DEFAULT_HOURLY_RATE_CAD = 80.00
DEFAULT_COMPLEXITY_MULTIPLIER = 1.0

HST_RATE_EMT = 0.13


class TruckType(str, Enum):
    ram_2015 = "2015_ram_1500_5_7"
    ram_2019 = "2019_ram_1500_warlock_5_7"


class PaymentMethod(str, Enum):
    cash = "cash"
    emt = "emt"  # e-transfer / EMT


DEFAULT_TRAVEL_PER_KM_CAD = 0.35
DEFAULT_TRAVEL_FREE_KM = 10.0

NonNegFloat = Annotated[float, Field(ge=0)]
NonNegInt = Annotated[int, Field(ge=0)]
ComplexityMult = Annotated[float, Field(ge=0.5, le=3.0)]


class QuoteLineItem(BaseModel):
    code: str
    label: str
    amount_cad: NonNegFloat = 0.0
    notes: Optional[str] = None


class QuoteRequest(BaseModel):
    job_type: str = Field(..., description="e.g., dump_run, scrap_pickup, small_move, demolition, delivery")
    distance_km: NonNegFloat = 0.0
    estimated_hours: NonNegFloat = 0.0

    hourly_rate_cad: NonNegFloat = DEFAULT_HOURLY_RATE_CAD
    helpers_count: NonNegInt = 0
    helper_hourly_rate_cad: NonNegFloat = 0.0

    dump_fees_cad: NonNegFloat = 0.0
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0

    is_scrap_pickup: bool = False
    curbside_easy: bool = False
    curbside_easy_but_charge_30: bool = False
    scrap_difficult_surcharge_cad: NonNegFloat = 0.0

    complexity_multiplier: ComplexityMult = DEFAULT_COMPLEXITY_MULTIPLIER
    stairs_surcharge_cad: NonNegFloat = 0.0
    heavy_items_surcharge_cad: NonNegFloat = 0.0

    min_gas_cad: NonNegFloat = MIN_GAS_CAD
    min_wear_cad: NonNegFloat = MIN_WEAR_CAD
    travel_per_km_cad: NonNegFloat = DEFAULT_TRAVEL_PER_KM_CAD
    travel_free_km: NonNegFloat = DEFAULT_TRAVEL_FREE_KM

    truck_type: TruckType = TruckType.ram_2015

    payment_method: PaymentMethod = PaymentMethod.cash
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD

    # BEFORE TAX
    subtotal_cad: float
    minimum_applied: bool

    # TAX
    payment_method: PaymentMethod
    tax_rate: float
    tax_cad: float

    # FINAL
    total_before_tax_cad: float
    total_cad: float

    line_items: List[QuoteLineItem]
    assumptions: List[str]


class CustomerMessageRequest(BaseModel):
    customer_name: Optional[str] = None
    quote: QuoteResponse
    tone: str = "friendly"


class CustomerMessageResponse(BaseModel):
    message: str


# =========================
# Jobs Models
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
    scheduled_start: Optional[str] = Field(None, description="ISO string preferred, e.g. 2026-02-16T14:00:00-05:00")
    scheduled_end: Optional[str] = Field(None, description="ISO string preferred")
    deposit_paid_cad: NonNegFloat = 0.0
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
    total_before_tax: float
    tax_rate: float
    tax: float
    total: float


def _round_money(x: float) -> float:
    return float(f"{x:.2f}")


def _tax_rate_for_method(method: PaymentMethod) -> float:
    if method == PaymentMethod.emt:
        return HST_RATE_EMT
    return 0.0


def _calc_travel(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float]:
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

    return items, assumptions, _round_money(gas + wear + variable_cost)


def _calc_labor(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float]:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []

    hours = float(req.estimated_hours)
    base_labor = hours * float(req.hourly_rate_cad)

    if hours > 0:
        items.append(
            QuoteLineItem(
                code="labor",
                label=f"Labour ({_round_money(hours)} hrs @ ${_round_money(req.hourly_rate_cad)}/hr)",
                amount_cad=_round_money(base_labor),
            )
        )
    else:
        assumptions.append("Labour hours not provided; labour line item omitted (quote may be low).")

    helper_total = 0.0
    if req.helpers_count > 0 and float(req.helper_hourly_rate_cad) > 0 and hours > 0:
        helper_total = float(req.helpers_count) * hours * float(req.helper_hourly_rate_cad)
        items.append(
            QuoteLineItem(
                code="helpers",
                label=f"Helpers ({req.helpers_count} × {_round_money(hours)} hrs @ ${_round_money(req.helper_hourly_rate_cad)}/hr)",
                amount_cad=_round_money(helper_total),
            )
        )
    elif req.helpers_count > 0:
        assumptions.append("Helpers count provided but helper hourly rate/hours missing; helpers not billed in calculation.")

    return items, assumptions, _round_money(base_labor + helper_total)


def _calc_disposal(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float]:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []

    dump_fees = float(req.dump_fees_cad)
    if dump_fees > 0:
        items.append(QuoteLineItem(code="dump_fees", label="Dump / landfill fees (pass-through)", amount_cad=_round_money(dump_fees)))
    else:
        assumptions.append("Dump fees set to $0 (confirm actual landfill/dump cost).")

    mattress_total = (int(req.mattresses_count) + int(req.box_springs_count)) * MATTRESS_FEE_EACH_CAD
    if mattress_total > 0:
        items.append(
            QuoteLineItem(
                code="mattress_fees",
                label=f"Mattress/box spring disposal ({int(req.mattresses_count) + int(req.box_springs_count)} × ${MATTRESS_FEE_EACH_CAD:.0f})",
                amount_cad=_round_money(mattress_total),
            )
        )

    return items, assumptions, _round_money(dump_fees + mattress_total)


def _calc_scrap(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float]:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []
    total = 0.0

    if not req.is_scrap_pickup:
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
        assumptions.append("Difficulty surcharge provided by user (confirm site conditions).")
        total += float(req.scrap_difficult_surcharge_cad)

    return items, assumptions, _round_money(total)


def _calc_surcharges(req: QuoteRequest) -> Tuple[List[QuoteLineItem], List[str], float]:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []
    s = 0.0

    if float(req.stairs_surcharge_cad) > 0:
        items.append(QuoteLineItem(code="stairs", label="Stairs surcharge", amount_cad=_round_money(float(req.stairs_surcharge_cad))))
        s += float(req.stairs_surcharge_cad)
    if float(req.heavy_items_surcharge_cad) > 0:
        items.append(QuoteLineItem(code="heavy_items", label="Heavy items surcharge", amount_cad=_round_money(float(req.heavy_items_surcharge_cad))))
        s += float(req.heavy_items_surcharge_cad)

    if s == 0:
        assumptions.append("No stairs/heavy-item surcharge included (confirm if applicable).")

    return items, assumptions, _round_money(s)


def calculate_quote(req: QuoteRequest) -> CalcResult:
    items: List[QuoteLineItem] = []
    assumptions: List[str] = []

    travel_items, travel_assumptions, travel_total = _calc_travel(req)
    labor_items, labor_assumptions, labor_total = _calc_labor(req)
    disposal_items, disposal_assumptions, disposal_total = _calc_disposal(req)
    scrap_items, scrap_assumptions, scrap_total = _calc_scrap(req)
    surcharge_items, surcharge_assumptions, surcharge_total = _calc_surcharges(req)

    items += travel_items + labor_items + disposal_items + scrap_items + surcharge_items
    assumptions += travel_assumptions + labor_assumptions + disposal_assumptions + scrap_assumptions + surcharge_assumptions

    pre_multiplier = travel_total + labor_total + disposal_total + scrap_total + surcharge_total

    complexity = float(req.complexity_multiplier)
    multiplier_base = travel_total + labor_total + scrap_total + surcharge_total
    multiplier_delta = 0.0

    if complexity != 1.0 and multiplier_base > 0:
        multiplied = multiplier_base * complexity
        multiplier_delta = multiplied - multiplier_base
        items.append(
            QuoteLineItem(
                code="complexity",
                label=f"Complexity multiplier ({complexity:.2f}× applied to labour/handling)",
                amount_cad=_round_money(multiplier_delta),
                notes="Does not multiply dump fees.",
            )
        )
        assumptions.append("Complexity multiplier applied to travel/labour/handling only (not dump fees).")

    subtotal = pre_multiplier + multiplier_delta

    minimum_applied = False
    total_before_tax = subtotal
    if total_before_tax < MINIMUM_CHARGE_CAD:
        minimum_applied = True
        items.append(
            QuoteLineItem(
                code="minimum",
                label=f"Minimum charge adjustment (to ${MINIMUM_CHARGE_CAD:.0f})",
                amount_cad=_round_money(MINIMUM_CHARGE_CAD - total_before_tax),
            )
        )
        total_before_tax = MINIMUM_CHARGE_CAD

    tax_rate = _tax_rate_for_method(req.payment_method)
    tax = _round_money(total_before_tax * tax_rate)
    total = _round_money(total_before_tax + tax)

    if tax_rate > 0:
        items.append(
            QuoteLineItem(
                code="tax_hst",
                label=f"HST ({int(tax_rate * 100)}%) for EMT payment",
                amount_cad=_round_money(tax),
                notes="Tax applied only when payment method is EMT/e-transfer.",
            )
        )
        assumptions.append("Tax applied because payment method is EMT/e-transfer. Cash payments are tax-free in this system.")
    else:
        assumptions.append("No tax applied because payment method is cash.")

    return CalcResult(
        line_items=items,
        assumptions=assumptions,
        subtotal=_round_money(subtotal),
        minimum_applied=minimum_applied,
        total_before_tax=_round_money(total_before_tax),
        tax_rate=float(f"{tax_rate:.2f}"),
        tax=_round_money(tax),
        total=_round_money(total),
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

    resp = QuoteResponse(
        quote_id=quote_id,
        created_at=created_at,
        subtotal_cad=result.subtotal,
        minimum_applied=result.minimum_applied,
        payment_method=req.payment_method,
        tax_rate=result.tax_rate,
        tax_cad=result.tax,
        total_before_tax_cad=result.total_before_tax,
        total_cad=result.total,
        line_items=result.line_items,
        assumptions=result.assumptions,
    )

    save_quote(
        quote_id=quote_id,
        created_at=created_at,
        job_type=req.job_type,
        total_cad=resp.total_cad,
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

    total = float(quote["total_cad"])
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
        "total_cad": total,
        "paid_cad": paid,
        "owing_cad": owing,
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
            "total_cad": total,
            "paid_cad": paid,
            "owing_cad": owing,
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
        total_cad=total,
        paid_cad=paid,
        owing_cad=owing,
        notes=req.notes,
        quote_snapshot=quote,
    )


@app.get("/job/{job_id}", response_model=JobResponse)
def job_get(job_id: str) -> JobResponse:
    data = get_job(job_id)
    if not data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        job_id=data["job_id"],
        created_at=data["created_at"],
        quote_id=data["quote_id"],
        status=JobStatus(data["status"]),
        customer_name=data.get("customer_name"),
        job_address=data.get("job_address"),
        scheduled_start=data.get("scheduled_start"),
        scheduled_end=data.get("scheduled_end"),
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

    return JobResponse(
        job_id=updated["job_id"],
        created_at=updated["created_at"],
        quote_id=updated["quote_id"],
        status=JobStatus(updated["status"]),
        customer_name=updated.get("customer_name"),
        job_address=updated.get("job_address"),
        scheduled_start=updated.get("scheduled_start"),
        scheduled_end=updated.get("scheduled_end"),
        total_cad=float(updated["total_cad"]),
        paid_cad=float(updated["paid_cad"]),
        owing_cad=float(updated["owing_cad"]),
        notes=updated.get("notes"),
        quote_snapshot=updated["quote_snapshot"],
    )
