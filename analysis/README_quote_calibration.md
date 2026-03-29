# Quote Calibration Framework

## Purpose

The quote calibration framework compares the Bay Delivery Quote Copilot's system-generated quotes against real-world expected Bay Delivery pricing. This enables data-driven tuning of the quote engine based on actual business examples rather than assumptions.

The framework identifies:
- **Undercharging scenarios**: Cases where the system estimates too low
- **Overcharging scenarios**: Cases where the system estimates too high
- **Pricing accuracy**: Scenarios within acceptable tolerance (±15%)
- **Tuning targets**: High-impact pricing adjustments that improve overall accuracy

## Files

- **`quote_calibration_dataset.json`**: Calibration scenarios with expected pricing
- **`run_quote_calibration.py`**: Runner script that executes calibration analysis
- **`README_quote_calibration.md`**: This file

## How to Run

### Prerequisites

Ensure the virtual environment is activated and dependencies are installed:

```bash
# On Windows with PowerShell
if (Test-Path .\\.venv\\Scripts\\Activate.ps1) { 
    . .\\.venv\\Scripts\\Activate.ps1 
} elseif (Test-Path .\\venv\\Scripts\\Activate.ps1) { 
    . .\\venv\\Scripts\\Activate.ps1 
}

# Ensure dependencies
pip install -r requirements.txt
```

### Running the Calibration

```bash
python analysis/run_quote_calibration.py
```

This will:
1. Load all scenarios from `quote_calibration_dataset.json`
2. Run each scenario through the quote engine
3. Output a comparison table
4. Display summary statistics

### Example Output

```
Scenario ID              Expected     System       Difference    %
junk-basement-01         $120.00      $105.00      $-15.00      -12.5%
junk-easy-01             $85.00       $82.50       $-2.50       -2.9%
drywall-cleanup-01       $210.00      $208.00      $-2.00       -1.0%
...

ANALYSIS SUMMARY
Total Scenarios: 20
Average Difference: $-8.50 (-4.2%)
Scenarios with Underquotes (>$5): 6
Scenarios with Overquotes (>$5): 2
Scenarios Outside ±15%: 3

Largest Underquote:
  extreme-access-01: Expected $245.00, System $210.00, Difference $-35.00 (-14.3%)

Largest Overquote:
  garage-cleanout-01: Expected $310.00, System $340.00, Difference $+30.00 (+9.7%)
```

## How to Add Scenarios

### Structure

Each scenario in `quote_calibration_dataset.json` follows this structure:

```json
{
  "scenario_id": "unique-scenario-name",
  "description": "Human-readable description of the job",
  "service_type": "haul_away" | "small_move" | "other",
  "bag_count": 8,
  "large_items": 1,
  "crew": 1,
  "access_difficulty": "normal" | "difficult" | "extreme",
  "has_dense_materials": false,
  "distance_km": 4,
  "expected_price_cad": 120,
  "notes": "Context and reasoning for expected price"
}
```

### Required Fields

- **`scenario_id`**: Unique identifier (use hyphens, lowercase)
- **`description`**: Clear description of the job type
- **`service_type`**: Must match a service type in the quote engine (typically `haul_away` or `small_move`)
- **`expected_price_cad`**: The expected Bay Delivery quote for this job (real-world or estimated)
- **`notes`**: Reasoning for the expected price

### Optional Fields

- **`bag_count`**: Number of garbage bags (for haul_away)
- **`large_items`**: Count of bulk items
- **`crew`**: Crew size (1 or 2+)
- **`access_difficulty`**: Job difficulty level
- **`has_dense_materials`**: Whether materials are heavy/dense
- **`distance_km`**: Approximate distance from base

### Best Practices

1. **Collect real examples**: Use actual Bay Delivery job requests when possible
2. **Vary scenarios**: Include easy, moderate, and difficult jobs
3. **Cover edge cases**: Include extreme access, far distances, dense materials
4. **Document reasoning**: Use notes to explain expected pricing
5. **Avoid assumptions**: If unsure, err toward conservative, realistic pricing

## How to Interpret Results

### Acceptable Range: ±15%

The framework considers quotes within **±15% of expected** as acceptable. This tolerance accounts for:
- Natural variation in job details
- Regional pricing adjustments
- Implementation differences between rules and system calculation

### Key Metrics

| Metric | Meaning |
|--------|---------|
| **Average Difference** | Mean variance from expected; zero is ideal |
| **% Difference** | Percentage variance (helpful for comparing different price ranges) |
| **Underquotes** | Scenarios where system undercharges (lost revenue) |
| **Overquotes** | Scenarios where system overcharges (lost customers) |
| **Outliers** | Scenarios >±15% (candidates for investigation or tuning) |

### When to Tune the Quote Engine

Investigate tuning when:
1. You see consistent underquoting in a specific scenario (e.g., all "extreme access" jobs)
2. Largest underquote exceeds 20% (revenue loss)
3. More than 30% of scenarios fall outside ±15%

### Tuning Targets

Common tuning targets in `app/quote_engine.py`:

- **`ACCESS_DIFFICULTY_ADDERS`**: Surcharges for difficult/extreme access
- **`DENSE_MATERIAL_LABOUR_MULTIPLIER`**: Adjustment for heavy materials
- **`TRAVEL_ZONE_ADDERS`**: Distance-based surcharges
- **`DEFAULT_BAG_TIER_*_PRICE`**: Disposal allowance tiers
- **Hourly rates**: Service-specific labor costs

## Workflow

### Regular Calibration Cycle

1. **Collect new real-world jobs** (monthly or as cases arise)
2. **Add scenarios** to `quote_calibration_dataset.json`
3. **Run calibration**: `python analysis/run_quote_calibration.py`
4. **Review results**: Identify systematic biases
5. **Tune if needed**: Adjust `quote_engine.py` based on findings
6. **Validate**: Run calibration again to confirm improvements
7. **Commit changes**: Document tuning in PR

## Safety & Constraints

- **No production code changes**: This analysis framework does not modify `app/` or any quote logic
- **Read-only operation**: The runner script only reads the dataset and quote engine
- **No database writes**: Calibration is purely computational
- **Portable**: Can be run in CI, manually, or scheduled

## Common Questions

### Q: How do I know if my expected_price_cad is accurate?

Look for patterns:
- Compare against competing junk removal services in your area
- Consult historical Bay Delivery quotes if available
- Consider labor hours, materials, distance, and access
- Use the system quote as a sanity check

### Q: What if the system quote differs due to missing parameters?

The runner script uses consistent defaults (e.g., `travel_zone="in_town"`). If scenarios need special handling, update the runner to pass additional parameters or add scenario metadata.

### Q: Should I add every possible job combination?

No. Focus on:
- Common job types (drywall, junk, moves)
- Edge cases (extreme access, far distance, dense materials)
- Problem areas (if you notice the system consistently misprice certain jobs)
- Representative diversity (20-30 scenarios cover most variation)

### Q: What if a scenario fails?

The runner logs errors to stderr. Check:
1. JSON syntax in the dataset
2. Service type spelling
3. Numeric parameters (hours, bag_count, etc.)
4. Required fields are present

## Next Steps

- **Collect real quotes**: Start with 5-10 actual Bay Delivery jobs
- **Run initial calibration**: Establish baseline accuracy
- **Identify tuning targets**: Review outliers
- **Iterate**: Tune pricing logic and re-run as needed
