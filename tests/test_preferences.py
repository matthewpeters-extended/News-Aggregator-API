import pytest


@pytest.fixture()
def seeded_catalog(client, user, token, auth_header):
    """Runs aggregation so real source/category/author rows exist to
    reference from preference ids."""
    client.post("/aggregate", headers=auth_header(token))
    return client


def test_preferences_start_empty(client, user, token, auth_header):
    response = client.get("/preferences", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json() == {"sources": [], "categories": [], "authors": []}


def test_set_and_retrieve_preferences(seeded_catalog, token, auth_header):
    sources = seeded_catalog.get("/sources").json()
    categories = seeded_catalog.get("/categories").json()

    source_ids = [sources[0]["id"], sources[1]["id"]]
    category_ids = [categories[0]["id"]]

    response = seeded_catalog.put(
        "/preferences",
        json={"source_ids": source_ids, "category_ids": category_ids},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert {s["id"] for s in body["sources"]} == set(source_ids)
    assert {c["id"] for c in body["categories"]} == set(category_ids)
    assert body["authors"] == []

    # Persisted across requests.
    response = seeded_catalog.get("/preferences", headers=auth_header(token))
    assert {s["id"] for s in response.json()["sources"]} == set(source_ids)


def test_preferences_reject_unknown_ids(client, user, token, auth_header):
    response = client.put("/preferences", json={"source_ids": [9999]}, headers=auth_header(token))
    assert response.status_code == 400


def test_preferences_require_auth(client):
    response = client.get("/preferences")
    assert response.status_code == 401
