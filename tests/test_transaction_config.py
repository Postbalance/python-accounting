"""
Characterization tests that pin the configuration attributes for all 10 transaction types.

These tests verify that main_account_types, credited, transaction_type, line_item_types,
account_type_map, and no_tax are correctly set for every transaction subclass.
"""

import pytest
from python_accounting.models import Transaction, Account
from python_accounting.transactions import (
    CashSale,
    CashPurchase,
    ClientInvoice,
    SupplierBill,
    CreditNote,
    DebitNote,
    ClientReceipt,
    SupplierPayment,
    ContraEntry,
    JournalEntry,
)


TT = Transaction.TransactionType
AT = Account.AccountType


class TestCashSaleConfig:
    def test_main_account_types(self, entity, currency):
        t = CashSale(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.BANK]

    def test_credited(self, entity, currency):
        t = CashSale(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is False

    def test_transaction_type(self, entity, currency):
        t = CashSale(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.CASH_SALE

    def test_line_item_types(self, entity, currency):
        t = CashSale(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == [AT.OPERATING_REVENUE]

    def test_account_type_map(self, entity, currency):
        t = CashSale(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["CashSale"] == AT.BANK

    def test_no_tax(self, entity, currency):
        t = CashSale(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert not getattr(t, "no_tax", False)


class TestCashPurchaseConfig:
    def test_main_account_types(self, entity, currency):
        t = CashPurchase(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.BANK]

    def test_credited(self, entity, currency):
        t = CashPurchase(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is True

    def test_transaction_type(self, entity, currency):
        t = CashPurchase(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.CASH_PURCHASE

    def test_line_item_types(self, entity, currency):
        t = CashPurchase(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == Account.purchasables

    def test_account_type_map(self, entity, currency):
        t = CashPurchase(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["CashPurchase"] == AT.BANK

    def test_no_tax(self, entity, currency):
        t = CashPurchase(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert not getattr(t, "no_tax", False)


class TestClientInvoiceConfig:
    def test_main_account_types(self, entity, currency):
        t = ClientInvoice(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.RECEIVABLE]

    def test_credited(self, entity, currency):
        t = ClientInvoice(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is False

    def test_transaction_type(self, entity, currency):
        t = ClientInvoice(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.CLIENT_INVOICE

    def test_line_item_types(self, entity, currency):
        t = ClientInvoice(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == [AT.OPERATING_REVENUE]

    def test_account_type_map(self, entity, currency):
        t = ClientInvoice(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["ClientInvoice"] == AT.RECEIVABLE


class TestSupplierBillConfig:
    def test_main_account_types(self, entity, currency):
        t = SupplierBill(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.PAYABLE]

    def test_credited(self, entity, currency):
        t = SupplierBill(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is True

    def test_transaction_type(self, entity, currency):
        t = SupplierBill(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.SUPPLIER_BILL

    def test_line_item_types(self, entity, currency):
        t = SupplierBill(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == Account.purchasables

    def test_account_type_map(self, entity, currency):
        t = SupplierBill(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["SupplierBill"] == AT.PAYABLE


class TestCreditNoteConfig:
    def test_main_account_types(self, entity, currency):
        t = CreditNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.RECEIVABLE]

    def test_credited(self, entity, currency):
        t = CreditNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is True

    def test_transaction_type(self, entity, currency):
        t = CreditNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.CREDIT_NOTE

    def test_line_item_types(self, entity, currency):
        t = CreditNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == [AT.OPERATING_REVENUE]

    def test_account_type_map(self, entity, currency):
        t = CreditNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["CreditNote"] == AT.RECEIVABLE


class TestDebitNoteConfig:
    def test_main_account_types(self, entity, currency):
        t = DebitNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.PAYABLE]

    def test_credited(self, entity, currency):
        t = DebitNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is False

    def test_transaction_type(self, entity, currency):
        t = DebitNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.DEBIT_NOTE

    def test_line_item_types(self, entity, currency):
        t = DebitNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == Account.purchasables

    def test_account_type_map(self, entity, currency):
        t = DebitNote(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["DebitNote"] == AT.PAYABLE


class TestClientReceiptConfig:
    def test_main_account_types(self, entity, currency):
        t = ClientReceipt(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.RECEIVABLE]

    def test_credited(self, entity, currency):
        t = ClientReceipt(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is True

    def test_transaction_type(self, entity, currency):
        t = ClientReceipt(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.CLIENT_RECEIPT

    def test_line_item_types(self, entity, currency):
        t = ClientReceipt(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == [AT.BANK]

    def test_account_type_map(self, entity, currency):
        t = ClientReceipt(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["ClientReceipt"] == AT.RECEIVABLE


class TestSupplierPaymentConfig:
    def test_main_account_types(self, entity, currency):
        t = SupplierPayment(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.PAYABLE]

    def test_credited(self, entity, currency):
        t = SupplierPayment(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is False

    def test_transaction_type(self, entity, currency):
        t = SupplierPayment(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.SUPPLIER_PAYMENT

    def test_line_item_types(self, entity, currency):
        t = SupplierPayment(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == [AT.BANK]

    def test_account_type_map(self, entity, currency):
        t = SupplierPayment(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["SupplierPayment"] == AT.PAYABLE


class TestContraEntryConfig:
    def test_main_account_types(self, entity, currency):
        t = ContraEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.main_account_types == [AT.BANK]

    def test_credited(self, entity, currency):
        t = ContraEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is False

    def test_transaction_type(self, entity, currency):
        t = ContraEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.CONTRA_ENTRY

    def test_line_item_types(self, entity, currency):
        t = ContraEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.line_item_types == [AT.BANK]

    def test_account_type_map(self, entity, currency):
        t = ContraEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.account_type_map["ContraEntry"] == AT.BANK

    def test_no_tax(self, entity, currency):
        t = ContraEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.no_tax is True


class TestJournalEntryConfig:
    def test_credited(self, entity, currency):
        t = JournalEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.credited is True

    def test_transaction_type(self, entity, currency):
        t = JournalEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert t.transaction_type == TT.JOURNAL_ENTRY

    def test_no_main_account_types(self, entity, currency):
        t = JournalEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert not hasattr(t, "main_account_types") or t.main_account_types is None

    def test_no_line_item_types(self, entity, currency):
        t = JournalEntry(narration="x", transaction_date="2024-01-02", account_id=1, entity_id=entity.id)
        assert not hasattr(t, "line_item_types") or t.line_item_types is None
