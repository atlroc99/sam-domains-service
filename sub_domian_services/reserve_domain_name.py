import json
from instance_service import InstanceService
from redis_connection import get_redis_connection

conn = get_redis_connection()


def lambda_handler(event, context):
    sub_domain_name = json.loads(event['body'])['subDomainName']
    print(f'Reserving sub domain: {sub_domain_name}')
    instance_service = InstanceService(redis_conn=conn)
    response = instance_service.reserve_sub_domain_name(sub_domain_name)
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response)
    }
