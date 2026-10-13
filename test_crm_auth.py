import requests
import json
import time

BASE_URL = "http://localhost:5000"  # Assuming app runs on 5000 locally

def test_auth():
    print("=== CRM AUTHENTICATION TEST ===")
    
    # 1. Test unauthorized access to stats
    print("\n1. Testing unauthorized access to /api/stats...")
    try:
        res = requests.get(f"{BASE_URL}/api/stats")
        print(f"Status: {res.status_code}")
        print(f"Body: {res.json()}")
        if res.status_code == 401:
            print("SUCCESS: Unauthorized access blocked.")
        else:
            print("FAILED: Unauthorized access allowed!")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Test login with invalid credentials
    print("\n2. Testing login with invalid credentials...")
    try:
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        print(f"Status: {res.status_code}")
        print(f"Body: {res.json()}")
        if res.status_code == 401:
            print("SUCCESS: Invalid login rejected.")
        else:
            print("FAILED: Invalid login accepted!")
    except Exception as e:
        print(f"Error: {e}")

    # 3. Test login with valid credentials (admin/mallika123)
    print("\n3. Testing login with valid credentials...")
    token = None
    try:
        res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "mallika123"
        })
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Body: {data}")
        if res.status_code == 200 and data.get('token'):
            print("SUCCESS: Registered admin logged in.")
            token = data['token']
        else:
            print("FAILED: Admin login failed!")
    except Exception as e:
        print(f"Error: {e}")

    if not token:
        print("\nSkipping further tests as token missing.")
        return

    # 4. Test authorized access with token
    print("\n4. Testing authorized access to /api/stats...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(f"{BASE_URL}/api/stats", headers=headers)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print("SUCCESS: Authorized access granted.")
        else:
            print(f"FAILED: Authorized access denied? {res.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # 5. Test logout
    print("\n5. Testing logout...")
    try:
        res = requests.post(f"{BASE_URL}/api/auth/logout", headers=headers)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print("SUCCESS: Logout successful.")
        else:
            print("FAILED: Logout failed!")
    except Exception as e:
        print(f"Error: {e}")

    # 6. Test access AFTER logout
    print("\n6. Testing access after logout...")
    try:
        res = requests.get(f"{BASE_URL}/api/stats", headers=headers)
        print(f"Status: {res.status_code}")
        if res.status_code == 401:
            print("SUCCESS: Access rejected after logout.")
        else:
            print("FAILED: Access still allowed after logout!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_auth()
