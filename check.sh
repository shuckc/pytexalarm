set -e
ruff check .
ruff format .
mypy --strict .
pytest .
