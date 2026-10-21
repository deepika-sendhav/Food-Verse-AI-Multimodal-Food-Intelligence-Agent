import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
DEMO_DATA_DIR = Path(__file__).resolve().parents[1] / "demo_data"
DEMO_WARNING = "Demo mode: sample data only. No real analysis was performed."


def load_demo_response(name: str, schema: type[T]) -> T:
    path = DEMO_DATA_DIR / f"{name}.json"
    with path.open(encoding="utf-8") as demo_file:
        payload = json.load(demo_file)
    payload["demo"] = True
    payload["demo_warning"] = DEMO_WARNING
    return schema.model_validate(payload)


def load_demo_payload(name: str, schema: type[T]) -> dict[str, object]:
    return load_demo_response(name, schema).model_dump(mode="json")
