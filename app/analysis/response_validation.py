"""Validation utilities for structured analysis responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationFailure:
    """Structured validation failure details for batch retries/logging."""

    category: str
    message: str


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
            min_items = field.get('min_items')
            if isinstance(min_items, int):
                field_schema['minItems'] = min_items
            max_items = field.get('max_items')
            if isinstance(max_items, int):
                field_schema['maxItems'] = max_items
        else:
            field_schema = {'type': 'STRING'}
        if field.get('nullable') is True:
            field_schema['nullable'] = True
        suggested_values = [str(value) for value in field.get('suggested_values', []) if str(value).strip()]
        if suggested_values:
            if allow_multiple:
                field_schema['items']['enum'] = suggested_values
            else:
                field_schema['enum'] = suggested_values
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


def _failure(category: str, message: str) -> ValidationFailure:
    return ValidationFailure(category=category, message=message)


def _validate_field_object(
    group_name: str,
    payload: object,
    schema_fields: list[dict[str, Any]],
) -> ValidationFailure | None:
    if not isinstance(payload, dict):
        return _failure('wrong_types', f'{group_name} must be an object')

    expected_field_names = {
        str(field.get('field_name', '')).strip()
        for field in schema_fields
        if str(field.get('field_name', '')).strip()
    }
    unexpected = sorted(key for key in payload if key not in expected_field_names)
    if unexpected:
        return _failure('unexpected_keys', f'{group_name} contains unexpected keys: {unexpected}')

    for field in schema_fields:
        field_name = str(field.get('field_name', '')).strip()
        if not field_name:
            continue
        required = bool(field.get('required', False))
        nullable = bool(field.get('nullable', True))
        has_key = field_name in payload
        value = payload.get(field_name)

        if required and (not has_key or (value is None and not nullable)):
            return _failure('missing_required_fields', f'{group_name}.{field_name} is required')
        if not has_key or value is None:
            continue

        if group_name == 'enum_fields':
            if not isinstance(value, str):
                return _failure('wrong_types', f'{group_name}.{field_name} must be a string')
            allowed_values = [str(v) for v in field.get('allowed_values', []) if str(v).strip()]
            if allowed_values and value not in allowed_values:
                return _failure('invalid_enum_values', f'{group_name}.{field_name} has invalid value: {value}')
            continue

        if group_name == 'categorical_fields':
            allow_multiple = bool(field.get('allow_multiple', False))
            suggested_values = {str(v) for v in field.get('suggested_values', []) if str(v).strip()}
            if allow_multiple:
                if not isinstance(value, list):
                    return _failure('wrong_types', f'{group_name}.{field_name} must be an array')
                if not all(isinstance(item, str) for item in value):
                    return _failure('wrong_types', f'{group_name}.{field_name} items must be strings')
                if suggested_values:
                    invalid = [item for item in value if item not in suggested_values]
                    if invalid:
                        return _failure(
                            'invalid_enum_values',
                            f'{group_name}.{field_name} has invalid values: {invalid}',
                        )
            else:
                if not isinstance(value, str):
                    return _failure('wrong_types', f'{group_name}.{field_name} must be a string')
                if suggested_values and value not in suggested_values:
                    return _failure('invalid_enum_values', f'{group_name}.{field_name} has invalid value: {value}')
            continue

        if group_name == 'scalar_fields':
            if not isinstance(value, int | float) or isinstance(value, bool):
                return _failure('wrong_types', f'{group_name}.{field_name} must be numeric')
            scale_min = field.get('scale_min')
            if isinstance(scale_min, int | float) and value < scale_min:
                return _failure('wrong_types', f'{group_name}.{field_name} must be >= {scale_min}')
            scale_max = field.get('scale_max')
            if isinstance(scale_max, int | float) and value > scale_max:
                return _failure('wrong_types', f'{group_name}.{field_name} must be <= {scale_max}')
            continue

        if group_name in {'key_quotes_fields', 'text_array_fields'}:
            if not isinstance(value, list):
                return _failure('wrong_types', f'{group_name}.{field_name} must be an array')
            if not all(isinstance(item, str) for item in value):
                return _failure('wrong_types', f'{group_name}.{field_name} items must be strings')
            min_items = field.get('min_items')
            if isinstance(min_items, int) and len(value) < min_items:
                return _failure('wrong_types', f'{group_name}.{field_name} must contain at least {min_items} values')
            max_items = field.get('max_items')
            max_quotes = field.get('max_quotes')
            hard_max = max_items if isinstance(max_items, int) else max_quotes
            if isinstance(hard_max, int) and len(value) > hard_max:
                return _failure('wrong_types', f'{group_name}.{field_name} must contain at most {hard_max} values')

    return None


def validate_analysis_payload(
    response_data: object,
    schema: dict[str, Any],
) -> ValidationFailure | None:
    """Validate parsed analysis response payload against source schema constraints."""
    if not isinstance(response_data, dict):
        return _failure('wrong_types', 'response payload must be an object')

    unexpected_top = sorted(key for key in response_data if key != 'records')
    if unexpected_top:
        return _failure('unexpected_keys', f'top-level unexpected keys: {unexpected_top}')

    records = response_data.get('records')
    if not isinstance(records, list):
        return _failure('wrong_types', 'records must be an array')

    allowed_record_keys = {
        'record_id',
        'enum_fields',
        'categorical_fields',
        'scalar_fields',
        'key_quotes_fields',
        'text_array_fields',
    }
    required_record_keys = [
        'record_id',
        'enum_fields',
        'categorical_fields',
        'scalar_fields',
        'key_quotes_fields',
        'text_array_fields',
    ]

    enum_fields = schema.get('enum_fields', [])
    categorical_fields = schema.get('categorical_fields', [])
    scalar_fields = schema.get('scalar_fields', [])
    key_quotes_fields = schema.get('key_quotes_fields', [])
    text_array_fields = schema.get('text_array_fields', [])

    for idx, record in enumerate(records):
        path = f'records[{idx}]'
        if not isinstance(record, dict):
            return _failure('wrong_types', f'{path} must be an object')

        unexpected_record_keys = sorted(key for key in record if key not in allowed_record_keys)
        if unexpected_record_keys:
            return _failure('unexpected_keys', f'{path} has unexpected keys: {unexpected_record_keys}')

        for required_key in required_record_keys:
            if required_key not in record:
                return _failure('missing_required_fields', f'{path}.{required_key} is required')

        if not isinstance(record.get('record_id'), str):
            return _failure('wrong_types', f'{path}.record_id must be a string')

        checks = [
            ('enum_fields', enum_fields),
            ('categorical_fields', categorical_fields),
            ('scalar_fields', scalar_fields),
            ('key_quotes_fields', key_quotes_fields),
            ('text_array_fields', text_array_fields),
        ]
        for group_name, group_schema in checks:
            failure = _validate_field_object(group_name, record.get(group_name), group_schema)
            if failure is not None:
                return _failure(failure.category, f'{path}: {failure.message}')

    return None
