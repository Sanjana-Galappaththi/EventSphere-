function updateNav() {
    const token = localStorage.getItem('access_token');
    const nav = document.getElementById('nav-links');
    if (token) {
        nav.innerHTML = `
            <a href="/dashboard" class="btn btn-outline-info btn-sm me-2">Dashboard</a>
            <a href="/scanner" class="btn btn-outline-light btn-sm me-2">Scanner</a>
            <button onclick="logout()" class="btn btn-danger btn-sm">Logout</button>
        `;
    } else {
        nav.innerHTML = `
            <a href="/login" class="btn btn-primary btn-sm me-2">Login / Register</a>
            <a href="/scanner" class="btn btn-outline-light btn-sm">Scanner</a>
        `;
    }
}

function logout() {
    localStorage.removeItem('access_token');
    window.location.reload();
}

async function loadEvents() {
    const res = await fetch('/api/events/');
    const events = await res.json();
    const list = document.getElementById('event-list');
    list.innerHTML = '';
    if (events.length === 0) {
        list.innerHTML = '<p class="text-muted">No events found.</p>';
        return;
    }
    events.forEach(event => {
        const card = document.createElement('div');
        card.className = 'col-12 col-md-6 mb-3';
        card.innerHTML = `
            <div class="card p-3">
                <h5>${event.title}</h5>
                <p class="text-muted mb-1">Status: ${event.status}</p>
                <button class="btn btn-sm btn-success mt-2" onclick="openBookingModal(${event.id})">Book Now</button>
            </div>
        `;
        list.appendChild(card);
    });
}

function openBookingModal(categoryId) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        alert("Please login first to book tickets.");
        window.location.href = '/login';
        return;
    }
    document.getElementById('modal-category-id').value = categoryId;
    document.getElementById('booking-result').innerHTML = '';
    new bootstrap.Modal(document.getElementById('bookModal')).show();
}

async function confirmBooking() {
    const categoryId = document.getElementById('modal-category-id').value;
    const quantity = document.getElementById('modal-quantity').value;
    const resultDiv = document.getElementById('booking-result');
    const token = localStorage.getItem('access_token');

    const res = await fetch('/api/bookings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ ticket_category_id: parseInt(categoryId), quantity: parseInt(quantity) })
    });
    const data = await res.json();
    if (res.ok) {
        resultDiv.innerHTML = `<div class="alert alert-success">Booking Confirmed! Ref: ${data.payment_reference}</div>`;
    } else {
        resultDiv.innerHTML = `<div class="alert alert-danger">${data.detail}</div>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateNav();
    loadEvents();
});