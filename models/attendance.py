from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class AttendanceRecord:
    student_id: int
    attendance_date: date
    status: str
