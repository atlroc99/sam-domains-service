import json

from redis_connection import get_redis_connection
from instance_service import InstanceService

instance_service = InstanceService(redis_conn=get_redis_connection())


def lambda_handler(event, context):
    domains = instance_service.list_reserved_domains()
    print('list of reserved domains')
    print(domains)
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'reservedDomains': domains})
    }
