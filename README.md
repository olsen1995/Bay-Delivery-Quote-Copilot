# Life OS — Practical Co-Pilot

Life OS — Practical Co-Pilot is a grounded “Life Operating System” for real-world decisions, problem-solving, and daily clarity. It routes user requests into specialized modes (Day Planner, Life Coach, Fix-It, Device Optimization, Kitchen, Laundry, Cleaning, Skincare, RC Car, Daily Horoscope, Decision Check). It prioritizes least-risk and reversible steps, enforces a mandatory Upload Analysis Gate for any uploaded file/image/log/CSV/script/screenshot before giving advice, and provides Stop/Check guidance for high-risk domains (health, vehicles, electricity, chemicals, food safety, significant money). For high-stakes or time-sensitive claims, it uses web browsing with citations; if not browsing, it avoids naming authorities or standards.

## What this repository is
This repo is the source of truth for the Custom GPT Instructions, supporting Knowledge content, tests, and changelog that keep the assistant consistent, safe, and up-to-date.

## Folder structure
- `/instructions` — Custom GPT instruction set
- `/knowledge` — Mode playbooks and reference materials
- `/tests` — Test suite for behavioral and safety checks
- `CHANGELOG.md` — Versioned change history

## Privacy note
This is a personal/private repository. Do not share contents publicly or include any personal data, addresses, phone numbers, or secrets in files or commits.

## Versioning
Releases are tagged (e.g., `v6.0.0`) to track changes over time.

## Update workflow
1. Edit instructions/knowledge/tests as needed.
2. Commit the changes.
3. Upload updated content to the Custom GPT.
   GitHub does not automatically sync to the Custom GPT; upload files manually after changes.
4. Run tests to validate behavior.
5. Update `CHANGELOG.md` and tag a release when ready.
