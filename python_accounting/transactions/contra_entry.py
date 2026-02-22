# transactions/contra_entry.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Contra Entry Transaction.

"""
from python_accounting.models import Transaction
from python_accounting.mixins.trading import TradingMixin


class ContraEntry(TradingMixin, Transaction):  # pylint: disable=too-many-ancestors
    """Class for the Contra Entry Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CONTRA_ENTRY,
    }
    _main_account_types = ["BANK"]
    _line_item_types = ["BANK"]
    _account_type_map = {"ContraEntry": "BANK"}
    _credited = False
    _no_tax = True
