"""Shared response-schema validation helpers for LLM clients."""

from __future__ import annotations


def schema_type_name(schema_type: str) -> str:
    """Normalize schema type names across JSON Schema styles."""
    return schema_type.strip().lower()


def python_type_name(value: object) -> str:
    """Get a stable type name for validation errors."""
    if value is None:
        return 'null'
    return type(value).__name__


def matches_schema_type(value: object, schema_type: str) -> bool:
    """Check whether a value matches a JSON-schema-like type."""
    normalized_type = schema_type_name(schema_type)
    if normalized_type == 'object':
        return isinstance(value, dict)
    if normalized_type == 'array':
        return isinstance(value, list)
    if normalized_type == 'string':
        return isinstance(value, str)
    if normalized_type == 'number':
        return isinstance(value, int | float) and not isinstance(value, bool)
    if normalized_type == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if normalized_type == 'boolean':
        return isinstance(value, bool)
    if normalized_type == 'null':
        return value is None
    return True


def validate_response_against_schema(schema: dict, value: object, path: str = '$') -> None:
    """Validate response JSON against the schema subset used by this app."""
    if value is None and schema.get('nullable') is True:
        return

    schema_type = schema.get('type')
    if isinstance(schema_type, str):
        if not matches_schema_type(value, schema_type):
            normalized_type = schema_type_name(schema_type)
            msg = f'{path}: expected {normalized_type}, got {python_type_name(value)}'
            raise ValueError(msg)
    elif isinstance(schema_type, list):
        if not any(matches_schema_type(value, t) for t in schema_type if isinstance(t, str)):
            expected_types = ','.join(sorted(schema_type_name(t) for t in schema_type if isinstance(t, str)))
            msg = f'{path}: expected one of [{expected_types}], got {python_type_name(value)}'
            raise ValueError(msg)

    if 'enum' in schema and value not in schema['enum']:
        msg = f'{path}: value not in enum {schema["enum"]}'
        raise ValueError(msg)

    normalized_type = schema_type_name(schema_type) if isinstance(schema_type, str) else None
    if normalized_type == 'object' and isinstance(value, dict):
        required_fields = schema.get('required', [])
        for field_name in required_fields:
            if field_name not in value:
                msg = f'{path}: missing required field "{field_name}"'
                raise ValueError(msg)

        properties = schema.get('properties', {})
        additional_properties = schema.get('additionalProperties', True)
        if additional_properties is False:
            unexpected = sorted(key for key in value if key not in properties)
            if unexpected:
                msg = f'{path}: unexpected fields {unexpected}'
                raise ValueError(msg)

        for field_name, field_value in value.items():
            field_schema = properties.get(field_name)
            if field_schema is not None:
                validate_response_against_schema(field_schema, field_value, f'{path}.{field_name}')

    if normalized_type == 'array' and isinstance(value, list):
        min_items = schema.get('minItems')
        max_items = schema.get('maxItems')
        if isinstance(min_items, int) and len(value) < min_items:
            msg = f'{path}: expected at least {min_items} items, got {len(value)}'
            raise ValueError(msg)
        if isinstance(max_items, int) and len(value) > max_items:
            msg = f'{path}: expected at most {max_items} items, got {len(value)}'
            raise ValueError(msg)

        item_schema = schema.get('items')
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                validate_response_against_schema(item_schema, item, f'{path}[{idx}]')

    if normalized_type == 'string' and isinstance(value, str):
        min_length = schema.get('minLength')
        max_length = schema.get('maxLength')
        if isinstance(min_length, int) and len(value) < min_length:
            msg = f'{path}: expected minLength {min_length}, got {len(value)}'
            raise ValueError(msg)
        if isinstance(max_length, int) and len(value) > max_length:
            msg = f'{path}: expected maxLength {max_length}, got {len(value)}'
            raise ValueError(msg)

    if normalized_type in {'number', 'integer'} and isinstance(value, int | float) and not isinstance(value, bool):
        minimum = schema.get('minimum')
        maximum = schema.get('maximum')
        if isinstance(minimum, int | float) and value < minimum:
            msg = f'{path}: expected minimum {minimum}, got {value}'
            raise ValueError(msg)
        if isinstance(maximum, int | float) and value > maximum:
            msg = f'{path}: expected maximum {maximum}, got {value}'
            raise ValueError(msg)
