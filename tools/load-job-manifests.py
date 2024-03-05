#!/usr/bin/env python
"""Loads Job Manifests using a YAML file to define their origin.
The file is simply a list of manifests that have a `url`, optional `header`,
and `params` (both of which are expected to be JSON strings of keys and values).
"""
import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List
import urllib3

from rich.console import Console
from squonk2.auth import Auth
from squonk2.dm_api import DmApi, DmApiRv
from squonk2.environment import Environment
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(c_args: argparse.Namespace, filename: StopIteration) -> None:
    """Main function."""

    console = Console()

    _ = Environment.load()
    env: Environment = Environment(c_args.environment)
    DmApi.set_api_url(env.dm_api)

    token: str = Auth.get_access_token(
        keycloak_url=env.keycloak_url,
        keycloak_realm=env.keycloak_realm,
        keycloak_client_id=env.keycloak_dm_client_id,
        username=env.admin_user,
        password=env.admin_password,
    )
    if not token:
        print("Failed to get token")
        sys.exit(1)

    # Just read the list from the chosen file
    file_content: str = Path(filename).read_text(encoding='utf8')
    manifests: List[Dict[str, Any]] = yaml.load(file_content, Loader=yaml.FullLoader)
    # Load the manifests one at a time (to handle any errors gracefully)
    num_manifests: int = 0
    num_manifests_failed: int = 0
    for manifest in manifests:
        # A manifest must have a url and optional header and params
        url: str = manifest.get('url')
        if not url:
            console.log(':boom: File has a manifest without a URL')
            sys.exit(1)
        header: str = manifest.get('header')
        params: str = manifest.get('params')
        # Now try and set the rate...
        jm_rv: DmApiRv = DmApi.put_job_manifest(token, url=url, header=header, params=params)
        if jm_rv.success:
            num_manifests += 1
            emoji = ':white_check_mark:'
        else:
            num_manifests_failed += 1
            emoji = ':cross_mark:'
        # Log
        console.log(f'{emoji} {url}')

    # Summary
    if num_manifests:
        console.log(f'Job manifests loaded {num_manifests}')
    # Error states
    if num_manifests_failed:
        console.log(f'Job manifest failures {num_manifests_failed}')


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="load-job-manifests",
        description="Loads Job Manifests (from a YAML file)"
    )
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument('file', type=str, help='The source file')
    args: argparse.Namespace = parser.parse_args()

    filename: str = args.file
    if not filename.endswith('.yaml'):
        filename += '.yaml'

    # File must exist
    if not Path(filename).is_file():
        parser.error(f"File '{filename}' does not exist")

    main(args, filename)
