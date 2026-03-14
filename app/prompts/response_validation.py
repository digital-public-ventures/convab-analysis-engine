"""Output-side validation for structured analysis payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationFailure:
    """Structured validation failure details for batch retries/logging."""

    category: str
    message: str


def _failure(category: str, message: str) -> ValidationFailure:
    return ValidationFailure(category=category, message=message)


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


def _validate_field_object(
    group_name: str,
    payload: object,
    schema_fields: list[dict[str, Any]],
) -> ValidationFailure | None:
    if not isinstance(payload, dict):
        return _failure('wrong_types', f'{group_name} must be an object')

    expected_field_names = {
        str(field.get('field_name', '')).strip() for field in schema_fields if str(field.get('field_name', '')).strip()
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
            value_mode = str(field.get('value_mode', 'closed')).strip().lower()
            allowed_values = set(_categorical_allowed_values(field)) if value_mode == 'closed' else set()
            if allow_multiple:
                if not isinstance(value, list):
                    return _failure('wrong_types', f'{group_name}.{field_name} must be an array')
                if not all(isinstance(item, str) for item in value):
                    return _failure('wrong_types', f'{group_name}.{field_name} items must be strings')
                min_items = _field_int(field, 'min_items', 'minItems')
                if min_items is not None and len(value) < min_items:
                    return _failure(
                        'wrong_types',
                        f'{group_name}.{field_name} must contain at least {min_items} values',
                    )
                max_items = _field_int(field, 'max_items', 'maxItems')
                if max_items is not None and len(value) > max_items:
                    return _failure(
                        'wrong_types',
                        f'{group_name}.{field_name} must contain at most {max_items} values',
                    )
                if allowed_values:
                    invalid = [item for item in value if item not in allowed_values]
                    if invalid:
                        return _failure(
                            'invalid_enum_values',
                            f'{group_name}.{field_name} has invalid values: {invalid}',
                        )
            else:
                if not isinstance(value, str):
                    return _failure('wrong_types', f'{group_name}.{field_name} must be a string')
                if allowed_values and value not in allowed_values:
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
