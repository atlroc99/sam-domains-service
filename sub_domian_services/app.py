import json


# for test
def lambda_handler(event, context):
    path_param = event['pathParameters']
    sub_domain_name = path_param['path_name']
    print('path_param', path_param)  # {'path_name': 'subDomainName'}
    # 'f6jz3rblo7'

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world",
            "sub_domain_name": sub_domain_name,
        })
    }
