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

echo "Using random name: $random_name"
echo "Using random username: $random_username"
echo "Using email: $email"
echo "Using password: $password"
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
