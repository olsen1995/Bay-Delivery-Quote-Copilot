from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Annotated
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# =========================
# App
# =========================

app = FastAPI(
    title="Bay Delivery Quote Copilot API",
    version="0.2.1",
    description="Backend for Bay Delivery Quotes & Ops: quote calculator + customer messaging helpers.",
)

# CORS: permissive for local dev; tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# Business Rules (Known)
# =========================

CAD = "CAD"

MINIMUM_CHARGE_CAD = 50.00
MIN_GAS_CAD = 20.00
MIN_WEAR_CAD = 20.00

MATTRESS_FEE_EACH_CAD = 50.00  # mattress or box spring
CURBSIDE_SCRAP_EASY_CAD = 0.00
CURBSIDE_SCRAP_EASY_NOT_FREE_CAD = 30.00

DEFAULT_HOURLY_RATE_CAD = 80.00  # placeholder; override per request
DEFAULT_COMPLEXITY_MULTIPLIER = 1.0


class TruckType(str, Enum):
    ram_2015 = "2015_ram_1500_5_7"
    ram_2019 = "2019_ram_1500_warlock_5_7"


# Travel tuning knobs
DEFAULT_TRAVEL_PER_KM_CAD = 0.35
DEFAULT_TRAVEL_FREE_KM = 10.0


# =========================
# Type aliases (Pydantic v2 friendly)
# =========================

NonNegFloat = Annotated[float, Field(ge=0)]
NonNegInt = Annotated[int, Field(ge=0)]
ComplexityMult = Annotated[float, Field(ge=0.5, le=3.0)]


# =========================
# Data Models
# =========================

class QuoteLineItem(BaseModel):
    code: str
    label: str
    amount_cad: NonNegFloat = 0.0
    notes: Optional[str] = None


class QuoteRequest(BaseModel):
    # Core job info
    job_type: str = Field(..., description="e.g., dump_run, scrap_pickup, small_move, demolition, delivery")
    distance_km: NonNegFloat = 0.0
    estimated_hours: NonNegFloat = 0.0

    # Labor / staffing
    hourly_rate_cad: NonNegFloat = DEFAULT_HOURLY_RATE_CAD
    helpers_count: NonNegInt = 0
    helper_hourly_rate_cad: NonNegFloat = 0.0  # if you pay helpers and bill it through

    # Disposal / dump details
    dump_fees_cad: NonNegFloat = 0.0  # pass-through (landfill / dump)
    mattresses_count: NonNegInt = 0
    box_springs_count: NonNegInt = 0

    # Scrap pickup specifics
    is_scrap_pickup: bool = False
    curbside_easy: bool = False
    curbside_easy_but_charge_30: bool = False
    scrap_difficult_surcharge_cad: NonNegFloat = 0.0

    # Complexity + stairs/heavy items (user supplies dollar surcharges for now)
    complexity_multiplier: ComplexityMult = DEFAULT_COMPLEXITY_MULTIPLIER
    stairs_surcharge_cad: NonNegFloat = 0.0
    heavy_items_surcharge_cad: NonNegFloat = 0.0

    # Travel cost tuning knobs
    min_gas_cad: NonNegFloat = MIN_GAS_CAD
    min_wear_cad: NonNegFloat = MIN_WEAR_CAD
    travel_per_km_cad: NonNegFloat = DEFAULT_TRAVEL_PER_KM_CAD
    travel_free_km: NonNegFloat = DEFAULT_TRAVEL_FREE_KM

    # Misc
    truck_type: TruckType = TruckType.ram_2015
    notes: Optional[str] = None


class QuoteResponse(BaseModel):
    quote_id: str
    created_at: str
    currency: str = CAD

    subtotal_cad: float
    minimum_applied: bool
    total_cad: float

    line_items: List[QuoteLineItem]
    assumptions: List[str]


class CustomerMessageRequest(BaseModel):
    customer_name: Optional[str] = None
    quote: QuoteResponse
    tone: str = "friendly"  # friendly / firm / short


class CustomerMessageResponse(BaseModel):
    message: str


class AdRequest(BaseModel):
    service: str
    city: str = "North Bay"
    hook: str = "Fast, reliable, no nonsense."
    include_price_hint: bool = True
    price_hint: str = "Quotes start at $50+ (depends on load & distance)."


class AdResponse(BaseModel):
    headline: str
    body: str
    bullets: List[str]


class InvoiceRequest(BaseModel):
    customer_name: str
    job_address: Optional[str] = None
    quote: QuoteResponse
    paid_cad: NonNegFloat = 0.0


class InvoiceResponse(BaseModel):
    invoice_text: str


# =========================
# In-memory storage (swap to DB later)
# =========================

_QUOTES: Dict[str, QuoteResponse] = {}


# =========================
# Quote Engine
# =========================

@dataclass
class CalcResult:
    line_items: List[QuoteLineItem]
    assumptions: List[str]
    subtotal: float
    minimum_applied: bool
    total: float


def _round_money(x: float) -> float:
    return float(f"{x:.2f}")


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
    total = subtotal
    if total < MINIMUM_CHARGE_CAD:
        minimum_applied = True
        items.append(
            QuoteLineItem(
                code="minimum",
                label=f"Minimum charge adjustment (to ${MINIMUM_CHARGE_CAD:.0f})",
                amount_cad=_round_money(MINIMUM_CHARGE_CAD - total),
            )
        )
        total = MINIMUM_CHARGE_CAD

    return CalcResult(
        line_items=items,
        assumptions=assumptions,
        subtotal=_round_money(subtotal),
        minimum_applied=minimum_applied,
        total=_round_money(total),
    )


# =========================
# Routes
# =========================

@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "bay-delivery-quote-copilot",
        "time": datetime.utcnow().isoformat() + "Z",
        "version": app.version,
    }


@app.post("/quote/calculate", response_model=QuoteResponse)
def quote_calculate(req: QuoteRequest) -> QuoteResponse:
    result = calculate_quote(req)
    quote_id = str(uuid4())

    resp = QuoteResponse(
        quote_id=quote_id,
        created_at=datetime.utcnow().isoformat() + "Z",
        subtotal_cad=result.subtotal,
        minimum_applied=result.minimum_applied,
        total_cad=result.total,
        line_items=result.line_items,
        assumptions=result.assumptions,
    )
    _QUOTES[quote_id] = resp
    return resp


@app.get("/quote/{quote_id}", response_model=QuoteResponse)
def quote_get(quote_id: str) -> QuoteResponse:
    q = _QUOTES.get(quote_id)
    if not q:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Quote not found")
    return q


@app.post("/quote/customer-message", response_model=CustomerMessageResponse)
def quote_customer_message(req: CustomerMessageRequest) -> CustomerMessageResponse:
    q = req.quote
    name = req.customer_name or "there"

    if req.tone == "short":
        msg = (
            f"Hey {name}! Your estimate is **${q.total_cad:.2f} CAD**.\n"
            f"If you want, send the address + what items/how many and I’ll lock it in."
        )
    elif req.tone == "firm":
        msg = (
            f"Hi {name}, based on the details provided your estimate comes to **${q.total_cad:.2f} CAD**.\n"
            f"This includes travel, labour/handling, and any disposal fees in the breakdown.\n"
            f"If stairs/heavy items/dump fees change on-site, the total may adjust."
        )
    else:
        msg = (
            f"Hey {name}! 😊 Based on what you told me, your estimate is **${q.total_cad:.2f} CAD**.\n\n"
            f"**What’s included:**\n"
            f"- Travel (gas + wear)\n"
            f"- Labour/handling\n"
            f"- Disposal fees (if applicable)\n\n"
            f"If you send a quick photo of the load (or list of items + address), I can confirm the quote and give you a time window."
        )

    return CustomerMessageResponse(message=msg)


@app.post("/ads/generate", response_model=AdResponse)
def ads_generate(req: AdRequest) -> AdResponse:
    headline = f"{req.city} {req.service} — Fast & Fair"
    bullets = [
        "Same-day or next-day when possible",
        "Dump runs, scrap pickup, small moves",
        "Careful handling (no drama)",
        "Clear pricing — no surprise nonsense",
    ]
    body = f"{req.hook} Serving {req.city} and nearby. "
    if req.include_price_hint:
        body += req.price_hint

    return AdResponse(headline=headline, body=body, bullets=bullets)


@app.post("/invoice/render", response_model=InvoiceResponse)
def invoice_render(req: InvoiceRequest) -> InvoiceResponse:
    q = req.quote
    owing = max(0.0, float(q.total_cad) - float(req.paid_cad))

    lines = [
        "BAY DELIVERY — INVOICE",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        f"Customer: {req.customer_name}",
    ]
    if req.job_address:
        lines.append(f"Address: {req.job_address}")

    lines += ["", "Breakdown:"]
    for li in q.line_items:
        lines.append(f"- {li.label}: ${float(li.amount_cad):.2f} CAD")

    lines += [
        "",
        f"Total: ${float(q.total_cad):.2f} CAD",
        f"Paid:  ${float(req.paid_cad):.2f} CAD",
        f"Owing: ${owing:.2f} CAD",
    ]

    return InvoiceResponse(invoice_text="\n".join(lines))
