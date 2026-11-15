// We use the attendee token here for testing the UI. 
const DUMMY_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3OTQ3NDAyNjYsInN1YiI6IjIifQ.WPvtS6yI53s365ZZFcw-aAaPAzPL3Rf7nUNlMXsUP1A"; 

async function loadEvents() {
    try {
        const response = await fetch('/api/events/');
        const events = await response.json();
        
        const list = document.getElementById('event-list');
        list.innerHTML = '';
        
        if (events.length === 0) {
            list.innerHTML = '<p class="text-muted">No events found.</p>';
            return;
        }

        events.forEach(event => {
            const card = document.createElement('div');
            card.className = 'col-12 col-md-6';
            card.innerHTML = `
                <div class="card event-card p-3">
                    <h5 class="card-title">${event.title}</h5>
                    <p class="card-text text-muted mb-1">Status: ${event.status}</p>
                    <button class="btn btn-sm btn-success mt-2" onclick="openBookingModal(1)">Book Now</button>
                </div>
            `;
            list.appendChild(card);
        });
    } catch (err) {
        console.error("Error loading events:", err);
    }
}

function openBookingModal(categoryId) {
    // For simplicity, we assume categoryId = 1 for this demo
    document.getElementById('modal-category-id').value = categoryId;
    document.getElementById('booking-result').innerHTML = '';
    new bootstrap.Modal(document.getElementById('bookModal')).show();
}

async function confirmBooking() {
    const categoryId = document.getElementById('modal-category-id').value;
    const quantity = document.getElementById('modal-quantity').value;
    const resultDiv = document.getElementById('booking-result');

    try {
        const response = await fetch('/api/bookings/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${DUMMY_TOKEN}`
            },
            body: JSON.stringify({
                ticket_category_id: parseInt(categoryId),
                quantity: parseInt(quantity)
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            resultDiv.innerHTML = `<div class="alert alert-success">Booking Confirmed! Ref: ${data.payment_reference}</div>`;
        } else {
            resultDiv.innerHTML = `<div class="alert alert-danger">${data.detail}</div>`;
        }
    } catch (err) {
        resultDiv.innerHTML = `<div class="alert alert-danger">Error connecting to server.</div>`;
    }
}

// Load events on page start
document.addEventListener('DOMContentLoaded', loadEvents);