import pytest


@pytest.fixture()
def seeded(client, user, token, auth_header):
    client.post("/aggregate", headers=auth_header(token))
    return client


def test_list_articles_is_public(client):
    response = client.get("/articles")
    assert response.status_code == 200
    assert response.json() == {"total": 0, "skip": 0, "limit": 20, "items": []}


def test_list_articles_paginates(seeded):
    response = seeded.get("/articles?limit=5&skip=0")
    body = response.json()
    assert body["total"] == 18
    assert len(body["items"]) == 5

    response = seeded.get("/articles?limit=5&skip=15")
    assert len(response.json()["items"]) == 3


def test_list_articles_search_by_keyword(seeded):
    response = seeded.get("/articles?q=battery")
    body = response.json()
    assert body["total"] == 1
    assert "Battery" in body["items"][0]["title"]


def test_list_articles_filter_by_category_slug(seeded):
    response = seeded.get("/articles?category=technology")
    body = response.json()
    assert body["total"] > 0
    assert all(item["category"]["slug"] == "technology" for item in body["items"])


def test_list_articles_filter_by_source_slug(seeded):
    response = seeded.get("/articles?source=the-guardian")
    body = response.json()
    assert body["total"] == 6
    assert all(item["source"]["name"] == "The Guardian" for item in body["items"])


def test_list_articles_filter_by_date_range(seeded):
    response = seeded.get("/articles?date_from=2026-10-18&date_to=2026-10-19")
    body = response.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert "2026-10-18" <= item["published_at"][:10] <= "2026-10-19"


def test_get_article_by_id(seeded):
    listing = seeded.get("/articles?limit=1").json()
    article_id = listing["items"][0]["id"]

    response = seeded.get(f"/articles/{article_id}")
    assert response.status_code == 200
    assert response.json()["id"] == article_id


def test_get_article_404(client):
    response = client.get("/articles/999")
    assert response.status_code == 404
