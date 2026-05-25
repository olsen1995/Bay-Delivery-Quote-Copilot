# Bay Delivery — Everyday Commands Cheat Sheet

Updated: 2026-05-25  
Repo path: `C:\Repos\Bay-Delivery-Quote-Copilot`

Use PowerShell unless a command says otherwise.

---

## 1. Start Here — Repo Location

| Use | Command | When to use | Notes |
|---|---|---|---|
| Go to Bay Delivery repo | `cd C:\Repos\Bay-Delivery-Quote-Copilot` | Before running repo commands | Run this first. |
| Check current folder | `pwd` | When unsure where PowerShell is | Should show the repo path. |
| List files | `dir` | Quick folder check | Useful if you feel lost. |

---

## 2. Git Status / Sync Commands

| Use | Command | When to use | Notes |
|---|---|---|---|
| Check repo status | `git status --short --branch` | Before/after any task | Clean should look like `## main...origin/main`. |
| Check recent commits | `git log --oneline -5` | After pull/merge | Confirms latest PR commit is present. |
| Switch to main | `git checkout main` | Before verification or new task | Do not do this with dirty files unless you know why. |
| Pull latest main | `git pull origin main` | After a PR is merged | Fast-forward is ideal. |
| Fetch remote only | `git fetch origin` | When you want latest refs without changing files | Safer than pull for inspection. |
| Show changed files | `git diff --name-only` | Before committing/reviewing | Shows modified files. |
| Show full diff | `git diff` | Before committing/reviewing | Inspect actual changes. |
| Check whitespace issues | `git diff --check` | Before commit/PR | Should output nothing. |
| Show last commit details | `git show --stat --oneline HEAD` | After commit | Confirms what changed. |

---

## 3. Safe Post-Merge Verification

| Use | Command | When to use | Expected |
|---|---|---|---|
| Sync main | `git checkout main; git pull origin main` | After merging a PR | main should update cleanly. |
| Check status/log | `git status --short --branch; git log --oneline -5` | After pull | Confirms current main. |
| Version parity | `.\.venv\Scripts\python.exe tools\check_version_parity.py` | Every verification | `Version markers aligned: 0.12.0` |
| GPT grounding parity | `.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py` | Every verification | `GPT grounding pack parity OK` |
| Compile check | `.\.venv\Scripts\python.exe -m compileall app tools scripts tests` | Every verification | No errors. |
| Full test suite | `.\.venv\Scripts\python.exe -m pytest -q` | Preferred after merge | Example: `716 passed` or higher. |

---

## 4. Focused Test Commands

| Area | Command | When to use | Notes |
|---|---|---|---|
| Static/frontend assets | `.\.venv\Scripts\python.exe -m pytest -q tests\test_static_assets.py` | Quote/admin static changes | Fast frontend safety check. |
| Quote structured intake | `.\.venv\Scripts\python.exe -m pytest -q tests\test_quote_structured_intake_fields.py` | Quote form/payload changes | Protects IDs/fields/payload expectations. |
| Playwright smoke | `.\.venv\Scripts\python.exe -m pytest -q tests\test_launch_smoke_playwright.py` | Quote/homepage UI changes | Browser-style smoke test. |
| GPT quote endpoint | `.\.venv\Scripts\python.exe -m pytest -q tests\test_gpt_quote_endpoint.py` | GPT quote work | Internal GPT quote boundary. |
| GPT admin notes | `.\.venv\Scripts\python.exe -m pytest -q tests\test_gpt_admin_notes.py` | GPT note work | Consequential action boundary. |
| Booking notifications | `.\.venv\Scripts\python.exe -m pytest -q tests\test_booking_notifications.py` | Notification changes | Email/status safety. |
| Abuse controls | `.\.venv\Scripts\python.exe -m pytest -q tests\test_abuse_controls.py` | Rate limit/security work | Abuse/rate-limit checks. |
| Admin origin/env/security | `.\.venv\Scripts\python.exe -m pytest -q tests\test_env_and_dependencies.py` | Admin/CORS/origin/env work | Current admin origin tests live here. |

---

## 5. Protected No-Go Diff Examples

### General protected diff

```powershell
git diff main...HEAD -- app/quote_engine.py app/services/quote_service.py app/main.py app/storage.py config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION canon_versions.txt static/admin_mobile.html static/admin_mobile.js .codex/config.toml
```

Expected: **no output** unless those surfaces are explicitly scoped.

### Quote-page frontend PR protected diff

```powershell
git diff main...HEAD -- app/quote_engine.py app/services/quote_service.py app/main.py app/storage.py config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION canon_versions.txt static/admin.html static/admin.js static/admin.css static/admin_mobile.html static/admin_mobile.js .codex/config.toml
```

Expected: **no output**.

### Merge-commit protected diff

Replace `MERGE_SHA` with the merge commit.

```powershell
git diff MERGE_SHA^1 MERGE_SHA -- app/quote_engine.py app/services/quote_service.py app/main.py app/storage.py config/business_profile.json render.yaml .github/workflows docs/gpt dist/gpt_grounding_pack requirements.txt requirements.lock.txt VERSION canon_versions.txt static/admin.html static/admin.js static/admin.css static/admin_mobile.html static/admin_mobile.js .codex/config.toml
```

Expected: **no output**.

---

## 6. Production Live-Safe Smoke

| Use | Command | When to use | Notes |
|---|---|---|---|
| Trigger smoke | `gh workflow run production_live_safe_smoke.yml --ref main` | After public/customer/admin-safe changes merge | Does live-safe checks. |
| List smoke runs | `gh run list --workflow production_live_safe_smoke.yml --limit 5` | After triggering | Get newest run ID/status. |
| Open newest run in browser | `gh run view --web` | Quick visual check | Opens GitHub Actions page. |
| View specific run logs | `gh run view RUN_ID --log` | If run fails | Replace `RUN_ID`. |

---

## 7. Health / Live Checks

| Use | Command | When to use | Notes |
|---|---|---|---|
| Check live health in browser | `https://bay-delivery-quote-copilot.onrender.com/health` | After deploy/smoke | Should show version/commit. |
| PowerShell health check | `Invoke-RestMethod https://bay-delivery-quote-copilot.onrender.com/health` | Quick terminal check | Shows JSON object. |
| Homepage | `https://bay-delivery-quote-copilot.onrender.com/` | Visual check | Customer-facing homepage. |
| Quote page | `https://bay-delivery-quote-copilot.onrender.com/quote` | Visual quote check | Do not submit real quote during QA. |
| Admin page | `https://bay-delivery-quote-copilot.onrender.com/admin` | Pre-auth shell check | Do not mutate unless intended. |
| Mobile admin | `https://bay-delivery-quote-copilot.onrender.com/admin/mobile` | Field check | Do not mutate unless intended. |

---

## 8. GitHub CLI Commands

| Use | Command | When to use | Notes |
|---|---|---|---|
| Check GitHub CLI version | `gh --version` | Update/check tooling | Confirms installed version. |
| Login status | `gh auth status` | If GitHub commands fail | Confirms auth. |
| View PR list | `gh pr list` | Check open PRs | Use in repo. |
| View PR in browser | `gh pr view PR_NUMBER --web` | Open PR quickly | Replace `PR_NUMBER`. |
| Check current PR status | `gh pr status` | On a branch | Shows PR context. |
| View Actions runs | `gh run list --limit 10` | Check CI | Good after PR push. |
| View workflow runs | `gh run list --workflow ci.yml --limit 5` | Check CI workflow | Workflow name may vary. |

---

## 9. Commit / PR Commands

Use Source Control UI if preferred. These are here when terminal is easier.

| Use | Command | When to use | Notes |
|---|---|---|---|
| Create branch | `git checkout -b create/example-branch-name` | New PR work | Branch should start with `create/`. |
| Stage specific file | `git add path\to\file.py` | Before commit | Prefer specific files over `git add .`. |
| Commit | `git commit -m "create short headline" -m "Longer description here."` | After validation | Commit headline should start with `create` for repo convention. |
| Push branch | `git push -u origin create/example-branch-name` | After commit | Uploads branch. |
| Open PR | `gh pr create --base main --head create/example-branch-name --title "create short title" --body "PR body here"` | After push | Usually agents handle this. |

---

## 10. Cleaning Local Junk Safely

| Use | Command | When to use | Notes |
|---|---|---|---|
| Check dirty files | `git status --short --branch` | Before cleanup | See what is dirty/untracked. |
| Remove Playwright MCP artifact | `Remove-Item -Recurse -Force .playwright-mcp` | If only `.playwright-mcp/` is untracked | Safe local artifact cleanup. |
| Remove Playwright output folder | `Remove-Item -Recurse -Force output\playwright` | Only if local QA output | Do not remove tracked files. |
| Remove PDF output folder | `Remove-Item -Recurse -Force output\pdf` | Only if generated local PDFs | Do not remove curated docs. |
| Clean ignored files only | `git clean -fdX` | Rare; removes ignored files | Be careful. |
| Preview untracked clean | `git clean -fdn` | Before deleting untracked files | Shows what would be deleted. |
| Remove untracked files | `git clean -fd` | Only when 100% sure | Dangerous if you have unsaved files. |

---

## 11. Python / Virtual Environment

| Use | Command | When to use | Notes |
|---|---|---|---|
| Check venv Python | `.\.venv\Scripts\python.exe --version` | Verify Python | Repo expects Python 3.11. |
| Activate venv | `.\.venv\Scripts\Activate.ps1` | Optional convenience | Direct `.venv\Scripts\python.exe` works without activation. |
| Install dependencies | `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | Initial setup/basic install | Prefer lock file if available. |
| Install locked dependencies | `.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt` | Reproducible setup | Best repo dependency install. |
| Upgrade pip | `.\.venv\Scripts\python.exe -m pip install --upgrade pip` | Occasionally | Do not mix with random dependency upgrades mid-PR. |
| List installed packages | `.\.venv\Scripts\python.exe -m pip list` | Inspect env | Useful for debugging. |
| Run pip-audit | `.\.venv\Scripts\pip-audit.exe -r requirements.lock.txt` | Dependency/security task | Only if installed. Do not install mid-audit unless scoped. |

---

## 12. Node / npm / Codex

| Use | Command | When to use | Notes |
|---|---|---|---|
| Check Node | `node --version` | Tooling check | Codex uses Node/npm if installed through npm. |
| Check npm | `npm --version` | Tooling check | Global package manager. |
| Check Codex | `codex --version` | Before/after update | Confirms Codex CLI. |
| Find Codex path | `where.exe codex` | If update weirdness happens | Shows installed path. |
| List global npm packages | `npm list -g --depth=0` | See global tools | Useful for Codex check. |
| Update Codex CLI | `npm install -g @openai/codex@latest` | Update Codex | Use outside active PR work. |

---

## 13. Winget / App Updates

| Use | Command | When to use | Notes |
|---|---|---|---|
| Check winget version | `winget --version` | Tooling check | Windows Package Manager. |
| List available updates | `winget upgrade` | See updates | Review before upgrading. |
| Update GitHub CLI | `winget upgrade --id GitHub.cli -e` | Keep GH CLI current | Safe generally. |
| Update GitHub Desktop | `winget upgrade --id GitHub.GitHubDesktop -e` | GUI updates | Safe generally. |
| Update VS Code | `winget upgrade --id Microsoft.VisualStudioCode -e` | Editor update | Usually safe. |
| Update Node LTS | `winget upgrade --id OpenJS.NodeJS.LTS -e` | Toolchain update | Do when no PR/agent running. |
| Update Python 3.11 | `winget upgrade --id Python.Python.3.11 -e` | Python patch update | Do carefully; verify venv after. |
| Update Build Tools | `winget upgrade --id Microsoft.VisualStudio.BuildTools -e` | Native build tooling | Do carefully; can take time. |
| Update everything | `winget upgrade --all` | Rare full update | Not recommended mid-project. |

---

## 14. Safe Update Routine

Run this when repo is clean and no agent task is running.

```powershell
# Check repo is clean first
cd C:\Repos\Bay-Delivery-Quote-Copilot
git status --short --branch

# Check tool versions
winget --version
gh --version
node --version
npm --version
codex --version

# Show Windows app/tool updates
winget upgrade

# Safer individual updates
winget upgrade --id GitHub.cli -e
winget upgrade --id GitHub.GitHubDesktop -e
winget upgrade --id Microsoft.VisualStudioCode -e

# Update Codex CLI if installed by npm
npm install -g @openai/codex@latest

# Confirm after updates
gh --version
codex --version
node --version
npm --version
```

---

## 15. Render / Deployment Checks

| Use | Command | When to use | Notes |
|---|---|---|---|
| Check Render CLI | `C:\Tools\render\render.exe --version` | If using Render CLI | Optional. |
| Live health | `Invoke-RestMethod https://bay-delivery-quote-copilot.onrender.com/health` | After deploy | Confirms live version/commit. |
| Production smoke | `gh workflow run production_live_safe_smoke.yml --ref main` | After important merge | Preferred Render/live check path. |

---

## 16. Search Commands

| Use | Command | When to use | Notes |
|---|---|---|---|
| Search text | `rg -n "search text" app static tests docs` | Find code/docs | Fast if ripgrep installed. |
| Search unsafe JS patterns | `rg -n "innerHTML|outerHTML|insertAdjacentHTML|eval\(|Function\(" static app tests` | Frontend/security audit | Should usually be empty or intentional. |
| Search secrets words | `rg -n "password|secret|token|SMTP|Bearer|Authorization" app static tests docs .github` | Security audit | Review results carefully. |
| Search TODOs | `rg -n "TODO|FIXME|SECURITY|HACK|temporary|unsafe|debug" app static tests scripts tools docs .github` | Audit cleanup | Useful before release. |
| Search route decorators | `rg -n "@app\.(get|post|put|delete|patch)\(" app/main.py` | Route audit | Shows API surface. |

---

## 17. Useful One-Shot Validation Blocks

### Standard local verification

```powershell
cd C:\Repos\Bay-Delivery-Quote-Copilot

git status --short --branch
git log --oneline -5

.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q
```

### Quote page validation

```powershell
cd C:\Repos\Bay-Delivery-Quote-Copilot

git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q tests\test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_quote_structured_intake_fields.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_launch_smoke_playwright.py
.\.venv\Scripts\python.exe -m pytest -q
```

### Security/admin hardening validation

```powershell
cd C:\Repos\Bay-Delivery-Quote-Copilot

git diff --check
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
.\.venv\Scripts\python.exe -m compileall app tools scripts tests
.\.venv\Scripts\python.exe -m pytest -q tests\test_env_and_dependencies.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_abuse_controls.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_static_assets.py
.\.venv\Scripts\python.exe -m pytest -q
```

---

## 18. What Not To Do Casually

| Do not casually run | Why |
|---|---|
| `git reset --hard` | Deletes local changes. Only use when explicitly approved. |
| `git clean -fd` | Deletes untracked files. Preview first with `git clean -fdn`. |
| `winget upgrade --all` | Can update Python/Node/Build Tools all at once. |
| `pip install --upgrade -r requirements.txt` | Can drift dependencies unexpectedly. |
| `npm update -g` | Can update global tools unpredictably. |
| `git add .` | Can accidentally stage junk/artifacts. Prefer specific files. |
| Live quote submits during QA | Can create production data. |
| Admin mutation tests on live Render | Can mutate production data. |
| Editing `app/quote_engine.py` casually | Pricing authority. High-risk. |
| Editing `docs/gpt` without export/parity | Can break grounding pack parity. |

---

## 19. Default “Is Everything Good?” Quick Check

```powershell
cd C:\Repos\Bay-Delivery-Quote-Copilot

git status --short --branch
.\.venv\Scripts\python.exe tools\check_version_parity.py
.\.venv\Scripts\python.exe tools\check_gpt_grounding_pack_parity.py
.\.venv\Scripts\python.exe -m pytest -q
```

If those pass and `git status` is clean, the repo is usually in good shape.

---

## 20. Current Bay Delivery Guardrails Reminder

| Guardrail | Reminder |
|---|---|
| Pricing authority | Only `app/quote_engine.py`. Do not create a second pricing engine. |
| Cash/EMT | Cash no HST. EMT/e-transfer +13% HST. |
| Admin | Internal operations only. |
| GPT | Internal-only, recommendation-first. |
| Customer quote flow | Public customer flow stays simple and safe. |
| Storage | SQLite is source of truth. |
| Calendar | Google Calendar is mirror/convenience only. |
| PR style | Narrow, reversible, auditable. |
| Verification | Parity checks + focused tests + protected diff. |
| Merge rule | Review first. Do not auto-merge. |
