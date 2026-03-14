from pathlib import Path

import pytest


def write_monitors_config(workspace: Path, contents: str) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    config_path = workspace / "monitors.yml"
    config_path.write_text(contents, encoding="utf-8")
    return config_path


def test_loads_minimal_monitors_configuration(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import MonitorConfig, MonitorsConfig, MonitorSourceConfig

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
""".strip(),
    )

    config = load_monitors_config(config_path)

    assert isinstance(config, MonitorsConfig)
    assert len(config.monitors) == 1
    monitor = config.monitors[0]
    assert isinstance(monitor, MonitorConfig)
    assert monitor.id == "reddit-wallstreetbets"
    assert monitor.schedule == "*/5 * * * *"
    assert isinstance(monitor.source, MonitorSourceConfig)
    assert monitor.source.plugin == "reddit"


def test_rejects_monitor_without_source_plugin(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source: {}
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "plugin" in str(exc_info.value)


def test_rejects_monitors_document_without_list_root(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  id: reddit-wallstreetbets
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "monitors" in str(exc_info.value)


def test_loads_monitor_with_analyses(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
    analyses:
      - profile: sentiment
      - profile: urgency
""".strip(),
    )

    config = load_monitors_config(config_path)

    monitor = config.monitors[0]
    assert monitor.analyses is not None
    assert [analysis.profile for analysis in monitor.analyses] == ["sentiment", "urgency"]


def test_rejects_monitor_analysis_without_profile(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
    analyses:
      - {}
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "profile" in str(exc_info.value)


def test_rejects_duplicate_monitor_analysis_profiles(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
    analyses:
      - profile: sentiment
      - profile: sentiment
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "sentiment" in str(exc_info.value)


def test_rejects_duplicate_monitor_ids(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: duplicate-monitor
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
  - id: duplicate-monitor
    schedule: "*/10 * * * *"
    source:
      plugin: hackernews
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "duplicate-monitor" in str(exc_info.value)


def test_rejects_monitor_with_blank_id(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: ""
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "id" in str(exc_info.value)


def test_rejects_monitor_with_blank_schedule(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: ""
    source:
      plugin: reddit
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "schedule" in str(exc_info.value)


def test_rejects_monitor_with_blank_source_plugin(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: ""
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "plugin" in str(exc_info.value)


def test_rejects_monitor_analysis_with_blank_profile(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_monitors_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_monitors_config(
        tmp_path,
        """
monitors:
  - id: reddit-wallstreetbets
    schedule: "*/5 * * * *"
    source:
      plugin: reddit
    analyses:
      - profile: ""
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_monitors_config(config_path)

    assert "profile" in str(exc_info.value)
