"""
Generate RSA key pair for WhatsApp Flows encryption.
Run this once to generate keys, then upload public key to Meta.
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import os

def generate_keys():
    """Generate RSA 2048-bit key pair for WhatsApp Flows."""
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize private key (PEM format)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize public key (PEM format)
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Save private key
    with open('private_key.pem', 'wb') as f:
        f.write(private_pem)
    print("✅ Private key saved to: private_key.pem")
    print("   ⚠️  Keep this file secure! Add to .gitignore!")
    
    # Save public key
    with open('public_key.pem', 'wb') as f:
        f.write(public_pem)
    print("✅ Public key saved to: public_key.pem")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("\n1. Copy the PUBLIC KEY below and paste it in WhatsApp Manager:")
    print("-"*60)
    print(public_pem.decode('utf-8'))
    print("-"*60)
    
    print("\n2. Add PRIVATE_KEY to your .env file:")
    print("   PRIVATE_KEY_PATH=private_key.pem")
    
    print("\n3. Add to .gitignore:")
    print("   private_key.pem")
    
    print("\n4. Restart your Flask app")
    
    return private_pem, public_pem


if __name__ == '__main__':
    generate_keys()
