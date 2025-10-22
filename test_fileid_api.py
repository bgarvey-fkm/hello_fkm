"""
Test doc_meta_data_tree with FileId instead of LoanNumber
Also test PDF endpoint with FileId
"""
import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test 1: doc_meta_data_tree with FileId
print("=" * 80)
print("Test 1: doc_meta_data_tree with FileId 1116")
print("=" * 80)
url = "https://harvestapi.firstkeyholdings.net:60000/api/doc_meta_data_tree/1116"
response = requests.get(url, verify=False)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    with open('test_fileid_1116_tree.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved to: test_fileid_1116_tree.json")
    print(f"Items returned: {len(data) if isinstance(data, list) else 'dict'}")
    print(f"\nFirst item sample:")
    print(json.dumps(data[0] if isinstance(data, list) else data, indent=2)[:500])
else:
    print(f"❌ Error")

# Test 2: PDF endpoint with FileId
print("\n" + "=" * 80)
print("Test 2: PDF endpoint with FileId 211612")
print("=" * 80)
url = "https://harvestapi.firstkeyholdings.net:60000/api/pdf/211612"
response = requests.get(url, verify=False)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print(f"Content-Length: {len(response.content)} bytes")

if response.status_code == 200 and response.content:
    with open('test_fileid_211612.pdf', 'wb') as f:
        f.write(response.content)
    print(f"✅ Saved PDF to: test_fileid_211612.pdf")
