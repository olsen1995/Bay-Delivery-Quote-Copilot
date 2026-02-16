import json
from pathlib import Path
from typing import Dict

CONFIG_PATH = Path("config/business_profile.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_quote(service_type: str, hours: float, dump_fee_estimate: float = 0) -> Dict:
    config = load_config()

    services = config["services"]
    minimums = config["minimum_charges"]

    if service_type not in services:
        raise ValueError(f"Service type '{service_type}' not found in config.")

    service_config = services[service_type]

    hourly_rate = service_config["hourly_rate"]
    minimum_hours = service_config["minimum_hours"]

    billable_hours = max(hours, minimum_hours)

    labour = billable_hours * hourly_rate
    total = labour + minimums["gas"] + minimums["wear_and_tear"] + dump_fee_estimate

    return {
        "service_type": service_type,
        "billable_hours": billable_hours,
        "hourly_rate": hourly_rate,
        "labour": labour,
        "gas": minimums["gas"],
        "wear_and_tear": minimums["wear_and_tear"],
        "dump_fee_estimate": dump_fee_estimate,
        "total_estimate": total,
        "note": "Final price confirmed on site."
    }
