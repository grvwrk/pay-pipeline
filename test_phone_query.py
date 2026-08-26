import httpx, json

client = httpx.Client(base_url='http://127.0.0.1:8000')
r = client.post('/api/v1/chat', json={'user_message': 'find me the best available small display phone under 50000 rs'})
data = r.json()

print("Status:", r.status_code)
print("Response Message:\n", data.get('message'))
print("\nMatched Products Count:", len(data.get('products', [])))
for p in data.get('products', []):
    print(f"- {p['name']} | Price: Rs {p['price']} | Display: {p.get('specs', {}).get('display')}")

if data.get('upsell_bundle'):
    print("\nAI Upsell Opportunity:", data['upsell_bundle']['title'], "| Savings:", data['upsell_bundle']['savings_amount'])
