#!/usr/bin/env python
"""Loads Job/Application Exchange Rates from a file.
"""
import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import urllib3

from rich.console import Console
from squonk2.auth import Auth
from squonk2.dm_api import DmApi, DmApiRv
from squonk2.environment import Environment
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(c_args: argparse.Namespace) -> None:
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

    # Just read the list from the chosen file
    file_content: str = Path(c_args.file).read_text(encoding='utf8')
    rates: List[Dict[str, Any]] = yaml.load(file_content, Loader=yaml.FullLoader)
    er_rv: DmApiRv = DmApi.set_job_exchange_rates(token, rates=rates)
    if not er_rv.success:
        console.log(f'[bold red]ERROR[/bold red] {er_rv.msg["error"]}')
        sys.exit(1)

    num_rates: int = len(rates)
    if num_rates:
        console.log(f'Loaded {num_rates}')
    else:
        console.log('Loaded [bold red]nothing[/bold red]')


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="load-er",
        description="Loads exchange rates (from a YAML file)"
    )
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument('file', type=str, help='The source file')
    args: argparse.Namespace = parser.parse_args()

    # File must exist
    if not Path(args.file).is_file():
        parser.error("File does not exist")

    main(args)
