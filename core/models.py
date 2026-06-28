from dataclasses import dataclass, field

@dataclass
class Note:
    id: str
    title: str
    body: str
    metadata: dict = field(default_factory=dict)
