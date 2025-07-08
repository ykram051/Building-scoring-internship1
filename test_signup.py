#!/usr/bin/env python3
"""
Test script for the user signup functionality
"""

import sys
import os
sys.path.append('app')

from utils.auth_db import create_new_user, get_users_data, hash_password
from utils.db import execute_query

def test_signup_functionality():
    """Test the signup functionality"""
    print("Testing signup functionality...")
    
    # Test 1: Create a new user
    print("\n1. Testing user creation...")
    test_username = "testuser123"
    test_password = "testpass123"
    test_name = "Test User"
    
    # First, clean up any existing test user
    try:
        execute_query("DELETE FROM users WHERE username = :username", {"username": test_username})
        print(f"   Cleaned up existing test user: {test_username}")
    except:
        pass
    
    success, message = create_new_user(test_username, test_password, test_name)
    print(f"   Result: {'✅' if success else '❌'} {message}")
    
    if success:
        # Test 2: Check if user was created properly
        print("\n2. Verifying user creation...")
        users_data = get_users_data()
        if test_username in users_data:
            user_info = users_data[test_username]
            print(f"   ✅ User found in database")
            print(f"   - Name: {user_info.get('name')}")
            print(f"   - Role: {user_info.get('role')}")
            print(f"   - Password hash matches: {user_info.get('password') == hash_password(test_password)}")
        else:
            print(f"   ❌ User not found in database")
    
    # Test 3: Test duplicate username
    print("\n3. Testing duplicate username prevention...")
    success2, message2 = create_new_user(test_username, "different_pass", "Different Name")
    print(f"   Result: {'✅' if not success2 else '❌'} {message2}")
    
    # Test 4: Test validation
    print("\n4. Testing input validation...")
    
    # Short username
    success3, message3 = create_new_user("ab", test_password, test_name)
    print(f"   Short username: {'✅' if not success3 else '❌'} {message3}")
    
    # Short password
    success4, message4 = create_new_user("validuser", "short", test_name)
    print(f"   Short password: {'✅' if not success4 else '❌'} {message4}")
    
    # Missing required fields
    success5, message5 = create_new_user("", test_password, test_name)
    print(f"   Empty username: {'✅' if not success5 else '❌'} {message5}")
    
    # Clean up
    print("\n5. Cleaning up test data...")
    try:
        execute_query("DELETE FROM users WHERE username = :username", {"username": test_username})
        print(f"   ✅ Test user deleted")
    except Exception as e:
        print(f"   ❌ Error cleaning up: {e}")
    
    print("\n✅ Signup functionality test completed!")

if __name__ == "__main__":
    test_signup_functionality()
