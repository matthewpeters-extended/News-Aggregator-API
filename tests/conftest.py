import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.limiter import limiter
from app.main import app
from app.models import User
from app.security import hash_password

# The /login and /password-reset/request rate limits are for real-world abuse
# prevention; they'd otherwise fire mid-suite since slowapi keys by client IP
# and the test client always looks like the same IP.
limiter.enabled = False

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _make_user(db_session, name, email, password):
    user = User(name=name, email=email, password=hash_password(password))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client, email, password):
    response = client.post("/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def user(db_session):
    return _make_user(db_session, "Nina", "nina@test-suite.dev", "nina12345")


@pytest.fixture()
def other_user(db_session):
    return _make_user(db_session, "Omar", "omar@test-suite.dev", "omar12345")


@pytest.fixture()
def token(client, user):
    return _login(client, "nina@test-suite.dev", "nina12345")


@pytest.fixture()
def other_token(client, other_user):
    return _login(client, "omar@test-suite.dev", "omar12345")


@pytest.fixture()
def auth_header():
    def _header(token):
        return {"Authorization": f"Bearer {token}"}

    return _header
