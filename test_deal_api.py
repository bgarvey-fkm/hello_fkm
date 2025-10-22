"""
Quick test to see what the deal API returns
"""
import requests
import json
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

deal_id = 2
url = f"https://harvestapi.firstkeyholdings.net:60000/api/deal/{deal_id}"

print(f"Fetching deal {deal_id} data...")
response = requests.get(url, verify=False)

if response.status_code == 200:
    deal_data = response.json()
    
    # Save full response
    with open(f'deal_{deal_id}_data.json', 'w', encoding='utf-8') as f:
        json.dump(deal_data, f, indent=2)
    
    print(f"✅ Deal data saved to: deal_{deal_id}_data.json")
    print(f"\nTop-level keys: {list(deal_data.keys())}")
    
    # Try to find loans
    if isinstance(deal_data, list):
        print(f"\n📊 Found {len(deal_data)} items in deal")
        if len(deal_data) > 0:
            print(f"\nFirst item keys: {list(deal_data[0].keys())}")
            print(f"\nFirst item sample:")
            print(json.dumps(deal_data[0], indent=2)[:500])
    elif isinstance(deal_data, dict):
        print(f"\n📊 Deal data is a dictionary")
        for key, value in deal_data.items():
            if isinstance(value, list):
                print(f"  - {key}: {len(value)} items")
            else:
                print(f"  - {key}: {type(value).__name__}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
