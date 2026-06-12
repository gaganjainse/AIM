# Contributing to AIM

## Getting Started

1. Fork the repo and create a branch: `git checkout -b feature/your-change`
2. Set up the dev environment (see README Setup section)
3. Make your changes, keeping each commit focused
4. Run tests: `python -m pytest tests/ -v`
5. Open a pull request against `main`

## Code Style

- Python: follow PEP 8; keep functions under ~40 lines
- All functions must have type hints
- Routes stay thin — logic belongs in `services/`
- SQL stays in `repositories/`, never inline in routes
- Use `current_app.logger` instead of `print()`

## Security Requirements

- All new routes must have `@login_required` and `@permission_required` as appropriate
- All user inputs must be validated
- All database queries must use parameterized `%s` placeholders
- Passwords must use Argon2id hashing (via `_hash_password()` helper)

## Testing Requirements

- All new features must have corresponding tests
- Tests must pass: `python -m pytest tests/ -v`

## Branch Naming

- `feature/` — new functionality
- `fix/` — bug fixes
- `docs/` — documentation only
- `refactor/` — no behaviour change
- `security/` — security fixes
