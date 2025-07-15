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
result=$(
    curl -X POST http://localhost:8000/api/v1/customer/create \
        -H "Content-Type: application/json" \
        --silent \
        --fail \
        -d '{
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "123-456-7890",
            "address": "123 Main St, Anytown, USA"
        }'
)
echo $result | jq '.'
