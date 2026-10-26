def test_register_and_login(client):
    response = client.post(
        "/register", json={"name": "Nina", "email": "nina@test-suite.dev", "password": "nina12345"}
    )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "nina@test-suite.dev"

    response = client.post("/login", json={"email": "nina@test-suite.dev", "password": "nina12345"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_register_rejects_duplicate_email(client, user):
    response = client.post(
        "/register", json={"name": "Someone Else", "email": "nina@test-suite.dev", "password": "whatever123"}
    )
    assert response.status_code == 400


def test_login_rejects_wrong_password(client, user):
    response = client.post("/login", json={"email": "nina@test-suite.dev", "password": "wrong-password"})
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, user, token, auth_header):
    response = client.get("/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["email"] == "nina@test-suite.dev"


def test_password_reset_flow(client, user):
    response = client.post("/password-reset/request", json={"email": "nina@test-suite.dev"})
    assert response.status_code == 200
    reset_token = response.json()["reset_token"]
    assert reset_token

    response = client.post(
        "/password-reset/confirm", json={"token": reset_token, "new_password": "brand-new-pass"}
    )
    assert response.status_code == 204

    # Old password no longer works, new one does.
    assert client.post("/login", json={"email": "nina@test-suite.dev", "password": "nina12345"}).status_code == 401
    assert client.post("/login", json={"email": "nina@test-suite.dev", "password": "brand-new-pass"}).status_code == 200


def test_password_reset_token_is_single_use(client, user):
    reset_token = client.post("/password-reset/request", json={"email": "nina@test-suite.dev"}).json()["reset_token"]

    first = client.post("/password-reset/confirm", json={"token": reset_token, "new_password": "first-pass-1"})
    assert first.status_code == 204

    second = client.post("/password-reset/confirm", json={"token": reset_token, "new_password": "second-pass-1"})
    assert second.status_code == 400


def test_password_reset_for_unknown_email_does_not_leak(client):
    response = client.post("/password-reset/request", json={"email": "nobody@test-suite.dev"})
    assert response.status_code == 200
    assert response.json()["reset_token"] == ""
