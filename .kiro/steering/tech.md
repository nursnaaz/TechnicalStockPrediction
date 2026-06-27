# Technology Stack

## Language

**Python** - Primary development language for the project

## Dependencies & Package Management

The project uses standard Python packaging. Supported package managers include:
- pip
- pipenv
- poetry
- uv
- pdm

## Environment Management

Virtual environments should be used for dependency isolation:
- `.venv/` or `venv/` directories are gitignored
- Environment variables stored in `.env` files (gitignored)

## Development Tools

Common Python development tools are supported:
- **Testing**: pytest, coverage
- **Linting**: ruff, mypy
- **Notebooks**: Jupyter notebooks (`.ipynb_checkpoints` gitignored)
- **IDE**: VS Code and PyCharm configurations supported

## Common Commands

Until dependencies are established, standard Python commands apply:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies (when requirements.txt exists)
pip install -r requirements.txt

# Run Python scripts
python <script_name>.py

# Run tests (when test framework is set up)
pytest
pytest --cov=. --cov-report=html

# Linting (when configured)
ruff check .
mypy .
```

## Code Quality

- Type checking with mypy is supported
- Ruff for fast linting and formatting
- Coverage reporting for tests
