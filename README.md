# 🚛 Bay Delivery Quote Copilot

Backend system for generating customer job estimates, managing quote approvals, and tracking Bay Delivery operations.

Deployed on Render:
https://bay-delivery-quote-copilot.onrender.com

---

## 🧠 What This System Does

- Generate customer job estimates
- Track submitted quote requests
- Admin review & approval workflow
- Job tracking system
- Cash vs EMT pricing logic
- Mattress & box spring disposal logic
- Simple database storage (SQLite)

---

## 📦 Core Features

### 🔹 Customer Side
- Submit quote requests
- View estimate totals
- Accept quotes
- Request job date (minimum next day)

### 🔹 Admin Side
- Secure admin login
- Review quote submissions
- Approve or reject jobs
- Convert approved quotes into active jobs
- Track job status

---

## 💰 Pricing Rules

- Minimum job: $50
- EMT payments: +13% HST
- Mattress disposal: $50 each
- Box spring disposal: $50 each
- Labour + disposal fees shown separately
- Final price subject to in-person review

---

## 🛠️ Tech Stack

- FastAPI
- SQLite
- Uvicorn
- Render (Deployment)
- Pydantic
- Python 3.11

---

## 🚀 Running Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit:
http://127.0.0.1:8000/health

---

## 🌐 Deployment (Render)

Build Command:
```
pip install -r requirements.txt
```

Start Command:
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 🔐 Environment Variables

Required:

```
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password
```

Optional (future):
```
GOOGLE_MAPS_API_KEY=your_key
BAYDELIVERY_BASE_ADDRESS=your_base_address
```

---

## 🗺️ Roadmap

- Frontend customer quote form
- Admin dashboard UI
- Google Calendar auto-booking
- SMS notifications
- Distance auto-calculation (Google Maps API)
- Multi-trip pricing logic
- Analytics dashboard

---

## 📍 Service Area

North Bay, Ontario  
Surrounding areas upon request

---

Built for real-world operations.
