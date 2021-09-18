import json

from instance_service import InstanceService

from redis_connection import get_redis_connection

conn = get_redis_connection()


def lambda_handler(event, context):
    instance_service = InstanceService(redis_conn=conn)
    print('EVENT')
    print(event)
    sub_domain_name = json.loads(event['body'])['subDomainName'] + '.'
    print('Check availability: ', sub_domain_name)
    response = instance_service.is_sub_domain_name_available(sub_domain_name)
    print('response', response)
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'isAvailable': response})
    }