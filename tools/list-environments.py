#!/usr/bin/env python
"""Prints the available environments.
"""
import sys
from typing import List

from squonk2.environment import Environment

environments: List[str] = Environment.load()
if not environments:
    print("No environments found")
    sys.exit(1)

index: int = 1
for environment in environments:
    if index == 1:
        print(f"{index}. {environment} (default)")
        first = False
    else:
        print(f"{index}. {environment}")
    index += 1
