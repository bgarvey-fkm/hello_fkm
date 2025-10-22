"""
Try different endpoints to find file list
"""
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

loan_number = "1000175957"
base = "https://harvestapi.firstkeyholdings.net:60000/api"

endpoints = [
    f"/files/{loan_number}",
    f"/loan/{loan_number}/files",
    f"/documents/{loan_number}",
    f"/loan_files/{loan_number}",
]

for endpoint in endpoints:
    url = base + endpoint
    print(f"\nTrying: {url}")
    response = requests.get(url, verify=False)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ SUCCESS! Found files endpoint")
        print(f"Response length: {len(response.text)}")
        break
