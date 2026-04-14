from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ConfigValidationError(ValueError):
    """Raised when workspace configuration does not match the expected schema."""


class ServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: str = Field(min_length=1)
    token_env: str | None = Field(default=None, min_length=1)
    token: str | None = None
    channel_id: str | None = Field(default=None, min_length=1)
    path: str | None = Field(default=None, min_length=1)
    retries: int | None = Field(default=None, ge=0)


class ServicesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin_import_paths: list[str] = Field(default_factory=list)
    services: dict[str, ServiceConfig]

    @classmethod
    def validate_payload(cls, payload: object) -> "ServicesConfig":
        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise ConfigValidationError(str(exc)) from exc


class AnalysisProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: str = Field(min_length=1)
    model_service: str = Field(min_length=1)
    prompt_ref: str | None = Field(default=None, min_length=1)
    output_schema: str | None = Field(default=None, min_length=1)
    retries: int | None = Field(default=None, ge=0)


class AnalysisProfilesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_profiles: dict[str, AnalysisProfileConfig]

    @classmethod
    def validate_payload(cls, payload: object) -> "AnalysisProfilesConfig":
        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise ConfigValidationError(str(exc)) from exc


class MonitorSourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plugin: str = Field(min_length=1)
    config: dict[str, object] = Field(default_factory=dict)


class MonitorAnalysisConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str = Field(min_length=1)


class MonitorOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str = Field(min_length=1)
    renderer: str = Field(min_length=1)
    service: str = Field(min_length=1)


class MonitorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    schedule: str = Field(min_length=1)
    source: MonitorSourceConfig
    analyses: list[MonitorAnalysisConfig] | None = None
    outputs: list[MonitorOutputConfig] | None = None

    @model_validator(mode="after")
    def validate_unique_analysis_profiles(self) -> "MonitorConfig":
        if self.analyses is None:
            analyses = []
        else:
            analyses = self.analyses

        seen_profiles: set[str] = set()
        for analysis in analyses:
            if analysis.profile in seen_profiles:
                raise ValueError(f"duplicate analysis profile: {analysis.profile}")
            seen_profiles.add(analysis.profile)

        seen_output_pairs: set[tuple[str, str]] = set()
        for output in self.outputs or []:
            if output.profile not in seen_profiles:
                raise ValueError(
                    f"output references unknown monitor analysis profile: {output.profile}"
                )
            output_pair = (output.profile, output.service)
            if output_pair in seen_output_pairs:
                raise ValueError(
                    "duplicate output target for analysis profile "
                    f"{output.profile} and service {output.service}"
                )
            seen_output_pairs.add(output_pair)
        return self


class MonitorsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monitors: list[MonitorConfig]

    @model_validator(mode="after")
    def validate_unique_monitor_ids(self) -> "MonitorsConfig":
        seen_ids: set[str] = set()
        for monitor in self.monitors:
            if monitor.id in seen_ids:
                raise ValueError(f"duplicate monitor id: {monitor.id}")
            seen_ids.add(monitor.id)
        return self

    @classmethod
    def validate_payload(cls, payload: object) -> "MonitorsConfig":
        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise ConfigValidationError(str(exc)) from exc
