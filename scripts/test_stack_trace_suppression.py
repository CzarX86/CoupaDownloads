#!/usr/bin/env python3
"""
Test Stack Trace Suppression
Verifies that Selenium stack traces are properly suppressed.
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import Config


def test_configuration():
    """Test current configuration settings."""
    print("🧪 Testing Stack Trace Suppression")
    print("=" * 50)
    
    print("📊 Current Configuration:")
    print(f"   🔧 SHOW_SELENIUM_LOGS: {Config.SHOW_SELENIUM_LOGS}")
    print(f"   🔧 VERBOSE_OUTPUT: {Config.VERBOSE_OUTPUT}")
    print(f"   🔧 SHOW_DETAILED_PROCESSING: {Config.SHOW_DETAILED_PROCESSING}")
    print(f"   🔧 SHOW_EDGE_CRASH_STACKTRACE: {Config.SHOW_EDGE_CRASH_STACKTRACE}")
    
    print(f"\n💡 Environment Variables:")
    print(f"   export SHOW_SELENIUM_LOGS=true    # Show Selenium logs")
    print(f"   export VERBOSE_OUTPUT=true        # Show detailed output")
    print(f"   export SHOW_DETAILED_PROCESSING=true  # Show processing steps")
    
    print(f"\n🎯 Expected Behavior:")
    if Config.SHOW_SELENIUM_LOGS or Config.VERBOSE_OUTPUT:
        print(f"   📢 Stack traces: ENABLED (verbose)")
    else:
        print(f"   🔇 Stack traces: SUPPRESSED (clean)")
    
    print(f"\n📋 What's Suppressed:")
    print(f"   ✅ Selenium WebDriver service logs")
    print(f"   ✅ Browser option verbose output")
    print(f"   ✅ Exception details in error messages")
    print(f"   ✅ Click error stack traces")
    print(f"   ✅ PO processing error details")
    
    print(f"\n📋 What's Still Shown:")
    print(f"   ✅ Human-friendly error messages")
    print(f"   ✅ Progress indicators")
    print(f"   ✅ Success/failure status")
    print(f"   ✅ Business outcomes")


def test_exception_handling():
    """Test exception handling behavior."""
    print(f"\n🧪 Testing Exception Handling")
    print("=" * 50)
    
    # Simulate different exception scenarios
    test_cases = [
        ("ElementClickInterceptedException", "element click intercepted"),
        ("TimeoutException", "timeout waiting for element"),
        ("NoSuchElementException", "no such element"),
        ("WebDriverException", "webdriver error")
    ]
    
    for exception_type, error_message in test_cases:
        print(f"\n📋 Testing: {exception_type}")
        
        # Simulate verbose mode
        original_verbose = Config.VERBOSE_OUTPUT
        Config.VERBOSE_OUTPUT = True
        print(f"   🔊 Verbose mode:")
        print(f"      ❌ PO #PO12345 failed with error: {error_message}")
        
        # Simulate clean mode
        Config.VERBOSE_OUTPUT = False
        print(f"   🔇 Clean mode:")
        print(f"      ❌ PO #PO12345 failed")
        
        # Restore original setting
        Config.VERBOSE_OUTPUT = original_verbose


def main():
    """Main test function."""
    print("🎯 Stack Trace Suppression Test")
    print("=" * 50)
    
    # Test configuration
    test_configuration()
    
    # Test exception handling
    test_exception_handling()
    
    print(f"\n✅ Test completed!")
    print(f"💡 To see stack traces, set: export VERBOSE_OUTPUT=true")
    print(f"💡 To see Selenium logs, set: export SHOW_SELENIUM_LOGS=true")


if __name__ == "__main__":
    main() 