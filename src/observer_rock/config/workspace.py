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
    services_path = workspace_root / "services.yml"
    analysis_profiles_path = workspace_root / "analysis_profiles.yml"
    monitors_path = workspace_root / "monitors.yml"

    if not services_path.exists():
        raise ValueError(f"Workspace config is missing required services.yml: {services_path}")

    services = load_services_config(services_path, env=env)
    analysis_profiles = (
        load_analysis_profiles_config(analysis_profiles_path)
        if analysis_profiles_path.exists()
        else None
    )
    monitors = load_monitors_config(monitors_path) if monitors_path.exists() else None

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

    return WorkspaceConfig(
        root=workspace_root,
        services=services,
        analysis_profiles=analysis_profiles,
        monitors=monitors,
    )
