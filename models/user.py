from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class User:
    id: int
    username: str
    email: str | None = None
    role_name: str | None = None
    theme: str = "light"
    records_per_page: int = 10
    created_at: datetime | None = None
