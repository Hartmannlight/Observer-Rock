from dataclasses import dataclass
from pathlib import Path

from observer_rock.config.loader import (
    load_analysis_profiles_config,
    load_monitors_config,
    load_services_config,
)
from observer_rock.config.models import AnalysisProfilesConfig, MonitorsConfig, ServicesConfig


@dataclass(frozen=True, slots=True)
class WorkspaceConfig:
    root: Path
    services: ServicesConfig
    analysis_profiles: AnalysisProfilesConfig | None = None
    monitors: MonitorsConfig | None = None


def load_workspace_config(
    workspace_root: Path,
    env: dict[str, str] | None = None,
) -> WorkspaceConfig:
    workspace_root = workspace_root.resolve()
    services_path = workspace_root / "services.yml"
    analysis_profiles_path = workspace_root / "analysis_profiles.yml"
    monitors_path = workspace_root / "monitors.yml"

    if not services_path.exists():
        raise ValueError(f"Workspace config is missing required services.yml: {services_path}")

    services = _resolve_relative_paths_in_services(
        load_services_config(services_path, env=env),
        workspace_root=workspace_root,
    )
    analysis_profiles = (
        load_analysis_profiles_config(analysis_profiles_path)
        if analysis_profiles_path.exists()
        else None
    )
    monitors = (
        _resolve_relative_paths_in_monitors(
            load_monitors_config(monitors_path),
            workspace_root=workspace_root,
        )
        if monitors_path.exists()
        else None
    )

    if analysis_profiles is not None:
        available_services = set(services.services)
        for profile_name, profile in analysis_profiles.analysis_profiles.items():
            if profile.model_service not in available_services:
                raise ValueError(
                    f"Analysis profile '{profile_name}' in {analysis_profiles_path.name} "
                    f"references missing service "
                    f"'{profile.model_service}'"
                )

    if monitors is not None:
        available_profiles = (
            set(analysis_profiles.analysis_profiles) if analysis_profiles is not None else None
        )
        for monitor in monitors.monitors:
            for analysis in monitor.analyses or []:
                if available_profiles is None:
                    raise ValueError(
                        "Workspace config requires analysis_profiles.yml "
                        "when monitors declare analyses: "
                        f"{analysis_profiles_path}"
                    )
                if analysis.profile not in available_profiles:
                    raise ValueError(
                        f"Monitor '{monitor.id}' references missing analysis profile "
                        f"'{analysis.profile}'"
                    )
            for output in monitor.outputs or []:
                if output.service not in services.services:
                    raise ValueError(
                        f"Monitor '{monitor.id}' references missing service '{output.service}'"
                    )

    return WorkspaceConfig(
        root=workspace_root,
        services=services,
        analysis_profiles=analysis_profiles,
        monitors=monitors,
    )


def _resolve_relative_paths_in_services(
    services: ServicesConfig,
    *,
    workspace_root: Path,
) -> ServicesConfig:
    resolved_services = {}
    for service_name, service in services.services.items():
        resolved_path = service.path
        if resolved_path is not None:
            path = Path(resolved_path)
            if not path.is_absolute():
                resolved_path = str((workspace_root / path).resolve())
        resolved_services[service_name] = service.model_copy(update={"path": resolved_path})

    return services.model_copy(update={"services": resolved_services})


def _resolve_relative_paths_in_monitors(
    monitors: MonitorsConfig,
    *,
    workspace_root: Path,
) -> MonitorsConfig:
    resolved_monitors = []
    for monitor in monitors.monitors:
        source_config = dict(monitor.source.config)
        for path_key in ("path", "index_path"):
            configured_path = source_config.get(path_key)
            if not isinstance(configured_path, str):
                continue
            path = Path(configured_path)
            if not path.is_absolute():
                source_config[path_key] = str((workspace_root / path).resolve())
        resolved_monitors.append(
            monitor.model_copy(
                update={"source": monitor.source.model_copy(update={"config": source_config})}
            )
        )

    return monitors.model_copy(update={"monitors": resolved_monitors})
