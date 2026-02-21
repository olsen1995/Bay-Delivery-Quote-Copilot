# Bay Delivery – Quote Copilot

Local quote/estimate tool for Bay Delivery (North Bay, Ontario).  
This project provides a simple web UI plus a FastAPI backend to generate customer-safe estimates.

## What it does

- Customer-facing quote form (served at `/`)
- API endpoint to calculate quotes: `POST /quote/calculate`
- Stores each quote request + internal breakdown for admin review (SQLite)

## Core pricing rules (current)

### Tax policy

- **Cash:** no HST
- **EMT / e-transfer:** add **13% HST** to the total

### Service types

- **Junk Removal / Haul Away** (Junk + Dump are treated as the same service)
  - The estimate total may include disposal/dump handling internally.
  - **Dump/disposal is NOT itemized** on the customer-facing output.
  - **Mattress/box spring**: allowed as a special note (not itemized line items).

- **Scrap Pickup**
  - **Curbside/outside:** $0 (picked up next time we’re in the area)
  - **Inside removal:** $30 flat
  - Scrap pickup bypasses labour/travel/disposal logic (flat-rate only).

Other service types may exist for future expansion (moving, delivery, demolition), but the primary enforced rules above are the current operational defaults.

## Running locally (Windows PowerShell)

### Create/activate venv (recommended: Python 3.11)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
