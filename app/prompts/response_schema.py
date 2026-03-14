"""Input-side structured output schema builders for prompts."""

from __future__ import annotations

from typing import Any


def _ordered_string_values(values: list[Any]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        ordered.append(text)
        seen.add(text)
    return ordered


def _categorical_allowed_values(field: dict[str, Any]) -> list[str]:
    return _ordered_string_values(
        [
            *field.get('required_values', []),
            *field.get('suggested_values', []),
        ]
    )


def _field_int(field: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = field.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def build_analysis_response_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON schema for analysis output based on a generated schema."""
    enum_fields = schema.get('enum_fields', [])
    categorical_fields = schema.get('categorical_fields', [])
    scalar_fields = schema.get('scalar_fields', [])
    key_quotes_fields = schema.get('key_quotes_fields', [])
    text_array_fields = schema.get('text_array_fields', [])

    enum_props: dict[str, Any] = {}
    enum_required: list[str] = []
    for field in enum_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        field_schema: dict[str, Any] = {'type': 'STRING'}
        if field.get('nullable') is True:
            field_schema['nullable'] = True
        allowed_values = [str(value) for value in field.get('allowed_values', []) if str(value).strip()]
        if allowed_values:
            field_schema['enum'] = allowed_values
        enum_props[field_name] = field_schema
        if field.get('required') is True:
            enum_required.append(field_name)

    categorical_props: dict[str, Any] = {}
    categorical_required: list[str] = []
    for field in categorical_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        allow_multiple = bool(field.get('allow_multiple', False))
        if allow_multiple:
            field_schema = {
                'type': 'ARRAY',
                'items': {'type': 'STRING'},
            }
            min_items = _field_int(field, 'min_items', 'minItems')
            if min_items is not None:
                field_schema['minItems'] = min_items
        else:
            field_schema = {'type': 'STRING'}
        if field.get('nullable') is True:
            field_schema['nullable'] = True
        value_mode = str(field.get('value_mode', 'closed')).strip().lower()
        allowed_values = _categorical_allowed_values(field) if value_mode == 'closed' else []
        if allowed_values:
            if allow_multiple:
                field_schema['items']['enum'] = allowed_values
            else:
                field_schema['enum'] = allowed_values
        categorical_props[field_name] = field_schema
        if field.get('required') is True:
            categorical_required.append(field_name)

    scalar_props: dict[str, Any] = {}
    scalar_required: list[str] = []
    for field in scalar_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        field_schema: dict[str, Any] = {'type': 'NUMBER'}
        if field.get('nullable') is True:
            field_schema['nullable'] = True
        scale_min = field.get('scale_min')
        if isinstance(scale_min, int | float):
            field_schema['minimum'] = scale_min
        scale_max = field.get('scale_max')
        if isinstance(scale_max, int | float):
            field_schema['maximum'] = scale_max
        scalar_props[field_name] = field_schema
        if field.get('required') is True:
            scalar_required.append(field_name)

    key_quotes_props: dict[str, Any] = {}
    key_quotes_required: list[str] = []
    for field in key_quotes_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        field_schema: dict[str, Any] = {
            'type': 'ARRAY',
            'items': {'type': 'STRING'},
        }
        min_items = field.get('min_items')
        if isinstance(min_items, int):
            field_schema['minItems'] = min_items
        max_quotes = field.get('max_quotes')
        if isinstance(max_quotes, int):
            field_schema['maxItems'] = max_quotes
        if field.get('nullable') is True:
            field_schema['nullable'] = True
        key_quotes_props[field_name] = field_schema
        if field.get('required') is True:
            key_quotes_required.append(field_name)

    text_array_props: dict[str, Any] = {}
    text_array_required: list[str] = []
    for field in text_array_fields:
        field_name = field.get('field_name', '').strip()
        if not field_name:
            continue
        field_schema: dict[str, Any] = {
            'type': 'ARRAY',
            'items': {'type': 'STRING'},
        }
        min_items = field.get('min_items')
        if isinstance(min_items, int):
            field_schema['minItems'] = min_items
        max_items = field.get('max_items')
        if isinstance(max_items, int):
            field_schema['maxItems'] = max_items
        if field.get('nullable') is True:
            field_schema['nullable'] = True
        text_array_props[field_name] = field_schema
        if field.get('required') is True:
            text_array_required.append(field_name)

    return {
        'type': 'OBJECT',
        'properties': {
            'records': {
                'type': 'ARRAY',
                'items': {
                    'type': 'OBJECT',
                    'properties': {
                        'record_id': {'type': 'STRING'},
                        'enum_fields': {
                            'type': 'OBJECT',
                            'properties': enum_props,
                            'required': enum_required,
                            'additionalProperties': False,
                        },
                        'categorical_fields': {
                            'type': 'OBJECT',
                            'properties': categorical_props,
                            'required': categorical_required,
                            'additionalProperties': False,
                        },
                        'scalar_fields': {
                            'type': 'OBJECT',
                            'properties': scalar_props,
                            'required': scalar_required,
                            'additionalProperties': False,
                        },
                        'key_quotes_fields': {
                            'type': 'OBJECT',
                            'properties': key_quotes_props,
                            'required': key_quotes_required,
                            'additionalProperties': False,
                        },
                        'text_array_fields': {
                            'type': 'OBJECT',
                            'properties': text_array_props,
                            'required': text_array_required,
                            'additionalProperties': False,
                        },
                    },
                    'required': [
                        'record_id',
                        'enum_fields',
                        'categorical_fields',
                        'scalar_fields',
                        'key_quotes_fields',
                        'text_array_fields',
                    ],
                    'additionalProperties': False,
                },
            }
        },
        'required': ['records'],
        'additionalProperties': False,
    }
