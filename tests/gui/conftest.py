import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]  # Go up two levels: gui -> tests -> project root
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
