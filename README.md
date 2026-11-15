# EventSphere - Multi-Agent Venue Booking System

EventSphere is a mobile-friendly venue booking and digital ticketing platform built with FastAPI. Every booking decision is handled by cooperating software agents communicating via JSON messages through a custom Message Bus.

## Architecture & Agents
- **VenueAgent**: Checks for time clashes (2-hour turnaround buffer) and proposes alternatives for private hires.
- **BookingAgent**: Prevents overbooking using SQLAlchemy `with_for_update()` row locking. Refuses bookings > 6 tickets.
- **TicketAgent**: Generates secure UUID QR codes and prevents double scanning.
- **WaitlistAgent**: Holds released seats for 10 minutes.
- **NotificationAgent**: Listens for INFORM broadcasts (e.g., "Booking confirmed!").

## Local Setup
1. Create a virtual environment: `python -m venv venv`
2. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
3. Install dependencies: `pip install -r requirements.txt`
4. Create `.env` file with `DATABASE_URL` and `SECRET_KEY`.
5. Create tables: `python -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)"`
6. Run the app: `uvicorn app.main:app --reload`

   
<img width="695" height="323" alt="login" src="https://github.com/user-attachments/assets/eaaabc90-4262-4278-a746-be228d44c99b" />

<img width="943" height="449" alt="reg" src="https://github.com/user-attachments/assets/612b8a12-6e18-4785-8bf5-f1291f8850a9" />

<img width="918" height="471" alt="dashboard" src="https://github.com/user-attachments/assets/ad8c8eb5-f0a0-4cf2-a544-cf76187989e7" />

<img width="922" height="460" alt="addvenue" src="https://github.com/user-attachments/assets/e8b7d9a8-edbc-4e8d-9765-49ebca33f3ad" />

<img width="939" height="464" alt="1" src="https://github.com/user-attachments/assets/c4094e1f-503e-4fbd-a172-7e6657fbb5ef" />


<img width="912" height="444" alt="hire venue" src="https://github.com/user-attachments/assets/43e31ae7-1621-4341-bc1f-c7ea2b7ac54c" />


<img width="920" height="365" alt="scanner" src="https://github.com/user-attachments/assets/ecd20b5d-58f4-4b6d-95b7-5537741d79a2" />

<img width="941" height="465" alt="logs" src="https://github.com/user-attachments/assets/7f533dd3-b3be-4585-8052-9ba9138dd7ff" />

<img width="926" height="455" alt="docs" src="https://github.com/user-attachments/assets/60e3b1ad-a6df-41bb-8c65-7b6a00c2f811" />

<img width="1421" height="562" alt="scanner1" src="https://github.com/user-attachments/assets/3891bee7-4793-4348-90f2-7c3c6b8007bd" />







## Testing

<img width="823" height="234" alt="test" src="https://github.com/user-attachments/assets/8d47c08f-2d0a-4ccf-855f-d23505ea44f5" />

Run the test suite:
```bash
pytest -v











