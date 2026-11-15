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

   
## dashboard

<img width="862" height="313" alt="dashboard" src="https://github.com/user-attachments/assets/fc38cd9c-8ec3-41a7-a4e8-6c87b0762a58" />

<img width="1333" height="599" alt="dshboard1" src="https://github.com/user-attachments/assets/07ac111c-bdb9-4697-a1cf-01208d9a3bee" />

## Scanner

<img width="1333" height="599" alt="dshboard1" src="https://github.com/user-attachments/assets/941cc4f3-3131-40be-840b-b630c6fd3619" />
<img width="870" height="399" alt="scanner" src="https://github.com/user-attachments/assets/ff5f2fef-38dc-40de-b246-68d9c6b67997" />


<img width="1421" height="562" alt="scanner1" src="https://github.com/user-attachments/assets/91a16611-e850-4541-8f74-2d03011d9f05" />


##login and register

<img width="575" height="270" alt="register" src="https://github.com/user-attachments/assets/a96db470-d3d4-44cb-a983-e246cbf84fd5" />

<img width="572" height="352" alt="login" src="https://github.com/user-attachments/assets/63a0a879-77de-4bf9-94dc-d162c725aa3d" />

## authorization

<img width="287" height="260" alt="authrization" src="https://github.com/user-attachments/assets/7d7e7ecf-bbf4-4fd8-9bb4-fdfa9c123605" />


##API

<img width="857" height="450" alt="docs1" src="https://github.com/user-attachments/assets/354de215-63fb-4f01-8b91-63ddfe98f1c6" />

<img width="615" height="437" alt="docs2" src="https://github.com/user-attachments/assets/08806506-5886-48d5-8b34-cba2eede43f4" />

## booking event

<img width="423" height="230" alt="booking" src="https://github.com/user-attachments/assets/41769565-d743-48e8-bdbd-ad9d2e2d182e" />

##testing

<img width="770" height="122" alt="Screenshot 2026-11-15 174245" src="https://github.com/user-attachments/assets/b0003f65-1354-4656-8c6e-f0e2cf354909" />


## Testing
Run the test suite:
```bash
pytest -v











