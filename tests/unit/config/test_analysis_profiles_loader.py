from pathlib import Path

import pytest


def write_analysis_profiles_config(workspace: Path, contents: str) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    config_path = workspace / "analysis_profiles.yml"
    config_path.write_text(contents, encoding="utf-8")
    return config_path


def test_loads_minimal_analysis_profile_configuration(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_analysis_profiles_config
    from observer_rock.config.models import AnalysisProfileConfig, AnalysisProfilesConfig

    config_path = write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
    model_service: openai_fast
""".strip(),
    )

    config = load_analysis_profiles_config(config_path)

    assert isinstance(config, AnalysisProfilesConfig)
    assert set(config.analysis_profiles) == {"street_mentions_v1"}
    profile = config.analysis_profiles["street_mentions_v1"]
    assert isinstance(profile, AnalysisProfileConfig)
    assert profile.plugin == "llm_extract"
    assert profile.model_service == "openai_fast"


def test_rejects_analysis_profile_without_plugin(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_analysis_profiles_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    model_service: openai_fast
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_analysis_profiles_config(config_path)

    assert "plugin" in str(exc_info.value)


def test_rejects_analysis_profile_with_blank_plugin(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_analysis_profiles_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: ""
    model_service: openai_fast
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_analysis_profiles_config(config_path)

    assert "plugin" in str(exc_info.value)


def test_rejects_analysis_profile_without_model_service(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_analysis_profiles_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_analysis_profiles_config(config_path)

    assert "model_service" in str(exc_info.value)


def test_rejects_analysis_profile_with_negative_retries(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_analysis_profiles_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
    model_service: openai_fast
    retries: -1
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_analysis_profiles_config(config_path)

    assert "retries" in str(exc_info.value)


def test_rejects_analysis_profile_with_blank_model_service(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_analysis_profiles_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
    model_service: ""
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_analysis_profiles_config(config_path)

    assert "model_service" in str(exc_info.value)


def test_rejects_analysis_profile_with_blank_prompt_ref(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_analysis_profiles_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
    model_service: openai_fast
    prompt_ref: ""
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_analysis_profiles_config(config_path)

    assert "prompt_ref" in str(exc_info.value)


def test_rejects_analysis_profile_with_blank_output_schema(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_analysis_profiles_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
    model_service: openai_fast
    output_schema: ""
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_analysis_profiles_config(config_path)

    assert "output_schema" in str(exc_info.value)
