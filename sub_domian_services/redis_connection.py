from redis import Redis
import logging
import os

import boto3

logging.basicConfig(level=logging.INFO)
current_region = os.environ.get('AWS_REGION')
ssm = boto3.client('ssm', region_name=current_region)


def get_redis_connection():
    resp = ssm.get_parameter(Name='/alc/autobots/redis/endpoint')

    if resp:
        print(f'retrieve the ssm param value')
        print('resp:', resp)
    else:
        print(f'failed to retrieve value from ssm param store')

    if resp:
        primary_endpoint = resp['Parameter']['Value']
        print('redis primary ep: ', primary_endpoint)
        port = 6379
        conn = Redis(host=primary_endpoint, port=port)
        try:
            if conn.ping():
                logging.info("connected to redis")
                print('Connection to redis - Successful')
                return conn
        except Exception as e:
            print(e)
    else:
        raise Exception('EXCEPTION: INVALID-SSM-VALUE')
