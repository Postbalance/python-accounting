# transactions/debit_note.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Debit Note Transaction.

"""
from python_accounting.models import Transaction
from python_accounting.mixins import BuyingMixin, AssigningMixin


class DebitNote(  # pylint: disable=too-many-ancestors
    BuyingMixin, AssigningMixin, Transaction
):
    """Class for the Debit Note Transaction."""

    __tablename__ = None
    __mapper_args__ = {
        "polymorphic_identity": Transaction.TransactionType.DEBIT_NOTE,
    }
    _main_account_types = ["PAYABLE"]
    _credited = False
