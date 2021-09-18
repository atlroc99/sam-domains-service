import json
from instance_service import InstanceService


def lambda_handler(event, context):
    sub_domain_name = json.loads(event['body'])['subDomainName']
    print('Get Instance status for associated domain name : ', sub_domain_name)
    instance_service = InstanceService()
    instance_status = instance_service.get_instances_status(sub_domain_name)
    print('Instance Status', instance_status)
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'status': instance_status})
    }
