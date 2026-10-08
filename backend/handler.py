import json

def build_response(status_code, body_dict):
    """Función auxiliar para eliminar la duplicación de código en las respuestas."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict)
    }

def lambda_handler(event, context):
    raw_body = event.get("body")
    
    # Extraemos metadatos de la solicitud HTTP
    request_context = event.get("requestContext", {})
    http_data = request_context.get("http", {})
    http_method = http_data.get("method", "UNKNOWN")
    path = http_data.get("path", "UNKNOWN")
    
    # IDs de rastreo: Correlacionamos el ID de API Gateway con el de Lambda
    apigw_request_id = request_context.get("requestId", "UNKNOWN")
    lambda_request_id = context.aws_request_id
    
    print(f"[{http_method}] {path} | APIGW_ID: {apigw_request_id} | LAMBDA_ID: {lambda_request_id}")

    if not raw_body:
        return build_response(400, {"error": "El cuerpo de la solicitud está vacío."})

    try:
        body_data = json.loads(raw_body)
    except json.JSONDecodeError:
        return build_response(400, {"error": "JSON inválido."})

    # json.loads también acepta listas, strings y números; esperamos un objeto JSON
    if not isinstance(body_data, dict):
        return build_response(400, {"error": "El body debe ser un objeto JSON."})

    name = body_data.get("name")
    if not name or str(name).strip() == "":
        return build_response(400, {"error": "El nombre no puede estar vacío o ausente."})

    return build_response(200, {"message": f"Hola, {name}!"})
