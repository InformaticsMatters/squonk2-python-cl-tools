"""Stuff that's used by more than one tool.
"""
from collections import namedtuple
import os
from typing import List, Optional

# The ID for an internal "test" unit
TEST_UNIT: str = "unit-11111111-1111-1111-1111-111111111111"

# The login names of the well-known set of test users.
TEST_USER_NAMES: List[str] = [
    "dmit-user-a",
    "dmit-user-b",
    "dmit-user-c",
    "dmit-user-d",
    "dmit-user-admin",
]
