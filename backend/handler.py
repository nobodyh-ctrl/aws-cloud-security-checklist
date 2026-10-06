import json

def lambda_handler(event, context):

    nombre = event.get("name", None)

    print(event)   
    
    if not nombre:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "El nombre no puede estar vacío."})
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": f"Hola, {nombre}"})  
    }
 