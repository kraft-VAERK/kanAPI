"""# test_case.py."""

import os
import sys

from fastapi.testclient import TestClient

from api.main import app

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Add a middleware module to sys.modules to satisfy the import in main.py
import sys
import types

middleware_module = types.ModuleType("middleware")
middleware_module.logging = types.ModuleType("middleware.logging")


# Create a dummy log_requests function
async def dummy_log_requests(request: any, call_next: any) -> any:
    """Act as a dummy logging middleware that does nothing."""
    return await call_next(request)


middleware_module.logging.log_requests = dummy_log_requests
sys.modules["middleware"] = middleware_module
sys.modules["middleware.logging"] = middleware_module.logging

# Now import from api


# Create a test client
client = TestClient(app)


# Rest of your test code remains the same
def test_health_endpoint() -> None:
    """Test the health endpoint to ensure the API is operational."""
    # Make a request to the health endpoint
    for i in ["startup", "ready", "live"]:
        print(f"Attempt at {i}: Testing health endpoint...")
        # Make a request to the health endpoint

        response = client.get(f"/api/v1/health/{i}")

        # Check if the request was successful
        assert response.status_code == 200


def test_get_case_by_id() -> None:
    """Test getting a case with ID 1."""
    # Make a request to get case with ID 1
    response = client.get("/api/v1/case/1")

    # Check if the request was successful
    assert response.status_code == 200

    # Check if the response contains a case with ID 1
    data = response.json()
    assert data["id"] == "1"

    # Print the result for debugging
    print(f"Test passed! Got case: {data}")


def test_get_non_existent_case() -> None:
    """Test getting a case that does not exist."""
    # Make a request to get a non-existent case
    response = client.get("/api/v1/case/999")

    # Check if the request returns a 404 status code
    assert response.status_code == 404

    # Check if the error message is correct
    data = response.json()
    assert data["detail"] == "Case with id 999 not found"


def test_create_case() -> None:
    """Test creating a new case."""
    # Define a new case
    new_case = {
        "id": "2",
        "deleted": False,
        "responsible_person": "John Doe",
        "status": "open",
        "customer": "Test Customer",
    }

    # Make a request to create the new case
    response = client.post("/api/v1/case/create", json=new_case)

    # Check if the request was successful
    assert response.status_code == 201

    # Check if the response contains the created case
    data = response.json()
    assert data["id"] == "2"
    assert data["responsible_person"] == "John Doe"
    assert data["status"] == "open"
    assert data["customer"] == "Test Customer"
    assert data["deleted"] is False


# Run the test if this script is executed directly
if __name__ == "__main__":
    test_get_case_by_id()
    print("All tests passed!")
