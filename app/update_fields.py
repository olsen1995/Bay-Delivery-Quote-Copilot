from __future__ import annotations

from typing import Any


def include_optional_update_fields(
    body: Any,
    update_kwargs: dict[str, Any],
    field_names: tuple[str, ...],
) -> None:
    """Include optional fields in update kwargs even when explicitly set to null.

    For Optional[...] request fields, parsing often maps both an omitted field and an
    explicit JSON null to `None`. We must distinguish *provided* vs *omitted*.

    Uses Pydantic's field tracking when available:
      - Pydantic v2: body.model_fields_set
      - Pydantic v1: body.__fields_set__
    """
    provided_fields = getattr(body, "model_fields_set", None)
    if provided_fields is None:
        provided_fields = getattr(body, "__fields_set__", set())

    for field_name in field_names:
        if field_name in provided_fields:
            update_kwargs[field_name] = getattr(body, field_name)