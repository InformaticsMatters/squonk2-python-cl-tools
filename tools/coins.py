#!/usr/bin/env python
"""Calculates Coin charges for an AS Product.
"""
import argparse
from collections import namedtuple
from decimal import Decimal
import sys
from typing import Any, Dict, Optional
import urllib3

from rich.pretty import pprint
from rich.console import Console
from squonk2.auth import Auth
from squonk2.as_api import AsApi, AsApiRv
from squonk2.environment import Environment

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AdjustedCoins: namedtuple = namedtuple("AdjustedCoins",
                                       ["coins", "fc", "ac", "aac"])


def main(c_args: argparse.Namespace) -> None:
    """Main function."""

    console = Console()

    _ = Environment.load()
    env: Environment = Environment(c_args.environment)
    AsApi.set_api_url(env.as_api)

    token: str = Auth.get_access_token(
        keycloak_url=env.keycloak_url,
        keycloak_realm=env.keycloak_realm,
        keycloak_client_id=env.keycloak_as_client_id,
        username=env.admin_user,
        password=env.admin_password,
    )

    # Get the product details.
    # This gives us the product's allowance, limit and overspend multipliers
    p_rv: AsApiRv = AsApi.get_product(token, product_id=args.product)
    if not p_rv.success:
        console.log(p_rv.msg)
        console.log(f"[bold red]ERROR[/bold red] Failed to get [blue]{args.product}[/blue]")
        sys.exit(1)
    if args.verbose:
        pprint(p_rv.msg)

    product_id: str = p_rv.msg["product"]["product"]["id"]
    product_name: str = p_rv.msg["product"]["product"]["name"]
    allowance: Decimal = Decimal(p_rv.msg["product"]["coins"]["allowance"])
    allowance_multiplier: Decimal = Decimal(p_rv.msg["product"]["coins"]["allowance_multiplier"])
    limit: Decimal = Decimal(p_rv.msg["product"]["coins"]["limit"])

    remaining_days: int = p_rv.msg["product"]["coins"]["remaining_days"]

    # Get the product's charges...
    pc_rv: AsApiRv = AsApi.get_product_charges(token, product_id=args.product)
    if not pc_rv.success:
        console.log(pc_rv.msg)
        console.log(f"[bold red]ERROR[/bold red] Failed to get [blue]{args.product}[/blue]")
        sys.exit(1)
    if args.verbose:
        pprint(pc_rv.msg)

    # Accumulate all the storage costs
    # (excluding the current which will be interpreted as the "burn rate")
    num_storage_charges: int = 0
    burn_rate: Decimal = Decimal()
    total_storage_coins: Decimal = Decimal()
    if "items" in pc_rv.msg["storage_charges"]:
        for item in pc_rv.msg["storage_charges"]["items"]:
            if "current_bytes" in item["additional_data"]:
                burn_rate = Decimal(item["coins"])
            else:
                total_storage_coins += Decimal(item["coins"])
                num_storage_charges += 1

    # Accumulate all the processing costs
    num_processing_charges: int = 0
    total_uncommitted_processing_coins: Decimal = Decimal()
    total_committed_processing_coins: Decimal = Decimal()
    if pc_rv.msg["processing_charges"]:
        for mp_charge in pc_rv.msg["processing_charges"]:
            charge_coins: Decimal = Decimal(mp_charge["charge"]["coins"])
            if "closed" in mp_charge:
                total_committed_processing_coins += charge_coins
            else:
                total_uncommitted_processing_coins += charge_coins
            num_processing_charges += 1

    invoice: Dict[str, Any] = {
        "Product": product_id,
        "Product Name": product_name,
        "Claim ID": pc_rv.msg.get("claim_id", "Unclaimed"),
        "Claim Name": pc_rv.msg.get("claim_name", "Undefined"),
        "Allowance": str(allowance),
        "Allowance Multiplier": str(allowance_multiplier),
        "Limit": str(limit),
        "From": pc_rv.msg["from"], "Until": pc_rv.msg["until"],
        "Billing Day": p_rv.msg["product"]["coins"]["billing_day"],
        "Remaining Days": remaining_days,
        "Current Burn Rate": str(burn_rate),
        "Number of Storage Charges": num_storage_charges,
        "Number of Processing Charges": num_processing_charges,
        "Committed Storage Coins": str(total_storage_coins),
        "Committed Processing Coins": str(total_committed_processing_coins),
        "Uncommitted Processing Coins": str(total_uncommitted_processing_coins),
    }

    total_coins: Decimal = total_storage_coins + total_committed_processing_coins

    ac: AdjustedCoins = _calculate_adjusted_coins(
        total_coins,
        allowance,
        allowance_multiplier,
    )

    invoice["Allowance Adjustment"] = {
        "Coins (Total Raw)": f"{total_storage_coins} + {total_committed_processing_coins} = {total_coins}",
        "Coins (Penalty Free)": str(ac.fc),
        "Coins (In Allowance Band)": str(ac.ac),
        "Coins (Allowance Charge)": f"{ac.ac} x {allowance_multiplier} = {ac.aac}",
        "Coins (Adjusted)": f"{ac.fc} + {ac.aac} = {ac.coins}",
    }

    additional_coins: Decimal = total_uncommitted_processing_coins + burn_rate * remaining_days
    predicted_total_coins: Decimal = total_coins
    zero: Decimal = Decimal()
    if remaining_days > 0:
        if burn_rate > zero:

            predicted_total_coins += additional_coins
            p_ac: AdjustedCoins = _calculate_adjusted_coins(
                predicted_total_coins,
                allowance,
                allowance_multiplier)

            invoice["Prediction"] = {
                "Coins (Burn Rate)": str(burn_rate),
                "Coins (Additional Spend)": f"{total_uncommitted_processing_coins} + {remaining_days} x {burn_rate} = {additional_coins}",
                "Coins (Total Raw)": f"{total_coins} + {additional_coins} = {predicted_total_coins}",
                "Coins (Penalty Free)": str(p_ac.fc),
                "Coins (In Allowance Band)": str(p_ac.ac),
                "Coins (Allowance Charge)": f"{p_ac.ac} x {allowance_multiplier} = {p_ac.aac}",
                "Coins (Adjusted)": f"{p_ac.fc} + {p_ac.aac} = {p_ac.coins}",
            }

    # Now just pre-tty-print the invoice
    pprint(invoice)


def _calculate_adjusted_coins(total_coins: Decimal,
                              allowance: Decimal,
                              allowance_multiplier: Decimal) -> AdjustedCoins:
    """Adjust total based on allowance and limit multipliers.
    Coins between the allowance and limit use the allowance multiplier.
    Coins above the limit use the limit multiplier.
    """

    # How many are free of any penalty?
    free_coins: Decimal = min(total_coins, allowance)

    allowance_coins: Decimal = Decimal()
    adjusted_allowance_coins: Decimal = Decimal()
    limit_coins: Decimal = Decimal()
    adjusted_limit_coins: Decimal = Decimal()

    if total_coins > allowance:
        allowance_coins = max(total_coins - allowance, Decimal())
        adjusted_allowance_coins = allowance_coins * allowance_multiplier

    adjusted_coins: Decimal = free_coins + adjusted_allowance_coins

    return AdjustedCoins(coins=adjusted_coins,
                         fc=free_coins,
                         ac=allowance_coins,
                         aac=adjusted_allowance_coins)


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="coins",
        description="Calculates a Product's Coin Charges (actual and predicted)"
    )
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument('product', type=str, help='The Product UUID')
    parser.add_argument(
        '--verbose',
        help='Set to print extra information',
        action='store_true',
    )
    args: argparse.Namespace = parser.parse_args()

    main(args)
