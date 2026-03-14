from pathlib import Path

import pytest


def write_services_config(workspace: Path, contents: str) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    config_path = workspace / "services.yml"
    config_path.write_text(contents, encoding="utf-8")
    return config_path


def write_analysis_profiles_config(workspace: Path, contents: str) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    config_path = workspace / "analysis_profiles.yml"
    config_path.write_text(contents, encoding="utf-8")
    return config_path


def write_monitors_config(workspace: Path, contents: str) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    config_path = workspace / "monitors.yml"
    config_path.write_text(contents, encoding="utf-8")
    return config_path


def test_loads_workspace_from_services_file_without_optional_configs(tmp_path: Path) -> None:
    from observer_rock.config.workspace import WorkspaceConfig, load_workspace_config

    write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    token_env: DISCORD_TOKEN
    channel_id: "12345"
""".strip(),
    )

    workspace = load_workspace_config(tmp_path)

    assert isinstance(workspace, WorkspaceConfig)
    assert workspace.root == tmp_path
    assert set(workspace.services.services) == {"discord_alerts"}
    assert workspace.services.services["discord_alerts"].plugin == "discord"


def test_raises_clear_error_when_services_file_is_missing(tmp_path: Path) -> None:
    from observer_rock.config.workspace import load_workspace_config

    with pytest.raises(ValueError, match=r"services\.yml"):
        load_workspace_config(tmp_path)


def test_loads_workspace_with_analysis_profiles_when_file_exists(tmp_path: Path) -> None:
    from observer_rock.config.workspace import load_workspace_config

    write_services_config(
        tmp_path,
        """
services:
  openai_fast:
    plugin: openai
""".strip(),
    )
    write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
    model_service: openai_fast
""".strip(),
    )

    workspace = load_workspace_config(tmp_path)

    assert workspace.analysis_profiles is not None
    assert set(workspace.analysis_profiles.analysis_profiles) == {"street_mentions_v1"}
    assert (
        workspace.analysis_profiles.analysis_profiles["street_mentions_v1"].model_service
        == "openai_fast"
    )


def test_raises_clear_error_when_analysis_profile_references_missing_model_service(
    tmp_path: Path,
) -> None:
    from observer_rock.config.workspace import load_workspace_config

    write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    channel_id: "12345"
""".strip(),
    )
    write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  street_mentions_v1:
    plugin: llm_extract
    model_service: openai_fast
""".strip(),
    )

    with pytest.raises(ValueError, match=r"openai_fast"):
        load_workspace_config(tmp_path)


def test_loads_workspace_with_monitors_when_file_exists(tmp_path: Path) -> None:
    from observer_rock.config.workspace import load_workspace_config

    write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    channel_id: "12345"
""".strip(),
    )
    write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
""".strip(),
    )

    workspace = load_workspace_config(tmp_path)

    assert workspace.monitors is not None
    assert len(workspace.monitors.monitors) == 1
    assert workspace.monitors.monitors[0].source.plugin == "reddit"


def test_loads_workspace_with_monitors_without_analyses_when_analysis_profiles_file_is_absent(
    tmp_path: Path,
) -> None:
    from observer_rock.config.workspace import load_workspace_config

    write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    channel_id: "12345"
""".strip(),
    )
    write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
""".strip(),
    )

    workspace = load_workspace_config(tmp_path)

    assert workspace.analysis_profiles is None
    assert workspace.monitors is not None
    assert len(workspace.monitors.monitors) == 1
    assert workspace.monitors.monitors[0].id == "reddit-wallstreetbets"


def test_load_workspace_forwards_env_to_service_secret_resolution(tmp_path: Path) -> None:
    from observer_rock.config.workspace import load_workspace_config

    write_services_config(
        tmp_path,
        """
services:
  openai_fast:
    plugin: openai
    token_env: OPENAI_API_KEY
""".strip(),
    )

    workspace = load_workspace_config(tmp_path, env={"OPENAI_API_KEY": "resolved-token"})

    service = workspace.services.services["openai_fast"]
    assert service.token_env == "OPENAI_API_KEY"
    assert service.token == "resolved-token"


def test_raises_clear_error_when_monitor_references_missing_analysis_profile(
    tmp_path: Path,
) -> None:
    from observer_rock.config.workspace import load_workspace_config

    write_services_config(
        tmp_path,
        """
services:
  openai_fast:
    plugin: openai
""".strip(),
    )
    write_analysis_profiles_config(
        tmp_path,
        """
analysis_profiles:
  sentiment:
    plugin: llm_extract
    model_service: openai_fast
""".strip(),
    )
    write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
    analyses:
      - profile: urgency
""".strip(),
    )

    with pytest.raises(ValueError, match=r"urgency"):
        load_workspace_config(tmp_path)


def test_raises_clear_error_when_monitors_declare_analyses_without_analysis_profiles_file(
    tmp_path: Path,
) -> None:
    from observer_rock.config.workspace import load_workspace_config

    write_services_config(
        tmp_path,
        """
services:
  openai_fast:
    plugin: openai
""".strip(),
    )
    write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
    analyses:
      - profile: urgency
""".strip(),
    )

    with pytest.raises(ValueError, match=r"analysis_profiles\.yml"):
        load_workspace_config(tmp_path)
