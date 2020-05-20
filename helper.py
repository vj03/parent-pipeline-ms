#!/usr/bin/env python3
# -*- coding: future_fstrings -*-
"""Helper script for checking client and organization IDs"""
import argparse
import os
import sys

import boto3
import requests


def parse_args():
    """Parse arguments passed to script"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--client-id', required=False,
        help='New Client ID to check against existing clients')
    parser.add_argument(
        '-o', '--org-id', required=False,
        help='New organization ID to check against existing organizations')

    environment_options = {
        'help': 'MuleSoft environment to run checks against'
    }

    if os.environ.get('Environment'):
        environment_options['default'] = os.environ['Environment']
    else:
        environment_options['required'] = True

    parser.add_argument('-e', '--environment', **environment_options)

    parser.add_argument(
        '--provisioning-api-host', required=False,
        help='Host to use when making requests against DIAS Provisioning API')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    return vars(parser.parse_args())


def get_parameter(name, ssm_client, **_):
    """Get SSM Parameter Store parameter contents"""
    try:
        return ssm_client.get_parameter(
            Name=name, WithDecryption=True)['Parameter']['Value']
    except ssm_client.exceptions.ParameterNotFound:
        return ''


def get_provisioning_api(endpoint, provisioning_api_host, **_):
    """Get data from DIAS Provisioning API"""
    request = requests.get(f'{provisioning_api_host}/{endpoint}')

    if not request.ok:
        # continue execution if not found
        if request.status_code == 404:
            return {}

        sys.exit(f'get_provisioning_api> {request.status_code}: {request.text}')

    return request.json()


def check_client_id(client_id, **kwargs):
    """Check client ID"""
    # TODO lookup client id in provisioning api
    print(get_parameter(f'/monitoring-center/{client_id}/org_id', **kwargs))


def check_org_id(org_id, **kwargs):
    """Check org ID"""
    response = get_provisioning_api(f'organizations/{org_id}', **kwargs)

    try:
        sku = response['organizations'][0]['environment']['entitlement'] \
            ['productSKU']
        print(sku)
    except (KeyError, IndexError):
        print()


def main(environment, **kwargs):
    """Check Client ID and Org ID"""
    kwargs['ssm_client'] = boto3.client('ssm')

    if not kwargs.get('provisioning_api_host'):
        base_host = 'cloudhub.io' if environment == 'prod' else 'msap.io'
        kwargs['provisioning_api_host'] = \
            f'https://dias-provisioning-api.{environment}.{base_host}'

    # check client id
    if kwargs.get('client_id'):
        check_client_id(**kwargs)

    # check org id
    if kwargs.get('org_id'):
        # lookup sku for org id
        check_org_id(**kwargs)


if __name__ == '__main__':
    main(**parse_args())
