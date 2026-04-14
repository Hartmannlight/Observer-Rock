from pathlib import Path

import pytest


def write_services_config(workspace: Path, contents: str) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    config_path = workspace / "services.yml"
    config_path.write_text(contents, encoding="utf-8")
    return config_path


def test_loads_minimal_service_configuration(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_services_config

    config_path = write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    token_env: DISCORD_TOKEN
    channel_id: "12345"
""".strip(),
    )

    config = load_services_config(config_path)

    assert set(config.services) == {"discord_alerts"}
    service = config.services["discord_alerts"]
    assert service.plugin == "discord"
    assert service.token_env == "DISCORD_TOKEN"
    assert service.channel_id == "12345"


def test_rejects_service_without_plugin(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_services_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    channel_id: "12345"
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_services_config(config_path)

    assert "plugin" in str(exc_info.value)


def test_resolves_service_secret_from_environment(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_services_config

    config_path = write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    token_env: DISCORD_TOKEN
    channel_id: "12345"
""".strip(),
    )

    config = load_services_config(config_path, env={"DISCORD_TOKEN": "secret-token"})

    assert config.services["discord_alerts"].token == "secret-token"


def test_fails_when_required_secret_is_missing(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_services_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    token_env: DISCORD_TOKEN
    channel_id: "12345"
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_services_config(config_path, env={})

    assert "DISCORD_TOKEN" in str(exc_info.value)


def test_rejects_service_with_blank_plugin(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_services_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: ""
    channel_id: "12345"
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_services_config(config_path)

    assert "plugin" in str(exc_info.value)


def test_rejects_service_with_blank_token_env(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_services_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    token_env: ""
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_services_config(config_path)

    assert "token_env" in str(exc_info.value)


def test_rejects_service_with_blank_channel_id(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_services_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    channel_id: ""
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_services_config(config_path)

    assert "channel_id" in str(exc_info.value)


def test_rejects_service_with_negative_retries(tmp_path: Path) -> None:
    from observer_rock.config.loader import load_services_config
    from observer_rock.config.models import ConfigValidationError

    config_path = write_services_config(
        tmp_path,
        """
services:
  discord_alerts:
    plugin: discord
    retries: -1
""".strip(),
    )

    with pytest.raises(ConfigValidationError) as exc_info:
        load_services_config(config_path)

    assert "retries" in str(exc_info.value)
