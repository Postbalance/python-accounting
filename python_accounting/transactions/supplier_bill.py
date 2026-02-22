# transactions/supplier_bill.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Supplier Bill Transaction.

"""
from python_accounting.models import Transaction
from python_accounting.mixins import BuyingMixin, ClearingMixin


class SupplierBill(  # pylint: disable=too-many-ancestors
    BuyingMixin, ClearingMixin, Transaction
):
    """Class for the Supplier Bill Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.SUPPLIER_BILL,
    }
    _main_account_types = ["PAYABLE"]
    _credited = True
