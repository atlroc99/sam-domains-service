import json
from uuid import uuid4
from copy import copy
import boto3
import os.path
from service_util import (is_none_or_empty, default)
import pickle
import random

region = os.environ.get('region')
route53_client = boto3.client('route53')
ec2_client = boto3.client('ec2', region_name=region)
elb_v2_client = boto3.client('elbv2', region_name=region)


class InstanceService:

    def __init__(self, **kwargs):
        print("initializing InstanceService and redis connection")
        print(f"kwargs has redis_conn: {'redis_conn' in kwargs.keys()}")
        if "redis_conn" in kwargs.keys():
            self.conn = kwargs.get("redis_conn")

    def is_sub_domain_name_available(self, sub_domain_name: str):
        print(f'checking for availability for domain name: {sub_domain_name}')

        is_available = True
        # checking if the sub domain name has been reserved
        is_reserved = self.__key_exists(sub_domain_name)
        print(f'domain name is_reserved: {type(is_reserved)} and : {is_reserved}')
        if is_reserved:
            return not is_available

        hosted_zone = self.__get_hosted_zone(sub_domain_name=sub_domain_name)
        print('hosted_zone: ', hosted_zone)

        if is_none_or_empty(hosted_zone):
            return {"error_msg": "Invalid domain name"}

        zone_id = hosted_zone.get('Id')[12:]  # skip the word /hostedzone/
        zone_name = hosted_zone.get('Name')
        print(f'sub_domain_name: {sub_domain_name} | zone-id: {zone_id} |  zone-name: {zone_name}')
        record_set = self.__get_paginated_resource_records_sets(zone_id=zone_id, sub_domain_name=sub_domain_name)
        is_available = is_none_or_empty(record_set)
        return is_available

    # get the records set -> contains records set and elbs
    def __get_paginated_resource_records_sets(self, zone_id: str, sub_domain_name: str) -> dict:
        print(f'Get get_paginated_resource_records_sets: {zone_id} and sub-domain-name: {sub_domain_name}')

        if is_none_or_empty(zone_id):
            raise Exception(f'{self.__class__.__name__}: InvalidZoneIDException: Invalid Zone ID: {zone_id}')

        record_set_dict = {}
        try:
            response = route53_client.get_paginator('list_resource_record_sets').paginate(HostedZoneId=zone_id)
            resource_record_set = response.search(f"ResourceRecordSets[?Name=='{sub_domain_name}']")

            if is_none_or_empty(resource_record_set):
                raise Exception(f'{self.__class__.__name__}: Exception: NoRecordSetFound for hosted-zone-id: {zone_id}')

            print(f'Type of resource_record_set: {resource_record_set} | {resource_record_set}')

            for resource_record in resource_record_set:
                record_set_dict = copy(json.loads(json.dumps(resource_record)))
        except StopIteration as er:
            print(er)

        return record_set_dict

    def get_instances_status(self, sub_domain: str) -> dict:
        print(f'get instances by sub-domain-name: {sub_domain}')
        # this is for testing only
        # remove this once the actual instances are in place
        print(f'get instances by sub-domain-name: {sub_domain}')
        colors = ['red', 'green', 'green', 'green',
                  'yellow', 'yellow', 'green', 'green']
        random_int = random.randint(0, 7)
        random_int_2 = random.randint(0, 7)
        return {
            'instances': [
                {
                    'name': f'i-{str(uuid4())[:10]}',
                    'color': colors[random_int]
                },
                {
                    'name': f'i-{str(uuid4())[:10]}',
                    'color': colors[random_int_2]
                }
            ]
        }

        hosted_zone = self.__get_hosted_zone(sub_domain)

        if is_none_or_empty(hosted_zone):
            return {"error_msg": "Invalid sub domain name or no sub domain name provided"}

        record_set = self.__get_paginated_resource_records_sets(hosted_zone['Id'], sub_domain_name=sub_domain)
        print(f'record_set: {record_set}')

        if is_none_or_empty(record_set):
            return {
                'message': f'no Recordset found associated with the sub_domain_name: {sub_domain}'
            }
        record_type = record_set['Type']
        elb_dns_name = record_set['AliasTarget']['DNSName']

        if is_none_or_empty(elb_dns_name):
            raise Exception('{self.__class__.__name__}: No DNS Name found')

        _elb_name = ''
        if record_type == 'A':
            if elb_dns_name.startswith('dualstack'):
                elb_dns_name = elb_dns_name[len('dualstack.'):]

        elb = self.__get_elastic_load_balancer(elb_dns_name, region_name=region)
        if is_none_or_empty(elb):
            raise Exception(
                f'{self.__class__.__name__}: NoElasticLoadBalancerFoundException for dns_name: {elb_dns_name}')

        # print('found elb:', json.dumps(elb, indent=2, default=default))
        elb_arn = elb.get('LoadBalancerArn')
        # elb_arn= arn:aws:elasticloadbalancing:us-west-1:829898772826:loadbalancer/app/hwc-alb-west/fac6f91c5337f126
        elb_dns = elb.get('DNSName')
        load_balancer_name = elb.get('LoadBalancerName')

        print('ELB Target Group ....')
        target_group_arns = elb_v2_client \
            .get_paginator('describe_target_groups') \
            .paginate(LoadBalancerArn=elb_arn) \
            .search("TargetGroups[].TargetGroupArn")

        targets = [elb_v2_client.describe_target_health(TargetGroupArn=tg_arn) for tg_arn in target_group_arns]
        print(f'{len(targets)} target groups are attached to this elb : {elb}')

        target_id_and_port = []
        for target in targets:
            for target_description in target['TargetHealthDescriptions']:
                target_id_and_port.append(target_description['Target'])

        if len(target_id_and_port) == 0:
            return {
                'message': f'No instances found ',
                'sub-domain-name': sub_domain,
                'elb-dns': elb_dns,
                'load-balancer-name': load_balancer_name
            }

        instance_ids = [target['Id'] for target in target_id_and_port]
        print(f'Check status for instance-ids: {instance_ids}')
        # instances_state = self.get_instances_state_by_ids(tuple(set(instance_ids)))
        instances_state = self.get_instances_state_by_ids(instance_ids)
        return {'InstancesState': instances_state}

    def __get_elastic_load_balancer(self, elb_dns_name: str, region_name: str):
        print(f'get load balancers by name')
        elb_v2_client.__setattr__('region-name', region_name)
        paginator = elb_v2_client.get_paginator('describe_load_balancers')
        # results = paginator.paginate().search(f"LoadBalancers[?DNSName=='{elb_dns_name}']")
        results = paginator.paginate().search('LoadBalancers')

        if is_none_or_empty(results):
            raise Exception("{self.__class__.__name__}: NOLoadBalancerFoundException ")

        for res in results:
            # print(json.dumps(res, indent=2, default=default))
            if res['DNSName'] in elb_dns_name:
                return res

        return None

    '''
        [
            {
                "Code": 16,
                "Name": [
                    "hwc-linux-wc-hub"
                ]
            },
        ]
        * Instance code and state
            0 : pending
            16 : running
            32 : shutting-down
            48 : terminated
            64 : stopping
            80 : stopped
    '''

    # def get_instances_state_by_ids(self, instance_ids: tuple) -> list:
    def get_instances_state_by_ids(self, instance_ids: list) -> list:
        ids = tuple(set(instance_ids))
        response = ec2_client.get_paginator('describe_instances') \
            .paginate(InstanceIds=ids) \
            .search(
            "Reservations[].Instances[].{Code:State.Code, Name: Tags[?Key=='Name']}")  # --query "Reservations[].Instances[].Tags[?Key=='Name']"
        # .search("Reservations[].Instances[].{Code:State.Code,Name: Tags[].Value}")

        instance_states = []
        for instance in response:
            print('*** Value', instance['Name'][0]['Value'])
            state = 'red'
            instance_name = 'Name not Available'
            if instance['Code'] == 0:
                state = 'yellow'
            elif instance['Code'] == 16:
                state = 'green'

            print('Value', instance['Name'][0]['Value'])
            if not is_none_or_empty(instance['Name'][0]['Value']):
                instance_name = instance['Name'][0]['Value']

            print(f'instance_name: {instance_name}')
            instance_states.append({'name': instance_name, 'color': state})

        return instance_states

    def __get_hosted_zone(self, sub_domain_name: str) -> dict:
        print(f'GET hosted-zone: {sub_domain_name}')
        hosted_zone = None
        possible_hosted_zone_names = ['dev.controlj.com.',
                                      'webctrl.automatedlogic.com.',
                                      'automatedlogic.com.',
                                      'ivu.carrier.com.',
                                      'carrier.com.']
        hosted_zone_names = [
            domain for domain in possible_hosted_zone_names if domain in sub_domain_name]
        hosted_zone_name = hosted_zone_names[0] if len(
            hosted_zone_names) > 0 else ''

        if is_none_or_empty(hosted_zone_name):
            print(f'top level domain does not exist in sub domain name: {sub_domain_name}')
            return hosted_zone

        print(f'Query for hosted_zone_name: {hosted_zone_name}')
        response_iterator = route53_client.get_paginator('list_hosted_zones').paginate()
        filtered_itr = response_iterator.search(f"HostedZones[?contains(Name,'{hosted_zone_name}')]")
        hosted_zone_items = [item for item in filtered_itr if item['Name'] == hosted_zone_name]

        if not is_none_or_empty(hosted_zone_items):
            hosted_zone = hosted_zone_items[0]

        return hosted_zone

    def reserve_sub_domain_name(self, sub_domain_name: str) -> {}:
        sub_domain_name_object = {
            'uuid': str(uuid4()),
            'region': region,
            'sub_domain_name': sub_domain_name,
            'reserved': True
        }
        if not self.conn:
            return {"error_msg": f"unable to connect to redis conn type:{type(self.conn)}"}

        if self.__key_exists(sub_domain_name):
            return {
                'message': f'Unable to reserve {sub_domain_name}.The name has already been reserved',
                'subDomain': pickle.loads(self.conn.get(sub_domain_name))
            }

        self.conn.set(sub_domain_name, pickle.dumps(sub_domain_name_object))
        return pickle.loads(self.conn.get(sub_domain_name))

    def list_reserved_domains(self):
        if self.conn:
            keys = [key.decode('utf-8') for key in self.conn.keys()]
            return keys
        else:
            return 'error connecting to redis or not able to list reserved names'

    def __key_exists(self, sub_domain_name: str):
        print(f"checking if the domain name {sub_domain_name} has already been reserved...")
        if not self.conn:
            return {"error_msg": f"unable to connect to cluster: {type(self.conn)}"}
        keys = [key.decode('utf-8') for key in self.conn.keys()]
        temp = sub_domain_name
        if sub_domain_name.endswith("."):
            temp = sub_domain_name[:-1]
        return temp in keys
