from pydantic import BaseModel, Field


class FollowConditionIn(BaseModel):
    age_scope: str = Field(default="both", pattern="^(pediatric|adult|both)$")
    geography: str = "global"
    notify_trials: bool = True
    notify_recruiting_trials_only: bool = False
    notify_papers: bool = True
    notify_regulatory: bool = True
    notify_foundation_news: bool = True
    notify_major_only: bool = False
    frequency: str = Field(default="daily", pattern="^(real_time|daily|weekly|off)$")
    quiet_hours_json: dict = Field(default_factory=dict)
    email_enabled: bool = True
    push_enabled: bool = False
    in_app_enabled: bool = True
