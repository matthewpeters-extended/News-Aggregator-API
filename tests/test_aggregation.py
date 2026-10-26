def test_aggregate_requires_auth(client):
    response = client.post("/aggregate")
    assert response.status_code == 401


def test_aggregate_pulls_from_all_mock_providers(client, user, token, auth_header):
    response = client.post("/aggregate", headers=auth_header(token))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["mode"] == "mock"
    providers = {r["provider"] for r in body["results"]}
    assert providers == {"newsapi", "guardian", "nytimes"}
    assert all(r["error"] is None for r in body["results"])
    assert sum(r["created"] for r in body["results"]) == 18  # 6 fixture articles x 3 providers

    articles = client.get("/articles?limit=100").json()
    assert articles["total"] == 18


def test_aggregate_is_idempotent(client, user, token, auth_header):
    client.post("/aggregate", headers=auth_header(token))
    second = client.post("/aggregate", headers=auth_header(token)).json()

    assert sum(r["created"] for r in second["results"]) == 0
    assert sum(r["skipped_duplicates"] for r in second["results"]) == 18

    articles = client.get("/articles?limit=100").json()
    assert articles["total"] == 18


def test_aggregate_populates_catalog(client, user, token, auth_header):
    client.post("/aggregate", headers=auth_header(token))

    sources = {s["name"] for s in client.get("/sources").json()}
    assert sources == {"TechCrunch", "BBC News", "Reuters", "The Guardian", "The New York Times"}

    categories = {c["name"] for c in client.get("/categories").json()}
    assert "technology" in categories or "Technology" in categories
