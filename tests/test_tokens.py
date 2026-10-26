def test_create_and_use_api_token(client, user, token, auth_header):
    response = client.post("/tokens", json={"name": "my script"}, headers=auth_header(token))
    assert response.status_code == 201, response.text
    api_token = response.json()["token"]

    # The API token works on a protected endpoint exactly like a JWT.
    response = client.get("/me", headers=auth_header(api_token))
    assert response.status_code == 200
    assert response.json()["email"] == "nina@test-suite.dev"


def test_list_tokens_excludes_raw_value(client, user, token, auth_header):
    client.post("/tokens", json={"name": "my script"}, headers=auth_header(token))

    response = client.get("/tokens", headers=auth_header(token))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "token" not in body[0]
    assert body[0]["name"] == "my script"


def test_revoked_token_no_longer_works(client, user, token, auth_header):
    created = client.post("/tokens", json={"name": "my script"}, headers=auth_header(token)).json()
    api_token = created["token"]

    revoke = client.delete(f"/tokens/{created['id']}", headers=auth_header(token))
    assert revoke.status_code == 204

    response = client.get("/me", headers=auth_header(api_token))
    assert response.status_code == 401


def test_cannot_revoke_another_users_token(client, user, token, other_user, other_token, auth_header):
    created = client.post("/tokens", json={"name": "my script"}, headers=auth_header(token)).json()

    response = client.delete(f"/tokens/{created['id']}", headers=auth_header(other_token))
    assert response.status_code == 404
