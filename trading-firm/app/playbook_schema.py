from datetime import datetime
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

class OKR(BaseModel):
    objective: str
    key_results: List[str]

class Task(BaseModel):
    description: str
    dependencies: List[str] = []

class CatalystEvent(BaseModel):
    type: Literal["CatalystEvent"] = "CatalystEvent"
    event_name: str
    ticker: Optional[str] = None
    event_time_utc: datetime
    hold_until_utc: Optional[datetime] = None
    expected_impact: str

class SystemHalt(BaseModel):
    type: Literal["SystemHalt"] = "SystemHalt"
    reason: str

class NewsHeadline(BaseModel):
    type: Literal["NewsHeadline"] = "NewsHeadline"
    headline: str
    source: str
    ticker: Optional[str] = None
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)

class Playbook(BaseModel):
    type: Literal["Playbook"] = "Playbook"
    start_date: str
    end_date: str
    okrs: List[OKR]
    tasks: List[Task]

PlaybookMessage = Union[Playbook, CatalystEvent, SystemHalt, NewsHeadline]
