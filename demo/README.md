# AIM Demo Data

This directory contains scripts and data for seeding the AIM application with realistic demo content.

## Quick Start

```bash
from the project root:
python demo/seed_demo_data.py
```

This will create:
- **35 students** across 4 batches (CS-2026, CS-2025, EE-2026, ME-2026)
- **4 teacher users** with the teacher role
- **30 days of attendance data** (weekdays only, ~78% present / 14% absent / 8% leave)
- **System settings** configured for a university environment

## Login Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `gagan` | `admin123` |
| Admin | `admin` | `admin123` |
| Teacher | `prof_sharma` | `Teacher@123` |
| Teacher | `prof_patel` | `Teacher@123` |
| Teacher | `prof_kumar` | `Teacher@123` |
| Teacher | `prof_reddy` | `Teacher@123` |

## Options

```bash
python demo/seed_demo_data.py              # Seed everything
python demo/seed_demo_data.py --students   # Seed only students
python demo/seed_demo_data.py --attendance # Seed only attendance (requires students)
python demo/seed_demo_data.py --users      # Seed only teacher users
python demo/seed_demo_data.py --reset      # Clear all demo data first
python demo/seed_demo_data.py --reset --students  # Reset then re-seed
```

## Sample CSV Files

The `database/` directory contains sample CSV files for import:
- `database/sample_students.csv` — Sample student import format
- `database/sample_attendance.csv` — Sample attendance import format
