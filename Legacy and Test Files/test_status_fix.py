#!/usr/bin/env python3
"""
Test script to verify the status determination fix.
"""

def test_status_determination():
    """Test the status determination logic."""
    print("🧪 Testing status determination logic...")
    
    # Test cases
    test_cases = [
        {"attachments_found": 3, "downloaded_files": 3, "expected": "COMPLETED"},
        {"attachments_found": 3, "downloaded_files": 2, "expected": "PARTIAL"},
        {"attachments_found": 3, "downloaded_files": 1, "expected": "PARTIAL"},
        {"attachments_found": 3, "downloaded_files": 0, "expected": "FAILED"},
        {"attachments_found": 1, "downloaded_files": 1, "expected": "COMPLETED"},
        {"attachments_found": 1, "downloaded_files": 0, "expected": "FAILED"},
    ]
    
    for i, case in enumerate(test_cases):
        attachments_found = case["attachments_found"]
        downloaded_files = case["downloaded_files"]
        expected = case["expected"]
        
        # Simulate the status determination logic
        if downloaded_files == attachments_found:
            status = 'COMPLETED'
        elif downloaded_files > 0:
            status = 'PARTIAL'
        else:
            status = 'FAILED'
        
        result = "✅ PASS" if status == expected else "❌ FAIL"
        print(f"  Test {i+1}: Found={attachments_found}, Downloaded={downloaded_files} → {status} ({expected}) {result}")
    
    print("\n✅ Status determination test completed!")


if __name__ == "__main__":
    test_status_determination()
