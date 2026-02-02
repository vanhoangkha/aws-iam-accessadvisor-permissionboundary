#!/usr/bin/env python3
# Copyright 2008-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License").

import boto3
from botocore.exceptions import ClientError
import time
from datetime import date
import json
import os

__version__ = '1.1'
__author__ = '@ddmitriy@'

# Environment variables
bucket = os.environ.get('DoNotListBucket', '')
key = os.environ.get('DoNotListKey', '')
enforce = os.environ.get('Enforce', 'no')
base_actions = os.environ.get('BaseActions', '')
days_expire = int(os.environ.get('DaysExpire', 180))

# Reusable clients
iam_client = boto3.client('iam')
s3_resource = boto3.resource('s3')
sts_client = boto3.client('sts')

NoBoundaryPolicyEdit = [
    "iam:CreatePolicyVersion",
    "iam:DeletePolicy",
    "iam:DeletePolicyVersion",
    "iam:SetDefaultPolicyVersion"
]


def get_aws_account_id():
    return sts_client.get_caller_identity()["Account"]


def get_list_s3(bucket_name, key_name):
    print({'msg': 'get_s3_object', 'bucket': bucket_name, 'key': key_name})
    do_not_list = []
    try:
        obj = s3_resource.Object(bucket_name, key_name)
        body = obj.get()['Body'].read().decode('utf8')
        for i in body.split(','):
            i = i.strip('\n').strip()
            if i:
                do_not_list.append(i)
    except ClientError as e:
        print(f"Error reading S3 object: {e}")
    return do_not_list


def get_users():
    user_names = []
    paginator = iam_client.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page['Users']:
            user_names.append(user['Arn'])
    return user_names


def get_roles():
    role_names = []
    paginator = iam_client.get_paginator('list_roles')
    for page in paginator.paginate():
        for role in page['Roles']:
            role_names.append(role['Arn'])
    return role_names


def get_groups():
    group_names = []
    paginator = iam_client.get_paginator('list_groups')
    for page in paginator.paginate():
        for group in page['Groups']:
            group_names.append(group['Arn'])
    return group_names


def generateServiceLastAccessedDetails(arn):
    response = iam_client.generate_service_last_accessed_details(Arn=arn)
    return response['JobId']


def wait_for_job(func, max_retries=30, base_delay=1):
    """Exponential backoff for job completion."""
    for attempt in range(max_retries):
        response = func()
        if response.get('JobStatus') == 'COMPLETED':
            return response
        delay = min(base_delay * (2 ** attempt), 30)
        time.sleep(delay)
    raise TimeoutError("Job did not complete in time")


def getServiceLastAccessedDetails(jobid):
    def fetch():
        return iam_client.get_service_last_accessed_details(JobId=jobid)
    return wait_for_job(fetch)


def getServiceLastAccessedDetailswithEntities(jobid, service):
    def fetch():
        return iam_client.get_service_last_accessed_details_with_entities(
            JobId=jobid, ServiceNamespace=service
        )
    return wait_for_job(fetch)


def tag_role(role, key_name, value):
    try:
        iam_client.tag_role(RoleName=role, Tags=[{'Key': key_name, 'Value': value}])
    except ClientError as e:
        print(f"Error tagging role {role}: {e}")


def tag_user(user, key_name, value):
    try:
        iam_client.tag_user(UserName=user, Tags=[{'Key': key_name, 'Value': value}])
    except ClientError as e:
        print(f"Error tagging user {user}: {e}")


def create_iam_policy(iam_entity, servicelist, accountid):
    iam_policy_name = 'AccessAdvisor-PB-' + iam_entity
    policy_arn = f'arn:aws:iam::{accountid}:policy/{iam_policy_name}'

    base_actions_list = get_list_s3(bucket, base_actions)
    if servicelist == base_actions_list:
        servicelist2 = servicelist
    else:
        servicelist2 = sorted([s + ':*' for s in servicelist])

    policy_doc = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'AccessAdvisorPermissionsBoundary',
                'Effect': 'Allow',
                'Action': servicelist2,
                'Resource': '*'
            },
            {
                'Sid': 'NoBoundaryPolicyEdit',
                'Effect': 'Deny',
                'Action': NoBoundaryPolicyEdit,
                'Resource': policy_arn
            },
            {
                'Sid': 'NoBoundaryRoleDelete',
                'Effect': 'Deny',
                'Action': ['iam:DeleteRolePermissionsBoundary', 'iam:DeleteUserPermissionsBoundary'],
                'Resource': '*'
            }
        ]
    }
    iam_policy_json = json.dumps(policy_doc)

    try:
        response = iam_client.get_policy(PolicyArn=policy_arn)
        policyver = response['Policy']['DefaultVersionId']
        response_ver = iam_client.get_policy_version(PolicyArn=policy_arn, VersionId=policyver)
        version_action = response_ver['PolicyVersion']['Document']['Statement'][0].get('Action', [])

        if sorted(version_action) if isinstance(version_action, list) else version_action != servicelist2:
            try:
                iam_client.create_policy_version(PolicyArn=policy_arn, PolicyDocument=iam_policy_json, SetAsDefault=True)
            except ClientError:
                # Delete old version and retry
                p_id = int(policyver[1:]) - 3
                if p_id > 0:
                    iam_client.delete_policy_version(PolicyArn=policy_arn, VersionId=f'v{p_id}')
                iam_client.create_policy_version(PolicyArn=policy_arn, PolicyDocument=iam_policy_json, SetAsDefault=True)
    except iam_client.exceptions.NoSuchEntityException:
        iam_client.create_policy(PolicyName=iam_policy_name, PolicyDocument=iam_policy_json)

    return policy_arn


def attach_user_pb(user, pb):
    do_not_list = get_list_s3(bucket, key)
    if user not in do_not_list:
        try:
            iam_client.put_user_permissions_boundary(UserName=user, PermissionsBoundary=pb)
        except ClientError as e:
            print(f"Error attaching boundary to user {user}: {e}")


def attach_role_pb(role, pb):
    do_not_list = get_list_s3(bucket, key)
    if role not in do_not_list:
        try:
            iam_client.put_role_permissions_boundary(RoleName=role, PermissionsBoundary=pb)
        except ClientError as e:
            print(f"Error attaching boundary to role {role}: {e}")


def process_entity(entity_type, entities, tag_func, attach_func):
    do_not_list = get_list_s3(bucket, key)
    
    for entity_arn in entities:
        print({'start': entity_arn})
        services = []
        used_count = 0
        unused_count = 0
        total_count = 0
        entity_name = entity_arn.split("/")[-1]

        try:
            jobid = generateServiceLastAccessedDetails(entity_arn)
            details = getServiceLastAccessedDetails(jobid)
        except Exception as e:
            print(f"Error getting details for {entity_arn}: {e}")
            continue

        for service in details.get('ServicesLastAccessed', []):
            total_count += 1

            if service['TotalAuthenticatedEntities'] > 0 and service.get('LastAuthenticated'):
                last_auth = service['LastAuthenticated']
                dategap = (date.today() - last_auth.date()).days

                if dategap <= days_expire:
                    used_count += 1
                    services.append(service['ServiceNamespace'])
                    
                    if entity_name not in do_not_list:
                        tag_func(entity_name, f'{entity_type}ServiceAccessed{used_count}', service['ServiceNamespace'])
            else:
                unused_count += 1

        if enforce == 'yes' and entity_name not in do_not_list:
            if not services:
                services = get_list_s3(bucket, base_actions)
            if services:
                policy_arn = create_iam_policy(entity_name, services, get_aws_account_id())
                attach_func(entity_name, policy_arn)

        if total_count > 0:
            calc_coverage = round(used_count / total_count * 100)
            tag_func(entity_name, 'Permissions_Coverage_Percent', str(calc_coverage))
            tag_func(entity_name, 'Permissions_Granted', str(total_count))
            tag_func(entity_name, 'Permissions_Unused', str(unused_count))


def iam_users():
    process_entity('user', get_users(), tag_user, attach_user_pb)


def iam_roles():
    process_entity('role', get_roles(), tag_role, attach_role_pb)


def iam_groups():
    do_not_list = get_list_s3(bucket, key)
    
    for group in get_groups():
        used_count = 0
        unused_count = 0

        try:
            jobid = generateServiceLastAccessedDetails(group)
            details = getServiceLastAccessedDetails(jobid)
        except Exception as e:
            print(f"Error getting details for {group}: {e}")
            continue

        for service in details.get('ServicesLastAccessed', []):
            if service['TotalAuthenticatedEntities'] > 0:
                used_count += 1
                try:
                    details_w_entity = getServiceLastAccessedDetailswithEntities(jobid, service['ServiceNamespace'])
                    for e in details_w_entity.get('EntityDetailsList', []):
                        user = e['EntityInfo']['Name']
                        if user not in do_not_list:
                            tag_user(user, f'GroupServiceAccessed{used_count}', service['ServiceNamespace'])
                except Exception as ex:
                    print(f"Error processing group entity: {ex}")
            else:
                unused_count += 1

        total_count = used_count + unused_count
        if total_count > 0:
            calc_coverage = round(used_count / total_count * 100)
            print({'summary': 'group', 'name': group, 'coverage': calc_coverage})


def lambda_handler(event, context):
    print({'msg': 'start_execution', 'enforcement': enforce, 'expiration': days_expire})
    iam_users()
    iam_roles()
    iam_groups()
    print({'msg': 'end_execution'})


if __name__ == '__main__':
    lambda_handler(None, None)
