import sys
import os

print("Python version:", sys.version)
print("Python executable:", sys.executable)
print("Current working directory:", os.getcwd())
print("PATH environment variable:", os.environ.get('PATH', ''))