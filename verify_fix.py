import os
import shutil
import tempfile
import time
from src.worker_manager import _create_profile_clone
from src.lib.config import Config

def test_profile_cloning():
    print("Testing profile cloning...")
    
    # Create a dummy profile structure
    with tempfile.TemporaryDirectory() as base_ud:
        profile_name = "Default"
        profile_dir = os.path.join(base_ud, profile_name)
        os.makedirs(profile_dir)
        
        # Create Local State
        with open(os.path.join(base_ud, "Local State"), "w") as f:
            f.write("dummy local state")
            
        # Create some profile files
        with open(os.path.join(profile_dir, "Preferences"), "w") as f:
            f.write("dummy preferences")
        with open(os.path.join(profile_dir, "History"), "w") as f:
            f.write("dummy history")
            
        # Create a clone
        clone_root = os.path.join(tempfile.gettempdir(), f"test_clone_{int(time.time())}")
        try:
            _create_profile_clone(base_ud, profile_name, clone_root)
            
            # Verify clone
            print(f"Verifying clone at: {clone_root}")
            assert os.path.exists(os.path.join(clone_root, "Local State")), "Local State missing"
            assert os.path.exists(os.path.join(clone_root, profile_name)), "Profile folder missing"
            assert os.path.exists(os.path.join(clone_root, profile_name, "Preferences")), "Preferences missing"
            assert os.path.exists(os.path.join(clone_root, profile_name, "History")), "History missing"
            
            print("✅ Profile cloning verified successfully!")
        finally:
            if os.path.exists(clone_root):
                shutil.rmtree(clone_root)

if __name__ == "__main__":
    try:
        test_profile_cloning()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
