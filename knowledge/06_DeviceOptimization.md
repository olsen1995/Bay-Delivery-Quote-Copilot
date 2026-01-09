# Device Optimization

**No debloat that breaks updates.**

## Principles
- Prefer reversible changes (document what you change).
- Measure before/after for every action.
- Do not break updates, security, or OEM support.

## Flow
1. Identify device + OS + symptom.
2. Snapshot baseline (startup items, storage, temps).
3. List likely causes (apps, services, drivers, storage pressure, heat).
4. Take safe actions first.
5. Take advanced actions with warnings.
6. Validate results and roll back if needed.

## Metrics to capture
- Boot time
- Idle CPU/RAM
- Disk usage
- Temps

## Safe actions first
- Remove obvious startup bloat (disable, don’t delete).
- Free storage (clear large files, caches you can restore).
- Update OS and drivers via official channels.
- Check for malware with trusted tools.
- Improve airflow/clean vents; verify fan behavior.

## Advanced actions (warnings)
- Disable nonessential services only if you can revert.
- BIOS/UEFI tweaks: document defaults and revert plan.
- Undervolting/overclocking: risky, can reduce stability.
- OS reinstall: backup, verify recovery media.

## Validate + rollback
- Re-measure metrics and compare to baseline.
- If worse or unstable, revert the last change.
- Keep a change log for future reference.
