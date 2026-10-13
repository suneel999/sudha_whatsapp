from database import init_database, verify_crm_login, create_crm_user, create_crm_session, get_crm_session, clear_crm_session
import time

def run_test():
    print("Initializing database...")
    init_database()
    
    username = "testuser_verif"
    password = "testpassword123"
    
    print(f"Creating user: {username}")
    created = create_crm_user(username, password, "Test Verifier", "admin")
    if not created:
        print("User already exists or failed to create. (OK if rerunning)")
    
    print("Verifying login...")
    user = verify_crm_login(username, password)
    if user and user['username'] == username:
        print(f"SUCCESS: User verified. ID: {user['id']}")
    else:
        print("FAILED: Verification failed.")
        return
        
    print("Creating session...")
    token = create_crm_session(user['id'])
    if token:
        print(f"SUCCESS: Session created. Token start: {token[:8]}")
    else:
        print("FAILED: Session creation failed.")
        return
        
    print("Validating session...")
    session = get_crm_session(token)
    if session and session['username'] == username:
        print("SUCCESS: Session valid.")
    else:
        print("FAILED: Session validation failed.")
        return
        
    print("Clearing session...")
    clear_crm_session(token)
    session_after = get_crm_session(token)
    if not session_after:
        print("SUCCESS: Session cleared correctly.")
    else:
        print("FAILED: Session still exists after clearing.")
        return

    print("\n=== ALL LOGIC TESTS PASSED ===")

if __name__ == "__main__":
    run_test()
