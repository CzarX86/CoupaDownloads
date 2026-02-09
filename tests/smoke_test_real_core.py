import time
import os
from src.core.real_core_system import RealCoreSystem
from src.core.config import ConfigurationSettings
from src.core.status import StatusMessage

def test_real_core_smoke():
    core = RealCoreSystem()
    config = ConfigurationSettings()
    config.worker_count = 1
    
    messages = []
    def callback(msg):
        messages.append(msg)
        print(f"Callback: {msg.level.value}: {msg.message} (progress: {msg.progress})")

    print("Starting smoke test...")
    handle = core.start_downloads(config, callback)
    
    # Wait some time for processing to start and hopefully get some updates
    # Since we don't have real POs in the input dir, it might finish quickly with "No POs found"
    max_wait = 30
    start_time = time.time()
    while time.time() - start_time < max_wait:
        if core.get_operation_status(handle) in ("completed", "error"):
            break
        time.sleep(1)
    
    print(f"Finished after {time.time() - start_time:.1f}s")
    print(f"Total messages received: {len(messages)}")
    for msg in messages[:10]:
        print(f" - {msg.message}")
    
    assert len(messages) > 0
    print("✅ Smoke test PASSED")

if __name__ == "__main__":
    test_real_core_smoke()
