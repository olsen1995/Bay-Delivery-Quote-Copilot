from __future__ import annotations

from typing import Any


def include_optional_update_fields(body: Any, update_kwargs: dict[str, Any], field_names: tuple[str, ...]) -> None:
    for field_name in field_names:
        if field_name in body.model_fields_set:
            update_kwargs[field_name] = getattr(body, field_name)
