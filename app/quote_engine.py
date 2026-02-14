from typing import Dict

MIN_GAS = 20
MIN_WEAR = 20


def calculate_base_charge(hours: float, hourly_rate: float) -> float:
    return hours * hourly_rate


def calculate_total(hours: float, hourly_rate: float, dump_fee_estimate: float = 0) -> Dict:
    labour = calculate_base_charge(hours, hourly_rate)
    total = labour + MIN_GAS + MIN_WEAR + dump_fee_estimate

    return {
        "labour": labour,
        "gas": MIN_GAS,
        "wear_and_tear": MIN_WEAR,
        "dump_fee_estimate": dump_fee_estimate,
        "total_estimate": total,
        "note": "Final price confirmed on site."
    }
