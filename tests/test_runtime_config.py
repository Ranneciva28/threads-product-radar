from config.runtime_config import RuntimeConfig
from database.db import Database


def test_runtime_config_round_trip(tmp_path):
    db = Database(tmp_path / "radar.db")
    db.initialize()
    config = RuntimeConfig(
        threads_access_token="secret-token",
        threads_api_base_url="https://graph.threads.net/v1.0",
        threads_search_endpoint="/keyword_search",
        max_posts=500,
        default_date_days=14,
        request_timeout_seconds=45,
        default_language="id",
        default_search_type="TOP",
    )

    db.save_app_settings(config.as_storage(), {"threads_access_token"})
    loaded = RuntimeConfig.from_mapping(db.get_app_settings())

    assert loaded == config


def test_seed_does_not_overwrite_ui_values(tmp_path):
    db = Database(tmp_path / "radar.db")
    db.initialize()
    db.save_app_settings({"max_posts": "900"})
    db.seed_app_settings({"max_posts": "250", "default_language": "id"})

    stored = db.get_app_settings()
    assert stored["max_posts"] == "900"
    assert stored["default_language"] == "id"


def test_runtime_config_bounds_invalid_values():
    config = RuntimeConfig.from_mapping(
        {
            "max_posts": "99999",
            "default_date_days": "invalid",
            "request_timeout_seconds": "1",
        }
    )

    assert config.max_posts == 1000
    assert config.default_date_days >= 1
    assert config.request_timeout_seconds == 5
