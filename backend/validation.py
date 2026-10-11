"""Reglas de un control válido. No depende de AWS ni de HTTP: devuelve mensajes de error."""

import uuid

SEVERITY_VALUES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
STATUS_VALUES = {"PASS", "REVIEW", "FAIL"}

FIELD_RULES = {
    "code":        {"required": True,  "max_len": 20},
    "title":       {"required": True,  "max_len": 200},
    "service":     {"required": True,  "max_len": 50},
    "category":    {"required": True,  "max_len": 100},
    "severity":    {"required": True,  "allowed": SEVERITY_VALUES},
    "status":      {"required": False, "allowed": STATUS_VALUES, "default": "REVIEW"},
    "description": {"required": False, "max_len": 2000},
    "remediation": {"required": False, "max_len": 2000},
}


def validate_fields(body, partial=False):
    """Valida tipo, strip, obligatorio, largo y enums. Retorna (cleaned, None) o (None, mensaje_error).
    En modo partial=True ningún campo es obligatorio, no se aplican defaults y solo se devuelven los campos presentes.
    """
    cleaned = {}
    for field, rules in FIELD_RULES.items():
        value = body.get(field)

        if value is None:
            if not partial and rules["required"]:
                return None, f"El campo '{field}' es requerido."
            if not partial:
                cleaned[field] = rules.get("default")
            continue

        if not isinstance(value, str):
            return None, f"El campo '{field}' debe ser un texto."

        value = value.strip()

        if rules["required"] and not value:
            return None, f"El campo '{field}' no puede estar vacío."

        if "max_len" in rules and len(value) > rules["max_len"]:
            return None, f"'{field}' no puede superar los {rules['max_len']} caracteres."

        if "allowed" in rules and value not in rules["allowed"]:
            return None, f"'{field}' debe ser uno de: {', '.join(sorted(rules['allowed']))}."

        cleaned[field] = value

    if partial and not cleaned:
        return None, "No hay campos válidos para actualizar."

    return cleaned, None


def validate_control_id(raw_id):
    """Valida y normaliza un UUID a su forma canónica. Retorna (id, None) o (None, mensaje_error)."""
    if not raw_id:
        return None, "El ID del control es requerido."
    try:
        return str(uuid.UUID(raw_id)), None
    except ValueError:
        return None, "El ID del control debe ser un UUID válido."
