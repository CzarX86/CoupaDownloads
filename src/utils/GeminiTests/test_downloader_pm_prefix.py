import os
import sys
from unittest.mock import MagicMock

# Ensure the src directory is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from src.core.downloader import Downloader
from src.core.config import Config


def test_downloader_accepts_pm_prefix_builds_correct_url():
    mock_driver = MagicMock()
    mock_manager = MagicMock()
    mock_manager.driver = mock_driver

    # Minimal attachment: return empty to skip download path
    mock_driver.find_elements.return_value = []

    d = Downloader(mock_driver, mock_manager)

    result = d.download_attachments_for_po('PM98765')

    mock_driver.get.assert_called_once_with(f"{Config.BASE_URL}/order_headers/98765")
    assert isinstance(result, dict)
    assert result.get('success') is True
    assert result.get('attachments_found') == 0

