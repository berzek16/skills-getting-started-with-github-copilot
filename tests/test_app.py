import asyncio
from copy import deepcopy

import httpx
import pytest

from src import app


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(app.activities)
    yield
    app.activities.clear()
    app.activities.update(original_activities)


async def request(method, url, **kwargs):
    transport = httpx.ASGITransport(app=app.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, url, **kwargs)


def test_root_redirects_to_static_index():
    # Arrange
    url = "/"

    # Act
    response = asyncio.run(request("GET", url, follow_redirects=False))

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_catalog():
    # Arrange
    expected_activities = {
        "Chess Club",
        "Programming Class",
        "Gym Class",
        "Soccer Club",
        "Track and Field",
        "Art Studio",
        "Drama Club",
        "Debate Team",
        "Robotics Club",
    }

    # Act
    response = asyncio.run(request("GET", "/activities"))

    # Assert
    assert response.status_code == 200
    assert set(response.json()) == expected_activities
    assert all(
        {"description", "schedule", "max_participants", "participants"}
        <= set(details)
        for details in response.json().values()
    )


def test_signup_adds_participant():
    # Arrange
    activity_name = "Soccer Club"
    email = "student@mergington.edu"

    # Act
    response = asyncio.run(
        request(
            "POST",
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Signed up {email} for {activity_name}"
    }
    assert email in app.activities[activity_name]["participants"]


def test_signup_rejects_unknown_activity():
    # Arrange
    activity_name = "Unknown Activity"
    email = "student@mergington.edu"

    # Act
    response = asyncio.run(
        request(
            "POST",
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_rejects_duplicate_participant():
    # Arrange
    activity_name = "Chess Club"
    email = app.activities[activity_name]["participants"][0]

    # Act
    response = asyncio.run(
        request(
            "POST",
            f"/activities/{activity_name}/signup",
            params={"email": email},
        )
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }
    assert app.activities[activity_name]["participants"].count(email) == 1


def test_unregister_removes_participant():
    # Arrange
    activity_name = "Chess Club"
    email = app.activities[activity_name]["participants"][0]

    # Act
    response = asyncio.run(
        request(
            "DELETE",
            f"/activities/{activity_name}/participants",
            params={"email": email},
        )
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Unregistered {email} from {activity_name}"
    }
    assert email not in app.activities[activity_name]["participants"]


def test_unregister_rejects_unknown_activity():
    # Arrange
    activity_name = "Unknown Activity"
    email = "student@mergington.edu"

    # Act
    response = asyncio.run(
        request(
            "DELETE",
            f"/activities/{activity_name}/participants",
            params={"email": email},
        )
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_rejects_missing_participant():
    # Arrange
    activity_name = "Soccer Club"
    email = "not-registered@mergington.edu"

    # Act
    response = asyncio.run(
        request(
            "DELETE",
            f"/activities/{activity_name}/participants",
            params={"email": email},
        )
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Student is not signed up for this activity"
    }
