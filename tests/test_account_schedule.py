import pytest
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from python_accounting.models import (
    Account,
    Balance,
    Transaction,
    LineItem,
    Tax,
    Assignment,
)
from python_accounting.transactions import (
    ClientInvoice,
    ClientReceipt,
    CreditNote,
    JournalEntry,
    SupplierBill,
    SupplierPayment,
    DebitNote,
)
from python_accounting.exceptions import InvalidAccountTypeError


def test_receivable_schedule(session, entity, currency):
    """Tests schedule for a receivable account returns outstanding clearable transactions."""
    client = Account(
        name="test client",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue = Account(
        name="test revenue",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    control = Account(
        name="test control",
        account_type=Account.AccountType.CONTROL,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    bank = Account(
        name="test bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([client, revenue, control, bank])
    session.commit()

    # opening balance
    date = datetime.now() - relativedelta(days=365)
    ob = Balance(
        transaction_date=date,
        transaction_type=Transaction.TransactionType.CLIENT_INVOICE,
        amount=45,
        balance_type=Balance.BalanceType.DEBIT,
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(ob)
    session.flush()

    # client invoice
    invoice = ClientInvoice(
        narration="Test invoice",
        transaction_date=datetime.now() - relativedelta(days=2),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(invoice)
    session.commit()

    line_item = LineItem(
        narration="Test line item",
        account_id=revenue.id,
        amount=100,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    invoice.line_items.add(line_item)
    session.add(invoice)
    session.flush()
    invoice.post(session)

    # partial receipt against opening balance
    receipt = ClientReceipt(
        narration="Test receipt",
        transaction_date=datetime.now(),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(receipt)
    session.commit()

    receipt_line = LineItem(
        narration="Receipt line",
        account_id=bank.id,
        amount=20,
        entity_id=entity.id,
    )
    session.add(receipt_line)
    session.flush()

    receipt.line_items.add(receipt_line)
    session.add(receipt)
    session.flush()
    receipt.post(session)

    assignment = Assignment(
        assignment_date=datetime.now(),
        transaction_id=receipt.id,
        assigned_id=ob.id,
        assigned_type=ob.__class__.__name__,
        entity_id=entity.id,
        amount=20,
    )
    session.add(assignment)
    session.flush()

    schedule = client.schedule(session)

    assert len(schedule["transactions"]) == 2
    assert schedule["transactions"][0].amount == 45
    assert schedule["transactions"][0].cleared_amount == 20
    assert schedule["transactions"][0].uncleared_amount == 25
    assert schedule["transactions"][0].age == 365

    assert schedule["transactions"][1].amount == 100
    assert schedule["transactions"][1].cleared_amount == 0
    assert schedule["transactions"][1].uncleared_amount == 100
    assert schedule["transactions"][1].age == 2

    assert schedule["total_amount"] == 145
    assert schedule["cleared_amount"] == 20
    assert schedule["uncleared_amount"] == 125


def test_payable_schedule(session, entity, currency):
    """Tests schedule for a payable account."""
    supplier = Account(
        name="test supplier",
        account_type=Account.AccountType.PAYABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    expense = Account(
        name="test expense",
        account_type=Account.AccountType.DIRECT_EXPENSE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    bank = Account(
        name="test bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([supplier, expense, bank])
    session.commit()

    # supplier bill
    bill = SupplierBill(
        narration="Test bill",
        transaction_date=datetime.now() - relativedelta(days=5),
        account_id=supplier.id,
        entity_id=entity.id,
    )
    session.add(bill)
    session.commit()

    line_item = LineItem(
        narration="Bill line item",
        account_id=expense.id,
        amount=200,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    bill.line_items.add(line_item)
    session.add(bill)
    session.flush()
    bill.post(session)

    schedule = supplier.schedule(session)

    assert len(schedule["transactions"]) == 1
    assert schedule["transactions"][0].amount == 200
    assert schedule["transactions"][0].cleared_amount == 0
    assert schedule["transactions"][0].uncleared_amount == 200
    assert schedule["transactions"][0].age == 5
    assert schedule["total_amount"] == 200
    assert schedule["uncleared_amount"] == 200


def test_schedule_rejects_invalid_account_type(session, entity, currency):
    """Tests that schedule raises InvalidAccountTypeError for non-receivable/payable accounts."""
    bank = Account(
        name="test bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(bank)
    session.commit()

    with pytest.raises(InvalidAccountTypeError):
        bank.schedule(session)


def test_schedule_with_end_date(session, entity, currency):
    """Tests that schedule respects the end_date parameter."""
    client = Account(
        name="test client",
        account_type=Account.AccountType.RECEIVABLE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue = Account(
        name="test revenue",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([client, revenue])
    session.commit()

    invoice = ClientInvoice(
        narration="Test invoice",
        transaction_date=datetime.now() - relativedelta(days=10),
        account_id=client.id,
        entity_id=entity.id,
    )
    session.add(invoice)
    session.commit()

    line_item = LineItem(
        narration="Test line item",
        account_id=revenue.id,
        amount=50,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    invoice.line_items.add(line_item)
    session.add(invoice)
    session.flush()
    invoice.post(session)

    end_date = datetime.now() - relativedelta(days=5)
    schedule = client.schedule(session, end_date)

    assert len(schedule["transactions"]) == 1
    assert schedule["transactions"][0].age == (end_date - invoice.transaction_date).days
