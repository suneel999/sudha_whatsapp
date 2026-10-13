"""
Sign and upload public key via WhatsApp Cloud API.
This registers your encryption key for Flows endpoint.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def sign_public_key():
    """Sign and upload public key to WhatsApp Cloud API."""
    
    # Check for keys
    if not os.path.exists('public_key.pem'):
        print("❌ public_key.pem not found!")
        print("   Run: python generate_keys.py")
        return False
    
    # Read public key
    with open('public_key.pem', 'r') as f:
        public_key = f.read().strip()
    
    # Get credentials from .env
    access_token = os.getenv('WHATSAPP_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token:
        print("❌ WHATSAPP_TOKEN not found in .env")
        return False
    
    if not phone_number_id:
        print("❌ WHATSAPP_PHONE_NUMBER_ID not found in .env")
        return False
    
    print("="*60)
    print("SIGNING PUBLIC KEY VIA CLOUD API")
    print("="*60)
    print(f"\nPhone Number ID: {phone_number_id}")
    print(f"Public Key Length: {len(public_key)} chars")
    
    # API endpoint for uploading business encryption key
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/whatsapp_business_encryption"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'business_public_key': public_key
    }
    
    print("\n📤 Uploading public key...")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Public key signed and uploaded!")
            print("\nNext steps:")
            print("1. Go to WhatsApp Manager > Flows")
            print("2. Create or edit your Flow")
            print("3. Set Endpoint URI to: https://your-ngrok-url/flow")
            print("4. Complete the remaining setup steps")
            return True
        else:
            print(f"\n❌ Failed to upload public key")
            print("\nTrying alternative method...")
            return try_alternative_method(access_token, phone_number_id, public_key)
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def try_alternative_method(access_token: str, phone_number_id: str, public_key: str):
    """Try alternative API endpoint for signing."""
    
    # Try with WABA ID instead
    print("\n" + "="*60)
    print("TRYING ALTERNATIVE: Get WABA ID first")
    print("="*60)
    
    # Get WABA ID from phone number
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    params = {
        'fields': 'id,display_phone_number,verified_name'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"\nPhone info: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Phone: {data.get('display_phone_number', 'N/A')}")
            print(f"✓ Name: {data.get('verified_name', 'N/A')}")
    except Exception as e:
        print(f"Error getting phone info: {e}")
    
    # Try WABA endpoint
    print("\n" + "-"*60)
    print("Enter your WhatsApp Business Account ID (WABA ID)")
    print("Find it in: Business Settings > Accounts > WhatsApp Accounts")
    print("-"*60)
    
    waba_id = input("\nWABA ID (or press Enter to skip): ").strip()
    
    if waba_id:
        return upload_to_waba(access_token, waba_id, public_key)
    
    return False


def upload_to_waba(access_token: str, waba_id: str, public_key: str):
    """Upload public key to WABA endpoint."""
    
    url = f"https://graph.facebook.com/v18.0/{waba_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Try to update WABA with business public key
    payload = {
        'business_public_key': public_key
    }
    
    print(f"\n📤 Uploading to WABA {waba_id}...")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS!")
            return True
        else:
            print("\n❌ Failed")
            print("\nManual alternative:")
            print_manual_instructions(public_key)
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def print_manual_instructions(public_key: str):
    """Print manual curl command for signing."""
    
    print("\n" + "="*60)
    print("MANUAL CURL COMMAND")
    print("="*60)
    
    # Escape the key for curl
    escaped_key = public_key.replace('\n', '\\n')
    
    print(f"""
Try this curl command in your terminal:

curl -X POST "https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID/whatsapp_business_encryption" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{{"business_public_key": "{escaped_key}"}}'

Replace:
- YOUR_PHONE_NUMBER_ID with: {os.getenv('WHATSAPP_PHONE_NUMBER_ID', 'your_phone_id')}
- YOUR_ACCESS_TOKEN with your token from .env

""")
    
    print("="*60)
    print("YOUR PUBLIC KEY (for copy-paste):")
    print("="*60)
    print(public_key)


def list_flows():
    """List existing flows."""
    
    access_token = os.getenv('WHATSAPP_TOKEN')
    
    print("\nEnter your WABA ID to list flows:")
    waba_id = input("WABA ID: ").strip()
    
    if not waba_id:
        return
    
    url = f"https://graph.facebook.com/v18.0/{waba_id}/flows"
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    response = requests.get(url, headers=headers)
    
    print(f"\nFlows Response: {response.text}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("WHATSAPP FLOWS - PUBLIC KEY SIGNING TOOL")
    print("="*60)
    
    print("\nOptions:")
    print("1. Sign public key")
    print("2. List existing flows")
    print("3. Show public key only")
    
    choice = input("\nChoice (1/2/3): ").strip()
    
    if choice == '1':
        sign_public_key()
    elif choice == '2':
        list_flows()
    elif choice == '3':
        if os.path.exists('public_key.pem'):
            with open('public_key.pem', 'r') as f:
                print("\n" + f.read())
        else:
            print("❌ Run generate_keys.py first")
    else:
        sign_public_key()
