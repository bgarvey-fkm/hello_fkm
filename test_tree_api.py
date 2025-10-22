"""
Test doc_meta_data_tree API to see full structure
"""
import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

loan_number = "1000175957"
url = f"https://harvestapi.firstkeyholdings.net:60000/api/doc_meta_data_tree/{loan_number}"

print(f"Fetching doc metadata tree for loan {loan_number}...")
response = requests.get(url, verify=False)

if response.status_code == 200:
    data = response.json()
    
    with open(f'loan_{loan_number}_tree.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved to: loan_{loan_number}_tree.json")
    print(f"\n📊 Structure:")
    print(json.dumps(data, indent=2)[:2000])
else:
    print(f"❌ Error: {response.status_code}")
