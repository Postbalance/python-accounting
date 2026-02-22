# transactions/cash_purchase.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Cash Purchase Transaction.

"""
from python_accounting.models import Transaction
from python_accounting.mixins import BuyingMixin


class CashPurchase(BuyingMixin, Transaction):  # pylint: disable=too-many-ancestors
    """Class for the Cash Purchase Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CASH_PURCHASE,
    }
    _main_account_types = ["BANK"]
    _credited = True
