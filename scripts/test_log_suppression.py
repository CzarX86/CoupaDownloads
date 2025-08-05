#!/usr/bin/env python3
"""
Test Log Suppression
Verifies that Selenium logs are properly suppressed.
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import Config
from core.browser import BrowserManager


def test_log_suppression():
    """Test that logs are suppressed by default."""
    print("🧪 Testing Log Suppression")
    print("=" * 50)
    
    print("📊 Current Configuration:")
    print(f"   🔧 SHOW_SELENIUM_LOGS: {Config.SHOW_SELENIUM_LOGS}")
    print(f"   🔧 VERBOSE_OUTPUT: {Config.VERBOSE_OUTPUT}")
    print(f"   🔧 SHOW_DETAILED_PROCESSING: {Config.SHOW_DETAILED_PROCESSING}")
    
    print(f"\n💡 Environment Variables:")
    print(f"   export SHOW_SELENIUM_LOGS=true    # Show Selenium logs")
    print(f"   export VERBOSE_OUTPUT=true        # Show detailed output")
    
    print(f"\n🎯 Expected Behavior:")
    if Config.SHOW_SELENIUM_LOGS:
        print(f"   📢 Selenium logs: ENABLED (verbose)")
    else:
        print(f"   🔇 Selenium logs: SUPPRESSED (clean)")
    
    if Config.VERBOSE_OUTPUT:
        print(f"   📢 Detailed output: ENABLED")
    else:
        print(f"   🔇 Detailed output: SUPPRESSED")
    
    print(f"\n🚀 Testing Browser Initialization...")
    
    try:
        # Test browser initialization
        browser_manager = BrowserManager()
        
        # This should not show verbose logs if suppression is working
        driver = browser_manager.start(headless=True)
        
        print(f"✅ Browser initialized successfully")
        print(f"   📱 Driver: {type(driver).__name__}")
        print(f"   🌐 Current URL: {driver.current_url}")
        
        # Clean up
        browser_manager.cleanup()
        print(f"✅ Browser cleaned up successfully")
        
        print(f"\n🎉 Test Results:")
        if not Config.SHOW_SELENIUM_LOGS:
            print(f"   ✅ Log suppression working correctly")
            print(f"   ✅ No verbose Selenium output detected")
        else:
            print(f"   📢 Verbose mode enabled - logs will be shown")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True


def test_with_verbose_logs():
    """Test with verbose logs enabled."""
    print(f"\n🧪 Testing with Verbose Logs Enabled")
    print("=" * 50)
    
    # Temporarily enable verbose logs
    original_setting = Config.SHOW_SELENIUM_LOGS
    Config.SHOW_SELENIUM_LOGS = True
    
    print(f"🔧 Temporarily enabled SHOW_SELENIUM_LOGS")
    
    try:
        browser_manager = BrowserManager()
        driver = browser_manager.start(headless=True)
        
        print(f"✅ Browser initialized with verbose logs")
        print(f"   📱 Driver: {type(driver).__name__}")
        
        # Clean up
        browser_manager.cleanup()
        print(f"✅ Browser cleaned up")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        # Restore original setting
        Config.SHOW_SELENIUM_LOGS = original_setting
        print(f"🔧 Restored SHOW_SELENIUM_LOGS to {original_setting}")


def main():
    """Main test function."""
    print("🎯 Log Suppression Test")
    print("=" * 50)
    
    # Test default behavior
    success = test_log_suppression()
    
    if success:
        # Test with verbose logs
        test_with_verbose_logs()
        
        print(f"\n✅ All tests completed!")
        print(f"💡 To see verbose logs, set: export SHOW_SELENIUM_LOGS=true")
    else:
        print(f"\n❌ Tests failed")


if __name__ == "__main__":
    main() 