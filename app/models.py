from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    attendee = "attendee"

class EventStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    cancelled = "cancelled"

class BookingStatus(str, enum.Enum):
    confirmed = "confirmed"
    cancelled = "cancelled"

class HireStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    escalated = "escalated"
    rejected = "rejected"

class TicketStatus(str, enum.Enum):
    valid = "valid"
    used = "used"
    cancelled = "cancelled"

class WaitlistStatus(str, enum.Enum):
    waiting = "waiting"
    offered = "offered"
    confirmed = "confirmed"
    expired = "expired"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.attendee, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    bookings = relationship("Booking", back_populates="user")
    hire_requests = relationship("HireRequest", back_populates="user")
    waitlist_entries = relationship("WaitlistEntry", back_populates="user")
    notifications = relationship("Notification", back_populates="user")

class Venue(Base):
    __tablename__ = "venues"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    description = Column(Text)
    image_url = Column(String)
    hourly_hire_rate = Column(Float, nullable=False)
    is_hireable = Column(Boolean, default=True)
    events = relationship("Event", back_populates="venue")
    hire_requests = relationship("HireRequest", back_populates="venue")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    description = Column(Text)
    status = Column(SAEnum(EventStatus), default=EventStatus.draft)
    created_at = Column(DateTime, default=datetime.utcnow)
    venue = relationship("Venue", back_populates="events")
    ticket_categories = relationship("TicketCategory", back_populates="event", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="event")

class TicketCategory(Base):
    __tablename__ = "ticket_categories"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    sold = Column(Integer, default=0)
    event = relationship("Event", back_populates="ticket_categories")
    bookings = relationship("Booking", back_populates="ticket_category")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    ticket_category_id = Column(Integer, ForeignKey("ticket_categories.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    payment_reference = Column(String, nullable=False)
    status = Column(SAEnum(BookingStatus), default=BookingStatus.confirmed)
    created_at = Column(DateTime, default=datetime.utcnow)
    cancelled_at = Column(DateTime, nullable=True)
    refund_amount = Column(Float, nullable=True)
    user = relationship("User", back_populates="bookings")
    event = relationship("Event", back_populates="bookings")
    ticket_category = relationship("TicketCategory", back_populates="bookings")
    tickets = relationship("Ticket", back_populates="booking", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    qr_code = Column(String, unique=True, nullable=False, index=True)
    status = Column(SAEnum(TicketStatus), default=TicketStatus.valid)
    checked_in_at = Column(DateTime, nullable=True)
    scan_count = Column(Integer, default=0)
    booking = relationship("Booking", back_populates="tickets")

class HireRequest(Base):
    __tablename__ = "hire_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    purpose = Column(String, nullable=False)
    guest_count = Column(Integer, nullable=False)
    status = Column(SAEnum(HireStatus), default=HireStatus.pending)
    total_price = Column(Float, nullable=True)
    admin_note = Column(Text, nullable=True)
    alternatives = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="hire_requests")
    venue = relationship("Venue", back_populates="hire_requests")

class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticket_category_id = Column(Integer, ForeignKey("ticket_categories.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(SAEnum(WaitlistStatus), default=WaitlistStatus.waiting)
    offered_at = Column(DateTime, nullable=True)
    offer_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="waitlist_entries")
    ticket_category = relationship("TicketCategory")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="notifications")

class AgentMessage(Base):
    __tablename__ = "agent_messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, nullable=False, index=True)
    sender = Column(String, nullable=False)
    receiver = Column(String, nullable=False)
    performative = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
