import argparse
import base64
import deepdiff
import json
import logging
import os
import pprint
import requests
import sys
import yaml
from pprint import pp


if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name', help='Microservice name', default='', required=True)
    parser.add_argument('-v', '--version', help='Microservice version', default='', required=True)
    parser.add_argument('-l', '--log-level', help='Set log level: info (default) or debug', default='info')
    args = parser.parse_args()
    microservice_name = args.name
    microservice_version = args.version
    log_level = args.log_level
    gitlab_address = ''
    project_name = ''

    # Set up logging
    logger = logging.getLogger(__name__)
    if log_level == 'info':
        logger.setLevel(logging.INFO)
    elif log_level == 'debug':
        logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s'))
    logger.addHandler(handler)
    if log_level == 'debug':
        logger.debug("Program started in debug mode!")
        pp = pprint.PrettyPrinter(depth=4)
    logger.debug(
        f"Arguments received - microservice_name: {microservice_name}, microservice_version: {microservice_version}, log_level: {log_level}")

    # Load config file with env parameters
    logging.info("Load servers config")
    script_dir = os.path.dirname(os.path.realpath(__file__))
    server_conf_path = os.path.join(script_dir, "config.yaml")
    with open(server_conf_path) as f:
        config_envs = yaml.safe_load(f)
        consul_token = config_envs['consul_token']
        gitlab_token = config_envs['gitlab_token']
        consul_scheme = config_envs['consul_scheme']
        consul_address = config_envs['consul_address']
        consul_port = config_envs['consul_port']
        project_name = config_envs['project_name']

    # Function to get yaml data from requests
    def fetch_content(data):
        data_yaml = json.loads(data.content.decode('utf-8'))
        data_yaml = base64.b64decode(data_yaml['content'])
        data_yaml = data_yaml.strip().decode('utf-8')
        data_yaml = yaml.safe_load(data_yaml)
        return data_yaml

    # Workaround with telemetryd naming
    if ((microservice_name == 'telemetryd-arnavi') or (microservice_name == 'telemetryd-egts')
       or (microservice_name == 'telemetryd-galileosky') or (microservice_name == 'telemetryd-teltonika')
       or (microservice_name == 'telemetryd-wialon-combine') or ( microservice_name == 'telemetryd-wialon-itelma-old')
       or (microservice_name == 'telemetryd-wialon')):
        if_telemetryd = True
        microservice_name_consul = microservice_name
        microservice_name_git = 'telemetryd'
    else:
        if_telemetryd = False
        microservice_name_consul = microservice_name
        microservice_name_git = microservice_name

    if if_telemetryd:
        logger.debug(f"Telemetryd microservice detected, keep that in mind...")
    logger.debug(f"The microservice name, which will be used for git: {microservice_name_git}, for consul: {microservice_name_consul}")

    # Get data from QA-consul
    logger.debug(f"Connecting to {project_name} QA consul and trying to get data")
    consul_response = requests.get(
        f'{consul_scheme}://{consul_address}:{consul_port}/v1/kv/cicd/{project_name}/qa/project/{microservice_name_consul}/helm_values',
        headers={"X-Consul-Token": consul_token})
    if consul_response.status_code != 200:
        logger.info(f"Error getting data from QA {project_name} consul!")
        exit(1)
    consul_data = consul_response.content.decode('utf-8').splitlines()[0]
    consul_data = json.loads(consul_data.strip('[]'))
    consul_data = base64.b64decode(consul_data["Value"]).strip().decode('utf-8')
    env_from_consul = yaml.safe_load(consul_data)

    if log_level == 'debug':
        print(f'ENV\'s in QA consul are:')
        print(type(env_from_consul))
        pp.pprint(env_from_consul)
        print('-----------------')

    # Get data from gitlab
    # First step: find out the project's id
    logger.debug(f"Connecting to gitlab and trying to get data. Step #1: looking for project id")
    gitlab_response = requests.get(f'https://{gitlab_address}/api/v4/projects/{project_name}%2F{microservice_name_git}',
                                   headers={"PRIVATE-TOKEN": gitlab_token})
    if gitlab_response.status_code != 200:
        logger.info(f"Error getting data from gitlab: couldn't define project id!")
        exit(0)
    gitlab_data = gitlab_response.content.decode('utf-8').splitlines()[0]
    gitlab_data = json.loads(gitlab_data)
    id_project_value = gitlab_data['id']
    logger.debug(f"The project's id in gitlab: {id_project_value}")

    # Second step: get and parse dev.yaml file
    # Telemetryd case
    if if_telemetryd == True:
        logger.debug(f"Telemetryd gitlab case")
        logger.debug(f"Connecting to gitlab and trying to fetch data. Step #2: looking for common-envs.yaml file and protocol-specific envs files, and sum them up")
        # Download common envs
        gitlab_response_common = requests.get(
            f'https://{gitlab_address}/api/v4/projects/{id_project_value}/repository/files/deploy%2Fcommon-envs.yaml?ref={microservice_version}',
            headers={"PRIVATE-TOKEN": gitlab_token})
        if gitlab_response_common.status_code != 200:
            logger.info(f"Error getting data from gitlab: couldn't get common telemetryd envs file!")
            exit(1)
        env_common_from_gitlab = fetch_content(gitlab_response_common)

        # Download protocol specific envs
        envs_file_name = ''
        if microservice_name == 'telemetryd-arnavi':
            envs_file_name = 'arnavi-dev.yaml'
        if microservice_name == 'telemetryd-egts':
            envs_file_name = 'egts-dev.yaml'
        if microservice_name == 'telemetryd-galileosky':
            envs_file_name = 'galileosky-dev.yaml'
        if microservice_name == 'telemetryd-teltonika':
            envs_file_name = 'teltonika-dev.yaml'
        if microservice_name == 'telemetryd-wialon-combine':
            envs_file_name = 'wialon-combine-dev.yaml'
        if microservice_name == 'telemetryd-wialon':
            envs_file_name = 'wialon-dev.yaml'
        if microservice_name == 'telemetryd-wialon-itelma-old':
            envs_file_name = 'wialon-itelma-old-dev.yaml'
        gitlab_response_protocol_specific = requests.get(
            f'https://{gitlab_address}/api/v4/projects/{id_project_value}/repository/files/deploy%2F{envs_file_name}?ref={microservice_version}',
            headers={"PRIVATE-TOKEN": gitlab_token})
        if gitlab_response_protocol_specific.status_code != 200:
            logger.info(f"Error getting data from gitlab: couldn't get protocol specific telemetryd envs file!")
            exit(1)
        env_protocol_specific_from_gitlab = fetch_content(gitlab_response_protocol_specific)

        # Merge and summ up the envs
        merged_envs = env_protocol_specific_from_gitlab['app']['env'] | env_common_from_gitlab['app']['env']
        env_protocol_specific_from_gitlab['app']['env'] = merged_envs
        env_from_gitlab = env_protocol_specific_from_gitlab
    else:
        # Common case (NOT telemetryd)
        logger.debug(f"Not telemetryd gitlab case")
        logger.debug(f"Connecting to gitlab and trying to fetch data. Step #2: looking for dev.yaml file")
        gitlab_response = requests.get(
            f'https://{gitlab_address}/api/v4/projects/{id_project_value}/repository/files/deploy%2Fdev.yaml?ref={microservice_version}',
            headers={"PRIVATE-TOKEN": gitlab_token})
        if gitlab_response.status_code != 200:
            logger.info(f"Error getting data from gitlab: couldn't get dev.yaml file!")
            exit(1)
        gitlab_data = json.loads(gitlab_response.content.decode('utf-8'))
        gitlab_data = base64.b64decode(gitlab_data['content'])
        gitlab_data = gitlab_data.strip().decode('utf-8')
        env_from_gitlab = yaml.safe_load(gitlab_data)

    if log_level == 'debug' and if_telemetryd == True:
        print(f'ENV\'s in gitlab after merging common and project files are:')
        print(type(env_from_gitlab))
        pp.pprint(env_from_gitlab)
        print('-----------------')
    elif log_level == 'debug':
        print(f'ENV\'s in gitlab are:')
        print(type(env_from_gitlab))
        pp.pprint(env_from_gitlab)
        print('-----------------')

    # Finally, compare the envs
    if env_from_gitlab and env_from_consul:
        diff = deepdiff.DeepDiff(env_from_consul, env_from_gitlab)
        logger.debug(f"Finally, calculating the difference of envs in consul and gitlab:")
        print(json.dumps(json.loads(diff.to_json()), indent=4))
