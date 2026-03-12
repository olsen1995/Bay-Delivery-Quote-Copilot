#!/usr/bin/env python3
"""
Quote Calibration Runner

Compares system quote estimates against expected Bay Delivery pricing
to identify tuning opportunities.

Usage:
  python analysis/run_quote_calibration.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.quote_engine import calculate_quote


def load_dataset(dataset_path: str = "analysis/quote_calibration_dataset.json") -> List[Dict[str, Any]]:
    """Load calibration dataset."""
    with open(dataset_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_scenario(scenario: Dict[str, Any]) -> Tuple[float, float, float, float]:
    """
    Run a single scenario through the quote engine.
    
    Returns: (system_quote, expected_price, difference, percentage_difference)
    """
    expected_price = float(scenario.get("expected_price_cad", 0))
    service_type = scenario.get("service_type", "haul_away")
    
    try:
        # Determine hours based on service type and scenario data
        if service_type == "haul_away":
            # For haul_away, estimate hours from bag count (~15-20 bags per hour)
            bag_count = scenario.get("bag_count", 0)
            hours = max(0.5, bag_count / 15.0 if bag_count else 0.5)
        else:
            # For other services, use provided hours or default
            hours = scenario.get("hours", 2)
        
        # Common parameters
        crew_size = scenario.get("crew", 1)
        bag_count = scenario.get("bag_count", 0)
        access_difficulty = scenario.get("access_difficulty", "normal")
        has_dense = scenario.get("has_dense_materials", False)
        
        # Call quote engine with positional and keyword arguments
        result = calculate_quote(
            service_type,
            hours,
            crew_size=crew_size,
            garbage_bag_count=bag_count,
            access_difficulty=access_difficulty,
            has_dense_materials=has_dense,
            travel_zone="in_town",  # Default for comparison
        )
        
        # Extract system quote (prefer emt for consistency)
        system_quote = result.get("total_emt_cad") or result.get("total_cash_cad", 0)
        
        difference = system_quote - expected_price
        pct_difference = (difference / expected_price * 100) if expected_price > 0 else 0
        
        return system_quote, expected_price, difference, pct_difference
    
    except Exception as e:
        # If scenario fails, return zeros and log the error
        print(f"  ERROR in {scenario.get('scenario_id', 'unknown')}: {e}", file=sys.stderr)
        return 0, expected_price, -expected_price, -100


def main():
    """Run calibration analysis."""
    print("\n" + "=" * 100)
    print("QUOTE CALIBRATION ANALYSIS")
    print("=" * 100 + "\n")
    
    # Load dataset
    scenarios = load_dataset()
    print(f"Loaded {len(scenarios)} scenarios from quote_calibration_dataset.json\n")
    
    # Run all scenarios
    results = []
    for scenario in scenarios:
        scenario_id = scenario.get("scenario_id", "unknown")
        description = scenario.get("description", "")
        
        system_quote, expected_price, difference, pct_diff = run_scenario(scenario)
        
        results.append({
            "scenario_id": scenario_id,
            "description": description,
            "expected": expected_price,
            "system": system_quote,
            "difference": difference,
            "pct_difference": pct_diff,
        })
    
    # Print results table
    print("\n" + "-" * 100)
    print(f"{'Scenario ID':<25} {'Expected':<12} {'System':<12} {'Difference':<12} {'%':<10}")
    print("-" * 100)
    
    for result in results:
        scenario_id = result["scenario_id"]
        expected = result["expected"]
        system = result["system"]
        difference = result["difference"]
        pct = result["pct_difference"]
        
        # Format row
        print(
            f"{scenario_id:<25} ${expected:<11.2f} ${system:<11.2f} ${difference:+11.2f} {pct:+9.1f}%"
        )
    
    print("-" * 100 + "\n")
    
    # Summary statistics
    differences = [r["difference"] for r in results]
    pct_differences = [r["pct_difference"] for r in results]
    
    avg_diff = sum(differences) / len(differences) if differences else 0
    avg_pct = sum(pct_differences) / len(pct_differences) if pct_differences else 0
    
    # Find outliers (±15%)
    outliers = [r for r in results if abs(r["pct_difference"]) > 15]
    underquotes = [r for r in results if r["difference"] < -5]
    overquotes = [r for r in results if r["difference"] > 5]
    
    largest_underquote = min(results, key=lambda r: r["difference"]) if results else None
    largest_overquote = max(results, key=lambda r: r["difference"]) if results else None
    
    print("ANALYSIS SUMMARY")
    print("-" * 100)
    print(f"Total Scenarios: {len(results)}")
    print(f"Average Difference: ${avg_diff:+.2f} ({avg_pct:+.1f}%)")
    print(f"Scenarios with Underquotes (>$5): {len(underquotes)}")
    print(f"Scenarios with Overquotes (>$5): {len(overquotes)}")
    print(f"Scenarios Outside ±15%: {len(outliers)}")
    
    if largest_underquote:
        print(f"\nLargest Underquote:")
        print(f"  {largest_underquote['scenario_id']}: Expected ${largest_underquote['expected']:.2f}, "
              f"System ${largest_underquote['system']:.2f}, "
              f"Difference ${largest_underquote['difference']:.2f} ({largest_underquote['pct_difference']:.1f}%)")
    
    if largest_overquote:
        print(f"\nLargest Overquote:")
        print(f"  {largest_overquote['scenario_id']}: Expected ${largest_overquote['expected']:.2f}, "
              f"System ${largest_overquote['system']:.2f}, "
              f"Difference ${largest_overquote['difference']:+.2f} ({largest_overquote['pct_difference']:+.1f}%)")
    
    if outliers:
        print(f"\nOutliers (Outside ±15%):")
        for outlier in sorted(outliers, key=lambda r: abs(r["pct_difference"]), reverse=True)[:5]:
            print(f"  {outlier['scenario_id']}: {outlier['pct_difference']:+.1f}%")
    
    print("\n" + "=" * 100 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
