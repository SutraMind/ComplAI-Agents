#!/usr/bin/env python3
"""
Test script to verify comment editing functionality.
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

def test_comment_edit():
    """Test comment editing functionality."""
    print("Testing comment editing functionality...")
    
    # First, let's get existing comments
    response = requests.get(f"{BASE_URL}/reports/sample_report/comments")
    if response.status_code == 200:
        comments = response.json()['data']
        if comments:
            comment_id = comments[0]['id']
            original_text = comments[0]['comment_text']
            print(f"Found comment: {comment_id}")
            print(f"Original text: {original_text}")
            
            # Test updating the comment
            new_text = f"Updated comment text - {time.time()}"
            update_response = requests.put(
                f"{BASE_URL}/comments/{comment_id}",
                json={"comment_text": new_text},
                headers={"Content-Type": "application/json"}
            )
            
            if update_response.status_code == 200:
                print("✓ Comment updated successfully")
                updated_comment = update_response.json()['data']
                print(f"New text: {updated_comment['comment_text']}")
                
                # Verify the update
                verify_response = requests.get(f"{BASE_URL}/reports/sample_report/comments")
                if verify_response.status_code == 200:
                    updated_comments = verify_response.json()['data']
                    found_comment = next((c for c in updated_comments if c['id'] == comment_id), None)
                    if found_comment and found_comment['comment_text'] == new_text:
                        print("✓ Comment update verified")
                        return True
                    else:
                        print("✗ Comment update not verified")
                        return False
            else:
                print(f"✗ Failed to update comment: {update_response.status_code}")
                print(update_response.text)
                return False
        else:
            print("No comments found to test with")
            return False
    else:
        print(f"Failed to get comments: {response.status_code}")
        return False

if __name__ == "__main__":
    test_comment_edit()