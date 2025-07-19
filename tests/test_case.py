"""# test_case.py."""

import requests

endpoint = "http://localhost:8000"


# Rest of your test code remains the same
def test_health_endpoint() -> None:
    """Test the health endpoint to ensure the API is operational."""
    # Make a request to the health endpoint
    for i in ["startup", "ready", "live"]:
        print(f"Attempt at {i}: Testing health endpoint...")
        # Make a request to the health endpoint

        response = requests.get(f"{endpoint}/api/v1/health/{i}")

        # Check if the request was successful
        assert response.status_code == 200


def create_new_users() -> None:
    """Create new users to test the user creation endpoint."""
    # Define the user data
    user_data = {
        "full_name": "Test User",
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "securepassword",
    }

    # Make a request to create the new user
    response = requests.post(f"{endpoint}/api/v1/user/create", json=user_data)

    # Check if the request was successful
    assert response.status_code == 201

    # Check if the response contains the created user
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"

    # Print the result for debugging
    print(f"Test passed! Created user: {data}")


# Run the test if this script is executed directly
if __name__ == "__main__":
    # test if the health endpoint is operational
    test_health_endpoint()
    # create new users to test the user creation endpoint
    create_new_users()
    print("All tests passed!")
