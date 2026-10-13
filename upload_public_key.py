"""
Upload and sign public key to WhatsApp Business API.
Run this after generating keys with generate_keys.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def upload_public_key():
    """Upload public key to WhatsApp Business API for signing."""
    
    # Read public key
    if not os.path.exists('public_key.pem'):
        print("❌ public_key.pem not found. Run generate_keys.py first.")
        return
    
    with open('public_key.pem', 'r') as f:
        public_key = f.read()
    
    print("="*60)
    print("PUBLIC KEY FOR WHATSAPP MANAGER")
    print("="*60)
    print("\nCopy the ENTIRE key below (including BEGIN/END lines):\n")
    print("-"*60)
    print(public_key)
    print("-"*60)
    
    print("\n" + "="*60)
    print("STEPS TO SIGN IN WHATSAPP MANAGER:")
    print("="*60)
    print("""
1. Go to WhatsApp Manager > Flows > Your Flow
2. Click on "Sign public key" step
3. Paste the public key above
4. Click "Upload and Sign"

If using API instead:
""")
    
    waba_id = input("\nEnter your WhatsApp Business Account ID (or press Enter to skip): ").strip()
    
    if not waba_id:
        print("\n✅ Copy the public key above and paste it in WhatsApp Manager.")
        return
    
    access_token = os.getenv('WHATSAPP_TOKEN')
    
    if not access_token:
        print("❌ WHATSAPP_TOKEN not found in .env")
        return
    
    # Upload via API
    url = f"https://graph.facebook.com/v18.0/{waba_id}"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # First, let's try to get the flow ID
    print("\nFetching your flows...")
    
    flows_url = f"https://graph.facebook.com/v18.0/{waba_id}/flows"
    response = requests.get(flows_url, headers=headers)
    
    if response.status_code == 200:
        flows = response.json().get('data', [])
        if flows:
            print("\nYour flows:")
            for i, flow in enumerate(flows, 1):
                print(f"  {i}. {flow.get('name', 'Unnamed')} (ID: {flow.get('id')})")
        else:
            print("No flows found.")
    else:
        print(f"Error fetching flows: {response.text}")
    
    print("\n" + "="*60)
    print("MANUAL UPLOAD INSTRUCTIONS")
    print("="*60)
    print("""
To upload via API, use this curl command:

curl -X POST "https://graph.facebook.com/v18.0/FLOW_ID" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -F "flow_json=@flow_definition.json" \\
  -F "name=clinic_appointment_booking"

Or simply paste the public key in WhatsApp Manager UI.
""")


def format_key_for_json(key_content: str) -> str:
    """Format PEM key for JSON (escape newlines)."""
    return key_content.replace('\n', '\\n')


if __name__ == '__main__':
    upload_public_key()
