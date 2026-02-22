# transactions/client_receipt.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Client Receipt Transaction.

"""
from python_accounting.models import Transaction
from python_accounting.mixins import AssigningMixin
from python_accounting.mixins.trading import TradingMixin


class ClientReceipt(  # pylint: disable=too-many-ancestors
    TradingMixin, AssigningMixin, Transaction
):
    """Class for the Client Receipt Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CLIENT_RECEIPT,
    }
    _main_account_types = ["RECEIVABLE"]
    _line_item_types = ["BANK"]
    _account_type_map = {"ClientReceipt": "RECEIVABLE"}
    _credited = True
