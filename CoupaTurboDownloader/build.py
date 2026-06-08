import os
import sys
import subprocess

def run_build():
    print("Building Coupa Turbo Downloader...")
    
    # Base command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=CoupaTurboDownloader",
        "--windowed", # Disables console window in GUI mode
    ]
    
    # Path to entry point
    entry_point = os.path.join("src", "main.py")
    
    # Format --add-data correctly depending on OS
    # format is: source_dir:dest_dir (POSIX) or source_dir;dest_dir (Windows)
    separator = ";" if sys.platform.startswith("win") else ":"
    
    web_assets = os.path.join("src", "gui", "web")
    dest_assets = os.path.join("src", "gui", "web")
    
    cmd.append(f"--add-data={web_assets}{separator}{dest_assets}")
    cmd.append(entry_point)
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\nBuild completed successfully!")
        print("Find your portable executable inside the 'dist/' folder.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with exit code: {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    run_build()
