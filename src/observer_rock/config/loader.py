from pathlib import Path

import yaml

from observer_rock.config.models import (
    AnalysisProfilesConfig,
    ConfigValidationError,
    MonitorsConfig,
    ServicesConfig,
)


def load_services_config(
    path: Path,
    env: dict[str, str] | None = None,
) -> ServicesConfig:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"Invalid YAML in services config {path}: {exc}") from exc
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ConfigValidationError("services config must contain a mapping at the document root")
    resolved_payload = _resolve_service_secrets(payload, env=env)
    return ServicesConfig.validate_payload(resolved_payload)


def load_analysis_profiles_config(path: Path) -> AnalysisProfilesConfig:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigValidationError(
            f"Invalid YAML in analysis profiles config {path}: {exc}"
        ) from exc
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ConfigValidationError(
            "analysis profiles config must contain a mapping at the document root"
        )
    return AnalysisProfilesConfig.validate_payload(payload)


def load_monitors_config(path: Path) -> MonitorsConfig:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"Invalid YAML in monitors config {path}: {exc}") from exc
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ConfigValidationError("monitors config must contain a mapping at the document root")
    return MonitorsConfig.validate_payload(payload)


def _resolve_service_secrets(
    payload: dict[str, object],
    env: dict[str, str] | None,
) -> dict[str, object]:
    if env is None:
        return payload

    services = payload.get("services")
    if not isinstance(services, dict):
        return payload

    resolved_services: dict[str, object] = {}
    for service_name, service_payload in services.items():
        if not isinstance(service_payload, dict):
            resolved_services[service_name] = service_payload
            continue
        resolved_service = dict(service_payload)
        token_env = resolved_service.get("token_env")
        if isinstance(token_env, str):
            token = env.get(token_env)
            if token is None:
                raise ConfigValidationError(f"missing required environment variable: {token_env}")
            resolved_service["token"] = token
        resolved_services[service_name] = resolved_service

    resolved_payload = dict(payload)
    resolved_payload["services"] = resolved_services
    return resolved_payload
