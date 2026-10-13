"""
Verification script for Interactive AI Responses
"""
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from ai_fallback import _parse_interactive_response, _validate_response
from intent_router import route_message

def test_parsing():
    print("--- Testing Button Parsing ---")
    
    samples = [
        "Dr. Mahesh Babu is our chief cardiologist. [[BUTTONS: book, doctors]]",
        "We are located near the railway station. [[BUTTONS: location, contact]]",
        "Our OPD hours are Mon-Sat 8am-8pm. [[BUTTONS: hours, book, emergency]]",
        "Simple text with no buttons."
    ]
    
    for sample in samples:
        text, buttons = _parse_interactive_response(sample)
        print(f"Input: {sample}")
        print(f"Parsed Text: {text}")
        print(f"Buttons: {buttons}")
        print("-" * 30)

def test_validation():
    print("\n--- Testing Response Validation ---")
    
    safe_samples = [
        "We have cardiologists available.",
        "You can book an appointment here.",
        "The hospital is open 24/7."
    ]
    
    unsafe_samples = [
        "I recommend taking 500mg of paracetamol.",
        "You should take this medicine twice a day.",
        "I think you have a fever.",
        "What is your name? I can help you.",
        "Your appointment is confirmed for tomorrow."
    ]
    
    for s in safe_samples:
        valid = _validate_response(s)
        print(f"Safe? {'YES' if valid else 'NO'} | Text: {s}")
        
    for s in unsafe_samples:
        valid = _validate_response(s)
        print(f"Unsafe blocked? {'YES' if not valid else 'NO'} | Text: {s}")

if __name__ == "__main__":
    test_parsing()
    test_validation()
    print("\nVerification complete!")
