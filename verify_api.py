import httpx

try:
    response = httpx.post("http://localhost:8000/investigate", json={
        "user_email": "customer@example.com",
        "issue_summary": "Payment failed on checkout",
        "priority": "P2",
        "reporter_name": "Sarah J."
    })
    print("STATUS:", response.status_code)
    print("RESPONSE:")
    import json
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print("ERROR:", e)
