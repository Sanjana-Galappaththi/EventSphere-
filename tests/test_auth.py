import uuid

def test_register_user(test_client):
    unique_email = f"user_{uuid.uuid4().hex[:6]}@test.com"
    response = test_client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "securepassword",
        "full_name": "New User"
    })
    assert response.status_code == 200
    assert response.json()["email"] == unique_email

def test_login_user(test_client):
    unique_email = f"login_{uuid.uuid4().hex[:6]}@test.com"
    # Register first
    test_client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "securepassword",
        "full_name": "Login User"
    })
    # Login
    response = test_client.post("/api/auth/login", data={
        "username": unique_email,
        "password": "securepassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()