# transactions/supplier_payment.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Supplier Payment Transaction.

"""
from python_accounting.models import Transaction
from python_accounting.mixins.trading import TradingMixin
from python_accounting.mixins import AssigningMixin


class SupplierPayment(
    # pylint: disable=too-many-ancestors
    TradingMixin,
    AssigningMixin,
    Transaction,
):
    """Class for the Supplier Payment Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.SUPPLIER_PAYMENT,
    }
    _main_account_types = ["PAYABLE"]
    _line_item_types = ["BANK"]
    _account_type_map = {"SupplierPayment": "PAYABLE"}
    _credited = False
