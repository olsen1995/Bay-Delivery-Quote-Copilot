from __future__ import annotations

from typing import Any


def include_optional_update_fields(body: Any, update_kwargs: dict[str, Any], field_names: tuple[str, ...]) -> None:
    provided_fields = getattr(body, "model_fields_set", None)
    if provided_fields is None:
        provided_fields = getattr(body, "__fields_set__", set())

    for field_name in field_names:
        if field_name in provided_fields:
            update_kwargs[field_name] = getattr(body, field_name)
