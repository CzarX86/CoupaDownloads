import os
import importlib
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
CORE_PATH = os.path.join(SRC_PATH, 'core')
UTILS_PATH = os.path.join(SRC_PATH, 'utils')


def test_src_directory_exists():
    assert os.path.isdir(SRC_PATH), f"src directory does not exist at {SRC_PATH}"

def test_core_directory_exists():
    assert os.path.isdir(CORE_PATH), f"core directory does not exist at {CORE_PATH}"

def test_utils_directory_exists():
    assert os.path.isdir(UTILS_PATH), f"utils directory does not exist at {UTILS_PATH}"

def test_core_module_imports():
    import sys
    sys.path.insert(0, SRC_PATH)
    # Try importing each core module
    for module in [
        'core.browser',
        'core.config',
        'core.csv_processor',
        'core.downloader',
    ]:
        importlib.import_module(module)

def test_utils_module_imports():
    import sys
    sys.path.insert(0, SRC_PATH)
    importlib.import_module('utils.excel_export_example') 