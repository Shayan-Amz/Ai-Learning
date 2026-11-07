from pathlib import Path

import pytest

from local_research_agent.config import Settings, load_settings


def test_settings_default_to_offline_and_private_local_host(tmp_path: Path):
    settings = load_settings(environ={}, project_root=tmp_path)

    assert settings.data_dir == (tmp_path / ".local_data").resolve()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.model_mode == "offline"
    assert settings.llm_api_key is None


def test_settings_mark_loopback_model_as_local(tmp_path: Path):
    settings = load_settings(
        environ={
            "LOCAL_RESEARCH_LLM_BASE_URL": "http://127.0.0.1:11434/v1",
            "LOCAL_RESEARCH_LLM_MODEL": "qwen2.5:7b",
        },
        project_root=tmp_path,
    )

    assert settings.model_enabled
    assert settings.model_mode == "local"
    assert settings.llm_api_key is None


def test_settings_require_https_for_non_local_model_endpoint(tmp_path: Path):
    with pytest.raises(ValueError, match="must use HTTPS"):
        load_settings(
            environ={
                "LOCAL_RESEARCH_LLM_BASE_URL": "http://model.example/v1",
                "LOCAL_RESEARCH_LLM_MODEL": "test-model",
            },
            project_root=tmp_path,
        )


def test_settings_require_base_url_and_model_together(tmp_path: Path):
    with pytest.raises(ValueError, match="Set both"):
        load_settings(
            environ={"LOCAL_RESEARCH_LLM_MODEL": "test-model"},
            project_root=tmp_path,
        )


def test_settings_enforce_bounded_agent_step_limit(tmp_path: Path):
    with pytest.raises(ValueError, match="max steps must be between 1 and 20"):
        load_settings(
            environ={"LOCAL_RESEARCH_MAX_STEPS": "0"},
            project_root=tmp_path,
        )


def test_settings_report_remote_model_by_name_without_exposing_key():
    settings = Settings(
        data_dir=Path("/tmp/agent"),
        llm_base_url="https://api.example/v1",
        llm_model="compact-model",
        llm_api_key="never-return-this",
    )

    assert settings.model_mode == "remote"
    assert "never-return-this" not in repr(settings)
