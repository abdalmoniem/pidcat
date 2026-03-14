import tomllib

from pathlib import Path
from pyproject_metadata import StandardMetadata

PY_PROJECT_FILE = Path(__file__).parent.parent / "pyproject.toml"


def get_metadata() -> StandardMetadata:
    with open(PY_PROJECT_FILE, "rb") as fd:
        data = tomllib.load(fd)

    return StandardMetadata.from_pyproject(data)
