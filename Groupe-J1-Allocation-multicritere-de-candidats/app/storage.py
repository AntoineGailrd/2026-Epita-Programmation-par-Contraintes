from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Generic, List, TypeVar
from uuid import uuid4

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class JsonRepository(Generic[T]):
    def __init__(self, path: Path, model_cls: type[T]) -> None:
        self.path = path
        self.model_cls = model_cls
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def list(self) -> List[T]:
        raw_items = json.loads(self.path.read_text(encoding="utf-8"))
        return [self.model_cls.model_validate(item) for item in raw_items]

    def create(self, payload: BaseModel) -> T:
        raw_items = json.loads(self.path.read_text(encoding="utf-8"))
        item = payload.model_dump()
        item["id"] = uuid4().hex
        item["created_at"] = datetime.now(timezone.utc).isoformat()
        raw_items.append(item)
        self.path.write_text(json.dumps(raw_items, indent=2, ensure_ascii=True), encoding="utf-8")
        return self.model_cls.model_validate(item)
