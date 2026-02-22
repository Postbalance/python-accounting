# transactions/credit_note.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Credit Note Transaction.

"""
from python_accounting.models import Transaction
from python_accounting.mixins import SellingMixin, AssigningMixin


class CreditNote(  # pylint: disable=too-many-ancestors
    SellingMixin, AssigningMixin, Transaction
):
    """Class for the Credit Note Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.CREDIT_NOTE,
    }
    _main_account_types = ["RECEIVABLE"]
    _credited = True
