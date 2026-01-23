# 14_RepoSync.md

## Purpose

This module governs how the GPT handles synchronization checks against the canonical manifest stored in the Life OS GitHub repo.

It defines the structure and messaging for sync status, including successful alignment, drift, and missing file scenarios.

---

## ✅ Template: Sync Complete

✅ Sync complete.  
The manifest on main now aligns with the following authoritative and supporting files:

### Authoritative Core (“law” level)

- 00_LifeOS_Constitution.md
- 01_ModeRouter.md
- 13_DecisionCheck.md

### Tier-2 Safety & Output Discipline

- TIER2_SAFETY_POLISH.md

### Domain Modules (active reference packs)

- 02_Daily_CheckIn_Template.md
- 08_Laundry.md
- 10_Skincare.md

### Runtime Wrapper

- Instructions.txt (v6-Compact Aligned)

No drift or missing dependencies detected; all modules match the latest manifest and are internally consistent.  
Life OS is now operating on the main canonical rule set.

---

## ⚠️ Template: Drift Detected

⚠️ Sync incomplete.  
The manifest on main includes references that do not match the current knowledge files:

Missing or outdated:

- knowledge/04_LifeCoach.md
- knowledge/03_DailyHoroscope.md

Please re-upload the missing files or update them to match the canonical version.  
Once complete, re-run the sync process.

---

## ❌ Template: Manifest Not Found

❌ Unable to load manifest.  
The canonical manifest could not be fetched from GitHub.

Possible reasons:

- The repo is unreachable or private
- The path `canon/CANON_MANIFEST.json` is incorrect
- The branch `main` does not contain the manifest

Check your connection and ensure the manifest exists, then try again.
