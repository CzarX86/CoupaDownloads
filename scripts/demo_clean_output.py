#!/usr/bin/env python3
"""
Demo Clean Output
Shows the improved, human-friendly terminal output.
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import Config
from core.unified_processor import UnifiedProcessor


def main():
    """Demonstrate the improved output."""
    print("🎯 Clean Output Demonstration")
    print("=" * 50)
    
    print("📊 Current Output Settings:")
    print(f"   🔧 VERBOSE_OUTPUT: {Config.VERBOSE_OUTPUT}")
    print(f"   🔧 SHOW_DETAILED_PROCESSING: {Config.SHOW_DETAILED_PROCESSING}")
    print(f"   🔧 SHOW_SELENIUM_LOGS: {Config.SHOW_SELENIUM_LOGS}")
    
    print(f"\n💡 To enable verbose output, set environment variables:")
    print(f"   export VERBOSE_OUTPUT=true")
    print(f"   export SHOW_DETAILED_PROCESSING=true")
    print(f"   export SHOW_SELENIUM_LOGS=true")
    
    print(f"\n📋 Current Input File:")
    detected_file = UnifiedProcessor.detect_input_file()
    file_type = UnifiedProcessor.get_file_type(detected_file)
    print(f"   📁 File: {os.path.basename(detected_file)}")
    print(f"   📋 Type: {file_type.upper()}")
    
    print(f"\n📊 Sample Output Comparison:")
    print(f"   🔇 Default (Clean):")
    print(f"      📋 Processing PO #PO15363269...")
    print(f"      📎 Found 2 attachment(s)")
    print(f"      ✅ Downloaded 2/2 files")
    
    print(f"\n   🔊 Verbose (Detailed):")
    print(f"      📋 Processing PO #PO15363269...")
    print(f"      🌐 Navigating to: https://unilever.coupahost.com/order_headers/15363269")
    print(f"      🔍 Trying CSS selector 1: span[data-supplier-name]")
    print(f"      ✅ Found supplier via CSS: SCIBITE LIMITED → SCIBITE_LIMITED")
    print(f"      📎 Found 2 attachment(s)")
    print(f"      📁 Downloading to: SCIBITE_LIMITED/")
    print(f"      ✅ Downloaded 2/2 files")
    
    print(f"\n🚀 Ready to Use:")
    print(f"   ✅ Clean, human-friendly output by default")
    print(f"   ✅ Verbose mode available when needed")
    print(f"   ✅ No more overwhelming Selenium logs")
    print(f"   ✅ Focus on what matters: progress and results")


if __name__ == "__main__":
    main() 