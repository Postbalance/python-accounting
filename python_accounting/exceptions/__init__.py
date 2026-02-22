# exceptions/__init__.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Provides exceptions arising from accounting operations.

"""


class AccountingException(Exception):
    """Base accounting exception

    Attributes:
        msg (str): Human readable string describing the exception.
    """

    message: str

    def __str__(self) -> str:
        return f"{self.message}"


class AdjustingReportingPeriodError(AccountingException):
    """
    Only Journal Entry Transactions can be recorded for adjusting status Reporting Periods.

    Args:
        reporting_period (ReportingPeriod): The Reporting Period in question.
    """

    def __init__(self, reporting_period) -> None:
        self.message = f"""Only Journal Entry Transactions can be recorded for Reporting
         Period: {reporting_period} which has the Adjusting Status."""
        super().__init__()


class ClosedReportingPeriodError(AccountingException):
    """
    Transactions cannot be recorded for closed reporting periods.

    Args:
        reporting_period (ReportingPeriod): The Reporting Period in question.
    """

    def __init__(self, reporting_period) -> None:
        self.message = f"""Transaction cannot be recorded because Reporting
         Period: {reporting_period} is Closed."""
        super().__init__()


class DuplicateReportingPeriodError(AccountingException):
    """An Entity can only have one reporting period per calendar year."""

    def __init__(self) -> None:
        self.message = "A reporting Period already exists for that calendar year."
        super().__init__()


class InvalidAccountTypeError(AccountingException):
    """
    The account type must be one of those given in the list.

    Args:
        message (str): A string containing the list of allowed Account Types.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()


class HangingTransactionsError(AccountingException):
    """
    The account cannot be deleted because it has Transactions in the current reporting period.

    Args:
        model (DeclarativeBase): The model to be deleted.
    """

    def __init__(self, model) -> None:
        self.message = f"""The {model} cannot be deleted because it has Transactions in
         the current reporting period."""
        super().__init__()


class InvalidBalanceAccountError(AccountingException):
    """Income Statement Accounts cannot have an opening balance."""

    def __init__(self) -> None:
        self.message = "Income Statement Accounts cannot have an opening balance."
        super().__init__()


class InvalidBalanceDateError(AccountingException):
    """
    Unless the Entity allows for mid year balances, the balance date must be earlier than
    its reporting period's start.
    """

    def __init__(self) -> None:
        self.message = "Transaction date must be earlier than the first day of the Balance's Reporting Period."  # pylint: disable=line-too-long
        super().__init__()


class InvalidBalanceTransactionError(AccountingException):
    """Balance Transaction must be one of Client Invoice, Supplier Bill or Journal Entry."""

    def __init__(self) -> None:
        self.message = "Balance Transaction must be one of Client Invoice, Supplier Bill or Journal Entry."  # pylint: disable=line-too-long
        super().__init__()


class InvalidCategoryAccountTypeError(AccountingException):
    """
    The account type must the same as the category account type.

    Args:
         account_type (Account.AccountType): The account type of the Account.
         category_account_type (Account.AccountType): The account type of the Category.
    """

    def __init__(self, account_type, category_account_type) -> None:
        self.message = (
            f"Cannot assign {account_type} Account to {category_account_type} Category."
        )
        super().__init__()


class InvalidLineItemAccountError(AccountingException):
    """
    The Line Item main Account type must be one of those given in the list.

    Args:
         classname (Transaction.TransactionType): The type of the Transaction.
         account_types (list): The list of allowed Account types for the Transaction.
    """

    def __init__(self, classname, account_types: list) -> None:
        self.message = f"""{classname} Transaction Line Item Account type must
         be one of: {', '.join(account_types)}."""
        super().__init__()


class InvalidMainAccountError(AccountingException):
    """
    The account type of the transaction must be of the type given.

    Args:
         classname (Transaction.TransactionType): The type of the Transaction.
         account_type (str): The allowed Account type for the Transaction.
    """

    def __init__(self, classname, account_type: str) -> None:
        self.message = (
            f"{classname} Transaction main Account be of type {account_type}."
        )
        super().__init__()


class InvalidTaxAccountError(AccountingException):
    """A Tax account must be of type Control."""

    def __init__(self) -> None:
        self.message = "A Tax account must be of type Control."
        super().__init__()


class InvalidTaxChargeError(AccountingException):
    """
    A Contra Entry Transaction cannot be charged Tax.

    Args:
         classname (Transaction.TransactionType): The type of the Transaction."""

    def __init__(self, classname) -> None:
        self.message = f"{classname} Transactions cannot be charged Tax."
        super().__init__()


class InvalidTransactionDateError(AccountingException):
    """The Transaction date cannot be the exact beginning of the reporting period."""

    def __init__(self) -> None:
        self.message = "The Transaction date cannot be at the exact start of the Reporting Period. Use a Balance object instead."  # pylint: disable=line-too-long
        super().__init__()


class InvalidTransactionTypeError(AccountingException):
    """The Transaction type cannot be changed as this would bypass subclass validations."""

    def __init__(self) -> None:
        self.message = "The Transaction type cannot be changed as this would bypass subclass validations."  # pylint: disable=line-too-long
        super().__init__()


class MissingEntityError(AccountingException):
    """Accounting objects must all be associated with an Entity."""

    def __init__(self) -> None:
        self.message = "Accounting objects must have an Entity."
        super().__init__()


class MissingLineItemError(AccountingException):
    """A Transaction must have at least one Line Item to be posted."""

    def __init__(self) -> None:
        self.message = "A Transaction must have at least one Line Item to be posted."
        super().__init__()


class MissingMainAccountAmountError(AccountingException):
    """A Compound Journal Entry Transaction must have a main account amount."""

    def __init__(self) -> None:
        self.message = (
            "A Compound Journal Entry Transaction must have a main account amount."
        )
        super().__init__()


class MissingReportingPeriodError(AccountingException):
    """The Entity does not have a reporting period for the given date."""

    def __init__(self, entity, year) -> None:
        self.message = f"Entity <{entity}> has no reporting period for the year {year}."
        super().__init__()


class MissingTaxAccountError(AccountingException):
    """A non Zero Rate Tax must have an associated control account."""

    def __init__(self) -> None:
        self.message = "A non Zero Rate Tax must have an associated Control Account."
        super().__init__()


class MultipleOpenPeriodsError(AccountingException):
    """An Entity can only have one reporting period open at a time."""

    def __init__(self) -> None:
        self.message = (
            "There can only be one Open Reporting Period per Entity at a time."
        )
        super().__init__()


class NegativeValueError(AccountingException):
    """
    Accounting amounts should not be negative.

    Args:
         classname (DeclarativeBase): The model in question.
         attribute : The model attribute that must be greater than zero.
    """

    def __init__(self, classname, attribute="amount") -> None:
        self.message = f"{classname} {attribute} cannot be negative."
        super().__init__()


class PostedTransactionError(AccountingException):
    """Changes are not allowed for a posted Transaction.

    Args:
         message (str): The changes that are not allowed for a posted Transaction.
    """

    def __init__(self, message) -> None:
        self.message = message
        super().__init__()


class RedundantTransactionError(AccountingException):
    """
    A Transaction main account cannot be used as the account for any of its Line Items.

    Args:
         line_item (LineItem): The line item in question.
    """

    def __init__(self, line_item) -> None:
        self.message = (
            f"Line Item <{line_item}> Account is the same as the Transaction Account."
        )
        super().__init__()


class SessionEntityError(AccountingException):
    """The Session Entity should not be deleted."""

    def __init__(self) -> None:
        self.message = "Cannot delete the session Entity."
        super().__init__()


class UnbalancedTransactionError(AccountingException):
    """Total Debit amounts do not match total Credit amounts."""

    def __init__(self) -> None:
        self.message = "Total Debit amounts do not match total Credit amounts."
        super().__init__()


class UnassignableTransactionError(AccountingException):
    """
    The Transaction type must be one of those given in the list.

    Args:
         line_item (LineItem): The line item in question.
    """

    def __init__(self, classname, transaction_types: list) -> None:
        self.message = f"""{classname} Transaction cannot be assigned. Assignment
         Transaction type must be one of: {', '.join(transaction_types)}."""
        super().__init__()


class UnclearableTransactionError(AccountingException):
    """
    The Transaction type must be one of those given in the list.

    Args:
         classname (Transaction.TransactionType): The type of the Transaction.
         transaction_types (list): The list of allowed Transactiom types for the Assignment.
    """

    def __init__(self, classname, transaction_types: list) -> None:
        self.message = f"""{classname} Transaction cannot be cleared. Assignment
         assigned transaction type be must one of: {', '.join(transaction_types)}."""
        super().__init__()


class UnpostedAssignmentError(AccountingException):
    """An unposted Transaction cannot be cleared or assigned."""

    def __init__(self) -> None:
        self.message = "An unposted Transaction cannot be cleared or assigned."
        super().__init__()


class SelfClearanceError(AccountingException):
    """A Transaction cannot clear/be assigned to itself."""

    def __init__(self) -> None:
        self.message = "A Transaction cannot clear/be assigned to itself."
        super().__init__()


class InvalidAssignmentAccountError(AccountingException):
    """The main account for the cleared and clearing Transaction must be the same."""

    def __init__(self) -> None:
        self.message = "The main account for the cleared and clearing Transaction must be the same."
        super().__init__()


class InvalidClearanceEntryTypeError(AccountingException):
    """
    Transaction Entry increases the Main Account outstanding balance instead of reducing it.

    Args:
         entry_type (Balance.BalanceType): The type of the Transaction entry.
    """

    def __init__(self, entry_type: str) -> None:
        self.message = f"""Transaction {entry_type} entry increases the outstaning balance
         on the account instead of reducing it."""
        super().__init__()


class CompoundTransactionAssignmentError(AccountingException):
    """A compound Transaction cannot be cleared or assigned."""

    def __init__(self) -> None:
        self.message = "A compound Transaction cannot be cleared or assigned."
        super().__init__()


class InsufficientBalanceError(AccountingException):
    """
    Assigning Transaction does not have suffecient balance to
    clear the amount specified of the assigned.

    Args:
         assigning (str): The type of the Transaction to be assigned.
         amount (Decimal): The amount to be assigned.
         assigned (str): The type of the Transaction to be cleared.

    """

    def __init__(self, assigning: str, amount: float, assigned: str) -> None:
        self.message = f"""{assigning} Transaction doesn't not have sufficient balance
         available to clear {amount} of the {assigned} Transaction."""
        super().__init__()


class OverclearanceError(AccountingException):
    """
    The assigned Transaction has already been completely cleared.

    Args:
         assigned (str): The type of the Transaction to be cleared.
    """

    def __init__(self, assigned: str) -> None:
        self.message = (
            f"The {assigned} Transaction has already been completely cleared."
        )
        super().__init__()


class MixedAssignmentError(AccountingException):
    """
    An assigned/cleared cannot be cleared/assigned.

    Args:
         previous (str): The role played by the Transaction in a previous Assignment.
         current (str): The role played by the Transaction in the current Assignment.
    """

    def __init__(self, previous: str, current: str) -> None:
        self.message = f"A Transaction that has been {previous} cannot be {current}."
        super().__init__()
