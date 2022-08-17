#!/usr/bin/env python
"""Calculates Coin charges for an AS Product.
"""
import argparse
from decimal import Decimal
from collections import namedtuple
from typing import Any, Dict, Optional
import urllib3

from rich.pretty import pprint
from squonk2.auth import Auth
from squonk2.as_api import AsApi, AsApiRv

from common import Env, get_env

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AdjustedCoins: namedtuple = namedtuple("AdjustedCoins",
                                       ["coins", "fc", "ac", "aac", "lc", "alc"])


def main(c_args: argparse.Namespace) -> None:
    """Main function."""
    env: Optional[Env] = get_env()
    if not env:
        return

    token: str = Auth.get_access_token(
        keycloak_url=env.keycloak_url,
        keycloak_realm=env.keycloak_realm,
        keycloak_client_id=env.keycloak_as_client_id,
        username=env.keycloak_user,
        password=env.keycloak_user_password,
    )

    # Get the product details.
    # This gives us the product's allowance, limit and overspend multipliers
    p_rv: AsApiRv = AsApi.get_product(token, product_id=args.product)
    assert p_rv.success
    allowance: Decimal = Decimal(p_rv.msg["product"]["coins"]["allowance"])
    allowance_multiplier: Decimal = Decimal(p_rv.msg["product"]["coins"]["allowance_multiplier"])
    limit: Decimal = Decimal(p_rv.msg["product"]["coins"]["limit"])
    overspend_multiplier: Decimal = Decimal(p_rv.msg["product"]["coins"]["overspend_multiplier"])

    remaining_days: int = p_rv.msg["product"]["coins"]["remaining_days"]

    invoice: Dict[str, Any] = {
        "Allowance": str(allowance),
        "Allowance Multiplier": str(allowance_multiplier),
        "Limit": str(limit),
        "Overspend Multiplier": str(overspend_multiplier),
    }

    # Get the product's charges...
    pc_rv: AsApiRv = AsApi.get_product_charges(token, product_id=args.product)
    assert pc_rv.success
    invoice["From"] = pc_rv.msg["from"]
    invoice["Until"] = pc_rv.msg["until"]

#    pprint(pc_rv.msg)

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
    total_processing_coins: Decimal = Decimal()
    if pc_rv.msg["processing_charges"]:
        for merchant in pc_rv.msg["processing_charges"]:
            for item in merchant["items"]:
                total_processing_coins += Decimal(item["coins"])
                num_processing_charges += 1

    # Accumulate processing coins
    total_processing_coins: Decimal = Decimal()

    invoice["Billing Day"] = p_rv.msg["product"]["coins"]["billing_day"]
    invoice["Remaining Days"] = remaining_days
    invoice["Current Burn Rate"] = str(burn_rate)
    invoice["Number of Storage Charges"] = num_storage_charges
    invoice["Accrued Storage Coins"] = str(total_storage_coins)
    invoice["Number of Processing Charges"] = num_processing_charges
    invoice["Accrued Processing Coins"] = str(total_processing_coins)

    total_coins: Decimal = total_storage_coins + total_processing_coins

    ac: AdjustedCoins = _calculate_adjusted_coins(
        total_coins,
        allowance,
        allowance_multiplier,
        limit,
        overspend_multiplier
    )

    invoice["Overspend Adjustment"] = {
        "Coins (Total Raw)": f"{total_storage_coins} + {total_processing_coins} = {total_coins}",
        "Coins (Penalty Free)": str(ac.fc),
        "Coins (In Allowance Band)": str(ac.ac),
        "Coins (Allowance Charge)": f"{ac.ac} x {allowance_multiplier} = {ac.aac}",
        "Coins (Above Limit)": str(ac.lc),
        "Coins (Overspend Charge)": f"{ac.lc} x {overspend_multiplier} = {ac.alc}",
        "Coins (Adjusted)": f"{ac.fc} + {ac.aac} + {ac.alc} = {ac.coins}",
    }

    additional_coins: Decimal = burn_rate * remaining_days
    predicted_total_coins: Decimal = total_coins
    zero: Decimal = Decimal()
    if remaining_days > 0:
        if burn_rate > zero:

            predicted_total_coins += additional_coins
            p_ac: AdjustedCoins = _calculate_adjusted_coins(
                predicted_total_coins,
                allowance,
                allowance_multiplier,
                limit,
                overspend_multiplier)

            invoice["Predicted Overspend Adjustment"] = {
                "Coins (Burn Rate)": str(burn_rate),
                "Coins (Additional Spend)": f"{remaining_days} x {burn_rate} = {additional_coins}",
                "Coins (Total Raw)": f"{total_coins} + {additional_coins} = {predicted_total_coins}",
                "Coins (Penalty Free)": str(p_ac.fc),
                "Coins (In Allowance Band)": str(p_ac.ac),
                "Coins (Allowance Charge)": f"{p_ac.ac} x {allowance_multiplier} = {p_ac.aac}",
                "Coins (Above Limit)": str(p_ac.lc),
                "Coins (Overspend Charge)": f"{p_ac.lc} x {overspend_multiplier} = {p_ac.alc}",
                "Coins (Adjusted)": f"{p_ac.fc} + {p_ac.aac} + {p_ac.alc} = {p_ac.coins}",
            }

    # Now just pre-tty-print the invoice
    pprint(invoice)


def _calculate_adjusted_coins(total_coins: Decimal,
                              allowance: Decimal,
                              allowance_multiplier: Decimal,
                              limit: Decimal,
                              overspend_multiplier: Decimal) -> AdjustedCoins:
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

    allowance_band: Decimal = limit - allowance

    if total_coins > allowance:
        allowance_coins = min(total_coins - allowance, allowance_band)
        adjusted_allowance_coins = allowance_coins * allowance_multiplier
    if total_coins > limit:
        limit_coins = total_coins - limit
        adjusted_limit_coins = limit_coins * overspend_multiplier

    adjusted_coins: Decimal = free_coins + adjusted_allowance_coins + adjusted_limit_coins

    return AdjustedCoins(coins=adjusted_coins,
                         fc=free_coins,
                         ac=allowance_coins,
                         aac=adjusted_allowance_coins,
                         lc=limit_coins,
                         alc=adjusted_limit_coins)


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="coins",
        description="Calculates a Product's Coin Charges (actual and predicted)"
    )
    parser.add_argument('product', type=str, help='The Product UUID')
    args: argparse.Namespace = parser.parse_args()

    main(args)
