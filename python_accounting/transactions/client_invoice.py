# transactions/client_invoice.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Client Invoice Transaction.

"""
from python_accounting.models import Transaction
from python_accounting.mixins import SellingMixin, ClearingMixin


class ClientInvoice(  # pylint: disable=too-many-ancestors
    SellingMixin, ClearingMixin, Transaction
):
    """Class for the Client Invoice Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CLIENT_INVOICE,
    }
    _main_account_types = ["RECEIVABLE"]
    _credited = False
