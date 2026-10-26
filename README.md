# News Aggregator API

A REST API that pulls articles from several news sources into one local catalog, with
auth, search and filtering, and per user preferences on top.

Stack: **FastAPI** + **SQLAlchemy** + **SQLite**, JWT auth via `python-jose`, password hashing
via `passlib`/`bcrypt`, rate limiting via `slowapi`, scheduled background jobs via
`APScheduler`.

It runs entirely on bundled mock data by default, with no API keys, no signup, and no network
calls. See [Mock mode versus live mode](#mock-mode-versus-live-mode) below for how to point it
at the real NewsAPI/Guardian/NYTimes APIs later.

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/seed_demo_data.py    # creates demo@news-aggregator.dev / demo12345, fetches mock articles

uvicorn app.main:app --reload --reload-dir app
```

Interactive docs (Swagger UI) at `http://127.0.0.1:8000/docs` once it is running.

Run the test suite with:

```bash
pytest
```

## The main components

The app is split by *what each piece knows about*, not by HTTP verb. The goal is that each
file has one job and does not need to understand how the others work internally.

**`app/models.py` is the data layer.** `User`, `Source`, `Category`, `Author`, and `Article`
hold the catalog; `ApiToken` and `PasswordResetToken` hold auth state. Preferences
(`user_preferred_sources`/`_categories`/`_authors`) are proper many to many association tables,
not a JSON blob, so "give me all articles matching this user's preferred sources" is a normal
join, not application level filtering. `Article` has a `UniqueConstraint` on
`(source_id, external_id)` and a unique `url`, which is what makes reaggregating safe to run
on a schedule: the same article fetched twice just gets skipped, not duplicated.

**`app/providers/` holds one class per external news API, behind a shared interface.**
`base.py` defines `NewsProvider.fetch(query, category) -> list[NormalizedArticle]`, the only
contract the rest of the app depends on. `newsapi.py`, `guardian.py`, and `nytimes.py` each
parse *that specific API's* real response shape (NewsAPI's `{"articles": [...]}` with a nested
`source` object; the Guardian's `{"response": {"results": [...]}}` with a `fields` sub object;
NYTimes's `{"response": {"docs": [...]}}` with a `headline.main` and `byline.original`) into the
same `NormalizedArticle` shape. Each provider's `fetch()` branches on `settings.app_mode`: in
`mock` mode it loads a bundled JSON fixture from `fixtures/`; in `live` mode it calls the real
endpoint with `httpx`, using the matching API key from `.env`. The parsing code below that
branch is identical either way, which is the whole point of the abstraction. Swapping mock for
live is a config change, not a rewrite.

**`app/aggregator.py` turns provider output into database rows.** `run_aggregation()` calls
every provider, then for each returned article: finds or creates its `Source`/`Category`/
`Author` by slug (not exact name match, since different feeds capitalize the same category
differently, for example NewsAPI's `"technology"` versus the Guardian's `"Technology"`), then
inserts the `Article` inside a SAVEPOINT (`db.begin_nested()`) so one duplicate or bad row only
unwinds itself, not the whole run's progress so far. Returns a per provider tally
(fetched/created/skipped/error) so a caller can see exactly what happened without reading logs.

**`app/scheduler.py` is the "aggregator" part of an aggregator API.** An `APScheduler`
`BackgroundScheduler` reruns `run_aggregation()` on an interval
(`AGGREGATION_INTERVAL_MINUTES`, default 30), started in `main.py`'s FastAPI `lifespan` and shut
down cleanly on exit. `POST /aggregate` triggers the same function on demand, for anyone
authenticated.

**`app/security.py` is crypto, with no web framework in it.** Three unrelated jobs live here on
purpose: hashing and verifying account passwords (`passlib`/`bcrypt`, deliberately slow, which
resists brute forcing a weak password); encoding and decoding JWTs (`python-jose`); and hashing
API and reset tokens (plain `sha256`, deliberately fast, since these are already random and
high entropy, and a fast deterministic hash lets `deps.py` look one up directly by its hash
instead of comparing against every row). Using `bcrypt` for all of them would be the wrong tool
for the token case.

**`app/deps.py` is one dependency, two kinds of credential.** `get_current_user` accepts
`Authorization: Bearer <value>` and tries it as a JWT first (`/login` tokens, short lived); if
that fails to decode, it falls back to looking the value up as a hashed `ApiToken` (`/tokens`,
long lived, for scripts and cron jobs rather than a logged in session). Every protected route
just depends on this one function and does not care which kind of credential was used.

**`app/routers/` holds the actual HTTP endpoints, one file per resource:**

<table>
<tr><th>File</th><th>Routes</th><th>Notes</th></tr>
<tr><td><code>auth.py</code></td><td><code>POST /register</code>, <code>POST /login</code>, <code>POST /password-reset/request</code>, <code>POST /password-reset/confirm</code></td><td>Reset tokens are single use and thirty minutes lived; the request endpoint never reveals whether an email is actually registered</td></tr>
<tr><td><code>tokens.py</code></td><td><code>POST /tokens</code>, <code>GET /tokens</code>, <code>DELETE /tokens/{id}</code></td><td>The raw token is returned once, at creation, and never again, the same pattern as a GitHub PAT</td></tr>
<tr><td><code>articles.py</code></td><td><code>GET /articles</code>, <code>GET /articles/{id}</code></td><td>Public; supports <code>q</code>, <code>category</code>, <code>source</code>, <code>date_from</code>/<code>date_to</code>, <code>skip</code>/<code>limit</code></td></tr>
<tr><td><code>catalog.py</code></td><td><code>GET /sources</code>, <code>GET /categories</code>, <code>GET /authors</code></td><td>Public; lets a client populate filter dropdowns and preference pickers</td></tr>
<tr><td><code>preferences.py</code></td><td><code>GET /preferences</code>, <code>PUT /preferences</code></td><td>Authenticated; <code>PUT</code> validates every id exists before saving any of them</td></tr>
<tr><td><code>aggregation.py</code></td><td><code>POST /aggregate</code></td><td>Authenticated; manual trigger alongside the scheduled job</td></tr>
</table>

**`app/limiter.py` plus the `slowapi` wiring in `main.py` handle abuse prevention.** A
`Limiter` keyed by client IP, with a global default (100 requests per minute) and stricter
limits specifically on `/login` and `/password-reset/request` (5 per minute each) since those
are the endpoints someone would actually try to brute force or spam.

**`app/main.py` assembles all of it.** Creates the tables on startup, starts and stops the
scheduler via `lifespan`, registers the rate limiter, and mounts each router. Nothing business
specific lives here; it is purely wiring.

**`scripts/seed_demo_data.py`** is a one time bootstrap: creates a demo login and runs
aggregation once, so there is a user and articles to explore immediately after the server
starts.

**`tests/`** has 28 pytest feature tests covering auth, token issuance and revocation, article
search, filtering, pagination, preferences, and aggregation (including that rerunning it is
idempotent), against an in memory SQLite database so they never touch `news.db`. The rate
limiter is disabled in this environment only, since the test client's requests all appear to
come from the same IP and would otherwise trip the login and reset limits for reasons unrelated
to what is actually being tested.

## Mock mode versus live mode

`APP_MODE` (in `.env`, see `.env.example`) controls everything:

* **mock** (the default): providers read from `app/providers/fixtures/*.json`, which mirror
  each real API's actual response shape with invented sample articles. Nothing leaves your
  machine.
* **live**: providers call the real NewsAPI/Guardian/NYTimes endpoints using
  `NEWSAPI_KEY`/`GUARDIAN_KEY`/`NYTIMES_KEY` from `.env`. All three offer free API keys via a
  short signup; none require a credit card.

Every other file in the app, including the aggregator, the routers, and the tests, is identical
in either mode, because they only ever see a `NormalizedArticle`, never a raw API response.

## Decisions worth knowing about

* **Categories and authors are deduplicated by slug or lowercased name, not exact string
  match.** The same category shows up as `"technology"` from NewsAPI and `"Technology"` from
  the Guardian; treating those as the same row (first spelling seen wins the display name)
  avoids silently fragmenting the catalog into near duplicate categories.
* **Article inserts happen inside a SAVEPOINT per article**, not the whole aggregation run in
  one transaction. A naive `try/except IntegrityError: db.rollback()` around each insert would
  roll back the *entire* session, including every source, category, and author already created
  earlier in the same run, not just the one bad article.
* **The JWT signing secret and news API keys come from `.env`** (via `pydantic-settings`),
  defaulting to a dev placeholder for the JWT secret so the app still runs with zero
  configuration in mock mode.
* **Password reset tokens are hashed with `sha256`, account passwords with `bcrypt`.** They are
  solving different problems: a password is low entropy and user chosen, so it needs a slow,
  salted hash to resist brute forcing. A reset or API token is already a random 256 bit value,
  so hashing it slowly buys nothing, and a fast deterministic hash is what makes "look this
  token up directly" possible instead of comparing against every row in the table.
