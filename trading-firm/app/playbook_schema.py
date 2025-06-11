from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


class OKR(BaseModel):
    """Objective and Key Results for a planning period."""

    objective: str = Field(
        ...,
        description="High-level goal for the week, e.g., 'Capitalize on tech sector volatility'",
    )
    key_results: List[str] = Field(
        ..., description="Specific, measurable outcomes to achieve the objective."
    )


class Task(BaseModel):
    """A specific, actionable task derived from an OKR."""

    description: str = Field(
        ...,
        description="What needs to be done, e.g., 'Scan for earnings surprises in NASDAQ 100'",
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Any prerequisite tasks or events."
    )


class CatalystEvent(BaseModel):
    """An external event that could significantly impact the market or a specific asset."""

    type: Literal["CatalystEvent"] = "CatalystEvent"
    event_name: str = Field(
        ...,
        description="Name of the event, e.g., 'CPI Release', 'AAPL Court Case Verdict'",
    )
    ticker: Optional[str] = Field(None, description="Specific ticker affected, if any.")
    event_time_utc: datetime = Field(
        ..., description="The expected date and time of the event in UTC."
    )
    hold_until_utc: Optional[datetime] = Field(
        None,
        description="If set, positions in the ticker should be held until this time.",
    )
    expected_impact: str = Field(
        ..., description="A brief summary of the potential market impact."
    )


class SystemHalt(BaseModel):
    """A signal to halt all new trading activity, usually for risk management."""

    type: Literal["SystemHalt"] = "SystemHalt"
    reason: str = Field(
        ..., description="Reason for the halt, e.g., 'Max notional limit breached.'"
    )


class NewsHeadline(BaseModel):
    """A news headline that is stored in memory for context."""

    type: Literal["NewsHeadline"] = "NewsHeadline"
    headline: str
    source: str
    ticker: Optional[str] = None
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)


class Playbook(BaseModel):
    """The complete strategic plan for a given period."""

    type: Literal["Playbook"] = "Playbook"
    start_date: str
    end_date: str
    okrs: List[OKR]
    tasks: List[Task]


# A union type for all possible messages on the 'playbook' topic
PlaybookMessage = Union[Playbook, CatalystEvent, SystemHalt, NewsHeadline]
