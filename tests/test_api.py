import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import app
from database import Base, get_db


@pytest.fixture()
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        database = testing_session()
        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def register_user(client, username):
    response = client.post(
        "/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "SecureTestPassword123!",
        },
    )
    assert response.status_code == 201
    return response.json()


def login_user(client, username):
    response = client.post(
        "/login",
        json={
            "username": username,
            "password": "SecureTestPassword123!",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_registration_login_and_profile(client):
    user = register_user(client, "employee")

    assert user["role"] == "employee"
    assert user["is_active"] is True

    duplicate = client.post(
        "/users",
        json={
            "username": "employee",
            "email": "another@example.com",
            "password": "SecureTestPassword123!",
        },
    )
    assert duplicate.status_code == 400

    wrong_password = client.post(
        "/login",
        json={"username": "employee", "password": "WrongPassword123!"},
    )
    assert wrong_password.status_code == 401

    profile = client.get("/me", headers=login_user(client, "employee"))
    assert profile.status_code == 200
    assert profile.json()["username"] == "employee"


def test_invalid_and_missing_tokens_are_rejected(client):
    assert client.get("/me").status_code == 401

    invalid_token = client.get(
        "/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert invalid_token.status_code == 401
    assert invalid_token.json() == {"detail": "Invalid token"}


def test_ticket_validation_update_and_comments(client):
    register_user(client, "owner")
    headers = login_user(client, "owner")

    invalid_priority = client.post(
        "/tickets",
        headers=headers,
        json={
            "title": "Invalid priority",
            "description": "This ticket must not be saved.",
            "priority": "urgent",
        },
    )
    assert invalid_priority.status_code == 422

    created = client.post(
        "/tickets",
        headers=headers,
        json={
            "title": "Login page error",
            "description": "Users cannot sign in.",
            "priority": "high",
        },
    )
    assert created.status_code == 201
    ticket = created.json()

    rejected_null = client.patch(
        f"/tickets/{ticket['id']}",
        headers=headers,
        json={"title": None},
    )
    assert rejected_null.status_code == 422

    updated = client.patch(
        f"/tickets/{ticket['id']}",
        headers=headers,
        json={"status": "resolved"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "resolved"
    assert updated.json()["title"] == ticket["title"]

    comment = client.post(
        f"/tickets/{ticket['id']}/comments",
        headers=headers,
        json={"body": "The issue has been investigated."},
    )
    assert comment.status_code == 201

    comments = client.get(
        f"/tickets/{ticket['id']}/comments",
        headers=headers,
    )
    assert comments.status_code == 200
    assert [item["body"] for item in comments.json()] == [
        "The issue has been investigated."
    ]


def test_users_cannot_access_each_others_tickets(client):
    register_user(client, "owner")
    owner_headers = login_user(client, "owner")
    register_user(client, "outsider")
    outsider_headers = login_user(client, "outsider")

    created = client.post(
        "/tickets",
        headers=owner_headers,
        json={
            "title": "Private ticket",
            "description": "Only the owner should access this ticket.",
            "priority": "medium",
        },
    )
    ticket_id = created.json()["id"]

    assert client.get(
        f"/tickets/{ticket_id}",
        headers=outsider_headers,
    ).status_code == 403
    assert client.get(
        f"/tickets/{ticket_id}/comments",
        headers=outsider_headers,
    ).status_code == 403
    assert client.get("/tickets", headers=outsider_headers).json() == []

    assignment = client.patch(
        f"/tickets/{ticket_id}",
        headers=owner_headers,
        json={"assigned_to_id": 2},
    )
    assert assignment.status_code == 403

    deletion = client.delete(
        f"/tickets/{ticket_id}",
        headers=owner_headers,
    )
    assert deletion.status_code == 403
