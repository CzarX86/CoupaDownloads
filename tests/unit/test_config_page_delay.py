import warnings

from src.config.app_config import AppConfig
from src.lib.config import Config


def test_config_exposes_page_delay_from_appconfig():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        cfg_delay = getattr(Config, "PAGE_DELAY")

    app_delay = AppConfig().page_delay

    assert isinstance(cfg_delay, (int, float))
    assert cfg_delay == app_delay
