# EventSphere — Digital Ticketing & Venue Booking Platform

> **IT4123 Agent Based Computing Practical — ICA 02**  
> A mobile-friendly venue booking and digital ticketing platform where every booking decision is made by cooperating software agents.

---

## 🏛 Multi-Agent System (MAS) Overview

EventSphere is not a simple CRUD application. All core business rules and decisions are negotiated between **5 autonomous software agents** communicating solely through structured FIPA-style JSON messages over an asynchronous in-process MessageBus (with performatives: `REQUEST`, `AGREE`, `REFUSE`, `PROPOSE`, `INFORM`, `FAILURE`):

1. **`VenueAgent`**:
   - **Goal:** Keep every venue's calendar free of clashes.
   - **Decisions:** Enforces a mandatory **30-minute turnaround cleaning buffer** between all consecutive events/hires. Evaluates private hire capacity. Applies a **1.5× weekend/peak surcharge**. Counter-proposes alternative dates via `PROPOSE` when requests clash.
2. **`BookingAgent`**:
   - **Goal:** Sell tickets fairly without overselling.
   - **Decisions:** Enforces per-order purchase limits (max 6 tickets). Uses database row-locking (`with_for_update`) to prevent race conditions during concurrent checkouts. Calculates tiered refunds on cancellation (≥ 7 days = 100%, < 7 days = 50%), and handles full automatic refunds if an event is cancelled.
3. **`TicketAgent`**:
   - **Goal:** Admit each ticket exactly once.
   - **Decisions:** Generates unguessable 256-bit cryptographically secure QR codes. Enforces gate check-in time windows (-2 hrs to +1 hr). Detects duplicate scans, wrong-event passes, and flags suspicious repeated scans (anti-fraud screenshot sharing protection).
4. **`WaitlistAgent`**:
   - **Goal:** Pass freed seats to waiting customers.
   - **Decisions:** Manages FIFO waitlist queues. Issues **15-minute timed seat holds**. Proactively triggers background sweeps on a timer (via `APScheduler`) with zero user intervention to expire abandoned holds and cascade re-offers to the next customer in line.
5. **`NotificationAgent`**:
   - **Goal:** Tell the right person what affects them.
   - **Decisions:** Universal listener for broadcast agent `INFORM` and `PROPOSE` events, dispatching real-time notifications to users.

---

## 🚀 Quick Start Guide (How to Run Locally)

### 1. Prerequisites
- Python 3.11+ (Python 3.14 compatible)
- PowerShell or Terminal

### 2. Run the Application
Open a terminal in the project directory:
```powershell
cd C:\Users\User\.gemini\antigravity\scratch\eventsphere
& "C:\Users\User\AppData\Local\Python\bin\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser or mobile device at: **`http://localhost:8000`**

---

## 👤 Pre-Seeded Demo Accounts (Viva Examination)

All accounts come pre-configured with the default password: **`password123`**

| Role | Email Address | Password | Permissions & Features |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@eventsphere.edu` | `password123` | Full access: Create/edit venues & events, approve/reject escalated hire requests, view sales & MAS message audit log |
| **Gate Staff** | `staff@eventsphere.edu` | `password123` | Entrance QR scanner page with live phone camera feed + manual token fallback |
| **Attendee** | `attendee@eventsphere.edu` | `password123` | Browse events, purchase digital tickets, cancel bookings for refund, join waitlists, request private venue hire |

---

## 🧪 Running Pytest Tests (11 Comprehensive Tests)

Execute the complete test suite verifying overbooking prevention, double check-in prevention, and individual agent decisions:
```powershell
cd C:\Users\User\.gemini\antigravity\scratch\eventsphere
& "C:\Users\User\AppData\Local\Python\bin\python.exe" -m pytest tests -o cache_dir="./.pytest_cache" -v
```

### Covered Test Cases:
1. `test_user_registration_and_password_hashing`: Verifies bcrypt hash generation and authentication.
2. `test_role_access_enforcement`: Tests admin route protection against unauthorized attendees.
3. `test_venue_agent_turnaround_buffer_refusal`: Validates VenueAgent's 30-min buffer clash prevention.
4. `test_venue_agent_weekend_pricing_and_decision`: Checks 1.5× peak weekend rate calculation.
5. `test_booking_agent_refuses_excessive_quantity`: Tests max 6 tickets limit.
6. `test_booking_agent_prevents_overselling`: Concurrency test proving anti-overbooking under zero available capacity.
7. `test_ticket_agent_admits_once_and_rejects_double_scan`: Verifies second scan rejection with explicit reason.
8. `test_ticket_agent_rejects_wrong_event`: Rejects ticket scanned at a different event gate.
9. `test_waitlist_agent_proactive_sweep_and_reoffer`: Autonomous timer sweep expiring abandoned holds and re-offering to FIFO queue.
10. `test_notification_agent_reacts_and_creates_alert`: Verifies reactive event listening and DB alert persistence.
11. `test_message_bus_logs_traceable_conversation_id`: Verifies multi-agent FIPA audit trail on dashboard.

---

## ☁️ Deployment Instructions (Render / Cloud Host)

This project is ready for one-click deployment on Render, Railway, or Fly.io:

### Environment Variables
| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./eventsphere.db` | PostgreSQL in production (e.g. `postgresql://user:pass@host/db`) |
| `SECRET_KEY` | `eventsphere-secret-key-change-in-production-2024` | Cryptographic signing key for JWT tokens |

### Render `render.yaml` Configuration:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
