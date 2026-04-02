from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(slots=True)
class Variant:
    mutation_type: str
    expected_gain: float
    budget_limit: float
    risk_level: str
    status: str = "draft"
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
