# mixins/selling.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Provides functionality to Transactions that can sell goods and services for an Entity.

"""

from python_accounting.mixins.trading import TradingMixin


# pylint: disable=too-few-public-methods
class SellingMixin(TradingMixin):
    """
    This class provides validation for Transaction that sell goods and services for an Entity.
    """

    _line_item_types = ["OPERATING_REVENUE"]
