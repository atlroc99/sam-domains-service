import json

from redis_connection import get_redis_connection


def lambda_handler(event, context):
    conn = get_redis_connection()
    response = {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
    }
    if conn and conn.ping():
        response['body'] = json.dumps({'isConnected': True})
    else:
        response['body'] = json.dumps({'error_msg': 'Unable to connect to redis'})

    return response
