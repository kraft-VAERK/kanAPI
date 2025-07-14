result=$(curl -X POST http://localhost:8000/api/v1/case/create \
    -H "Content-Type: application/json" \
    -d '{
            "title": "New Case", 
            "description": "This is a test case",
            "customer": "John Doe",
            "responsible_person": "Jane Smith",
            "status": "open"
        }'
)
echo $result | jq '.'