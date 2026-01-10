# RC Car Power Troubleshooting Ladder

## 1) Confirm model/setup
- Vehicle model + drivetrain type (2WD/4WD) and weight.
- Motor type, kV/turns, and rated voltage.
- ESC specs (continuous/peak current, LiPo cell count).
- Battery specs (cell count, capacity, C‑rating).
- Gearing (pinion/spur) and tire size.

## 2) Define the goal
- What exactly is improving? (speed, punch, run‑time, temperatures).
- Set a clear baseline target (e.g., “10% more top speed without exceeding 160°F/71°C”).

## 3) Diagnose the limiter
- **Overheating?** Motor/ESC too hot, thermal cutoff, or fading power.
- **Voltage sag?** Battery drops under load; weak punch or short run‑time.
- **Mechanical drag?** Binding drivetrain, tight bearings, rubbing tires.

## 4) Upgrade/test ladder (one change at a time)
1. **Cooling**: add heat sink/fan; improve airflow; clean debris.
2. **Gearing**: gear down if temps are high; gear up only after cool runs.
3. **ESC match**: ensure ESC current rating exceeds motor demand.
4. **Connectors**: upgrade to low‑resistance plugs/wire (e.g., XT60/XT90) and verify solder joints.

## 5) Validation
- **Heat check procedure**: after a 2–3 minute run, stop and measure motor/ESC temps. Keep motor under ~160°F/71°C and ESC under its rated limit.
- **Baseline run‑time**: record minutes per pack at a consistent driving style and surface.

## 6) LiPo safety reminders
- Use a LiPo‑safe bag for charging and storage.
- Never charge unattended; balance‑charge every time.
- Stop at low‑voltage cutoff; do not over‑discharge.
- Inspect for swelling or damage; retire unsafe packs.
