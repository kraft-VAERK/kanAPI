#!/bin/bash

# Store cookies in a file for session persistence
COOKIE_JAR="/tmp/kanapi-cookies.txt"

# Clean up any existing cookie jar
rm -f "$COOKIE_JAR"

# result=$(curl -X POST http://localhost:8000/api/v1/case/create \
#     -H "Content-Type: application/json" \
#     -d '{
#             "title": "New Case",
#             "description": "This is a test case",
#             "customer": "John Doe",
#             "responsible_person": "Jane Smith",
#             "status": "open"
#         }'
# )
# echo $result | jq '.'
# result=$(
#     curl -X POST http://localhost:8000/api/v1/customer/create \
#         -H "Content-Type: application/json" \
#         --silent \
#         --fail \
#         -d '{
#             "name": "John Doe",
#             "email": "john.doe@example.com",
#             "phone": "123-456-7890",
#             "address": "123 Main St, Anytown, USA"
#         }'
# )
# echo $result | jq '.'

# Function to get a random name from an API
get_random_name() {
    local response
    response=$(curl --silent --fail "https://randomuser.me/api/?inc=name")
    if [ $? -eq 0 ]; then
        echo $(echo "$response" | jq -r '.results[0].name.first + " " + .results[0].name.last')
    else
        echo "John Doe" # Fallback name if API call fails
    fi
}
# Get random names for our API calls
random_name=$(get_random_name)
random_username=$(echo "$random_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '_')
email=$(echo "$random_username" | sed 's/_/./g')@example.com
password=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 25)
# random_name="Morten Jakobsen"
# random_username="morten.jakobsen"
# email="morten.jakobsen@example.com"
# password="securepassword123"


echo "Using random name: $random_name"
echo "Using random username: $random_username"
echo "Using email: $email"
echo "Using password: $password"

echo -e "\n------ STEP 1: Create a new user ------"
result=$(
    curl -X POST http://localhost:8000/api/v1/user/create \
        -H "Content-Type: application/json" \
        --silent \
        --fail \
        -d '{
            "username": "'"$random_username"'",
            "email": "'"$email"'",
            "password": "'"$password"'",
            "full_name": "'"$random_name"'"
        }'
)
echo $result | jq '.'

echo -e "\n------ STEP 2: Login with the created user ------"
# Login using the email and password
login_result=$(
    curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -c "$COOKIE_JAR" \
        --silent \
        -d '{
            "email": "'"$email"'",
            "password": "'"$password"'"
        }'
)
echo $login_result | jq '.'
echo "Session cookies stored in: $COOKIE_JAR"

echo -e "\n------ STEP 3: Access a protected endpoint (/api/v1/user/all) ------"
# Access a protected endpoint using the session cookie
protected_result=$(
    curl -X GET http://localhost:8000/api/v1/user/all \
        -H "Content-Type: application/json" \
        --silent \
        --fail \
        -b "$COOKIE_JAR"
)
echo $protected_result | jq '.'

echo -e "\n------ STEP 4: Try to access the protected endpoint without cookie (should fail) ------"
# Try to access protected endpoint without the cookie (should fail)
echo "This should fail with a 401 error:"
no_cookie_result=$(
    curl -X GET http://localhost:8000/api/v1/user/all \
        -H "Content-Type: application/json" \
        --silent \
        -w "\nStatus code: %{http_code}\n"
)
echo $no_cookie_result

echo -e "\n------ STEP 5: Logout the user ------"
# Logout to invalidate the session
logout_result=$(
    curl -X POST http://localhost:8000/api/v1/auth/logout \
        -H "Content-Type: application/json" \
        --silent \
        --fail \
        -b "$COOKIE_JAR" \
        -c "$COOKIE_JAR"
)
echo $logout_result | jq '.'

echo -e "\n------ STEP 6: Try to access protected endpoint after logout (should fail) ------"
# Try to access the protected endpoint after logout (should fail)
echo "This should fail with a 401 error:"
after_logout_result=$(
    curl -X GET http://localhost:8000/api/v1/user/all \
        -H "Content-Type: application/json" \
        --silent \
        -b "$COOKIE_JAR" \
        -w "\nStatus code: %{http_code}\n"
)
echo $after_logout_result

# Alternative: Use the OAuth2 token authentication
echo -e "\n------ STEP 7: Authenticate with OAuth2 (username/password) ------"
token_result=$(
    curl -X POST http://localhost:8000/api/v1/auth/token \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --silent \
        --fail \
        -d "username=$email&password=$password"
)
# Extract the access token
access_token=$(echo $token_result | jq -r '.access_token')
echo "Received access token: ${access_token:0:20}..." # Only show the beginning of the token

echo -e "\n------ STEP 8: Access protected endpoint with bearer token ------"
# Access protected endpoint with the bearer token
token_protected_result=$(
    curl -X GET http://localhost:8000/api/v1/user/all \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $access_token" \
        --silent \
        --fail
)
echo $token_protected_result | jq '.'

# Clean up the cookie jar
# rm -f "$COOKIE_JAR"
echo -e "\nDone! All tests completed."
