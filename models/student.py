from dataclasses import dataclass


@dataclass(slots=True)
class Student:
    id: int
    roll: str
    first_name: str
    last_name: str
