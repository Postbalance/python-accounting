# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python Accounting is a comprehensive Double Entry Bookkeeping library focused on generating IFRS and GAAP-compliant financial reports. The library supports multi-entity accounting, transaction integrity via cryptographic hashing, and extensive reporting capabilities including receivables, payables, and aging schedules.

- **Tech Stack**: Python 3.9+, SQLAlchemy 2.0+, Pytest
- **Dependencies**: Uses uv for package management
- **Database Support**: MySQL/MariaDB, PostgreSQL, SQLite (testing only)
- **Documentation**: Available on [ReadTheDocs](https://python-accounting.readthedocs.io)

## Development Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_transaction.py

# Run specific test
uv run pytest tests/test_transaction.py::test_function_name

# Run tests with verbose output
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=python_accounting
```

### Linting
```bash
# Run pylint on the main package
uv run pylint ./python_accounting

# Run pylint on specific file
uv run pylint python_accounting/models/transaction.py
```

### Documentation
```bash
# Build docs locally (from docs directory)
cd docs
make html
```

## Architecture & Key Concepts

### Core Domain Model

The library is structured around standard accounting concepts with SQLAlchemy ORM models:

1. **Entity & Reporting Period**
   - `Entity`: Represents a company/organization. Each entity has isolated data.
   - `ReportingPeriod`: Auto-created for each entity on first transaction. Tracks accounting periods.
   - Entity isolation enforced via `IsolatingMixin` and SQLAlchemy event listeners.

2. **Chart of Accounts**
   - `Account`: Represents a ledger account with a specific `AccountType`.
   - Account types defined in `config.toml` and mapped to financial statement sections.
   - Types include: BANK, RECEIVABLE, PAYABLE, OPERATING_REVENUE, OPERATING_EXPENSE, etc.
   - Account codes auto-assigned based on type (e.g., BANK accounts: 3000-3999).

3. **Transactions**
   - Base `Transaction` model (in `models/transaction.py`) represents source documents.
   - Specific transaction types in `transactions/` directory (e.g., `CashSale`, `ClientInvoice`).
   - Each transaction type uses mixins (`SellingMixin`, `BuyingMixin`, `ClearingMixin`, `AssigningMixin`) for behavior.
   - Transactions must be `.post(session)` to record entries in the Ledger.

4. **Line Items**
   - `LineItem`: Represents the other side of double-entry for a transaction.
   - Line items are added to transactions via `transaction.line_items.add(line_item)`.
   - Support quantity, amount, and tax calculations.

5. **Ledger & Hashing**
   - `Ledger`: Immutable record of all posted transactions (double-entry records).
   - Each ledger entry is cryptographically hashed (see `database/event_listeners.py`).
   - Hash protects against tampering via direct database manipulation.
   - Hash algorithm and salt configured in `config.toml`.

6. **Assignments & Clearing**
   - `Assignment`: Links payment/receipt transactions to invoices/bills.
   - Used to track which invoices have been paid and outstanding balances.
   - Clearing tracked via `cleared()` and `balance()` methods.

### Transaction Flow

The standard workflow for creating a transaction:

```python
# 1. Create transaction (not yet posted)
transaction = CashSale(
    narration="Description",
    transaction_date=datetime.now(),
    account_id=bank_account.id,
    entity_id=entity.id,
)
session.add(transaction)
session.flush()  # Save but don't post to ledger

# 2. Add line items (the other side of double entry)
line_item = LineItem(
    narration="Line item description",
    account_id=revenue_account.id,
    amount=100,
    tax_id=tax.id,
    entity_id=entity.id,
)
session.add(line_item)
session.flush()

# 3. Link line item to transaction
transaction.line_items.add(line_item)
session.add(transaction)

# 4. Post to ledger (creates immutable ledger entries)
transaction.post(session)
```

### Configuration System

All accounting behavior is configured via `config.toml`:
- **Account types**: Labels, codes, and ranges
- **Transaction types**: Labels and prefixes for transaction numbers
- **Report structure**: Section definitions for each financial statement
- **Aging schedule**: Brackets for aging receivables/payables
- **Hashing**: Algorithm and salt for ledger integrity
- **Database**: Connection URL and settings

Access config via: `from python_accounting.config import config`

### Database Event Listeners

Key SQLAlchemy event listeners in `database/event_listeners.py`:
- **Recycling filter**: Automatically excludes soft-deleted records (unless `include_deleted=True`)
- **Entity isolation**: Filters all queries by current session entity (unless `ignore_isolation=True`)
- **Auto-indexing**: Assigns sequential numbers to accounts and transactions
- **Ledger hashing**: Automatically hashes ledger entries after insert
- **Validation**: Runs model `.validate()` method before flush

### Mixins

Mixins provide reusable accounting behaviors:
- `IsolatingMixin`: Adds `entity_id` and entity isolation
- `SellingMixin`: Validates selling transactions (revenue accounts)
- `BuyingMixin`: Validates purchasing transactions (expense/asset accounts)
- `ClearingMixin`: Adds clearable transaction behavior (invoices, bills)
- `AssigningMixin`: Adds assignable transaction behavior (receipts, payments)

### Reports

Financial reports in `reports/` directory:
- `IncomeStatement`: P&L statement
- `BalanceSheet`: Statement of financial position
- `CashflowStatement`: Cash flow statement
- `TrialBalance`: List of all account balances
- `AgingSchedule`: Receivables/payables aging analysis

Reports are configured in `config.toml` with section definitions that map account types to report sections.

### Soft Deletion (Recyclable)

All models inherit from `Recyclable` base class:
- `deleted_at`: Soft delete timestamp (can be restored)
- `destroyed_at`: Hard delete timestamp (permanent)
- `Recycled`: Tracks deletion history
- Soft-deleted records excluded by default via event listener

## Testing Conventions

- Tests use in-memory SQLite database (configured in `config.toml`)
- Fixtures in `tests/conftest.py` provide: `engine`, `session`, `entity`, `currency`
- Each test typically creates accounts, transactions, and verifies ledger entries or reports
- Tests are comprehensive with extensive validation of accounting rules

## Common Patterns

### Creating Test Data
```python
# Setup in conftest provides: session, entity, currency
account = Account(
    name="Test Account",
    account_type=Account.AccountType.BANK,
    currency_id=currency.id,
    entity_id=entity.id,
)
session.add(account)
session.commit()
```

### Querying with Session Context
```python
from python_accounting.database.session import get_session

with get_session(engine) as session:
    # session.entity auto-set from first added entity
    # All queries automatically filtered by entity_id
    accounts = session.query(Account).all()
```

### Accessing Transaction Balances
```python
# For clearable transactions (invoices, bills)
invoice.cleared(session)  # Amount cleared via assignments
invoice.balance(session)  # Outstanding balance

# For assignable transactions (receipts, payments)
receipt.balance(session)  # Unassigned amount available
```

## Important Notes

- **Transaction Immutability**: Once posted, transactions create immutable ledger entries. Cannot be edited directly.
- **Double Entry**: Every transaction must balance (debits = credits). Enforced by validation.
- **Entity Isolation**: All models are entity-scoped. Cross-entity queries require `ignore_isolation=True`.
- **Reporting Periods**: Auto-created based on calendar year. Closed periods prevent modifications.
- **Tax Handling**: Taxes automatically posted to control accounts when line items include `tax_id`.
- **Main Account Amounts**: For compound transactions (Journal Entry), use `main_account_amount` to specify the main account's amount.

## Development Methodology

- **Red/Green/Refactor TDD**: All development follows Test-Driven Development
  1. **Red**: Write a failing test first
  2. **Green**: Write the minimum code to make the test pass
  3. **Refactor**: Clean up while keeping tests green
- **Tests before code — always**, unless there is a first-class reason not to (e.g. requires a live API key, LLM integration, or other external dependency that cannot be reasonably mocked)
- When a first-class exception applies, document the reason in a comment near the code

## Commit Message Conventions

- **Do not include any authorship, co-authorship, or attribution notes** in commit messages or any documentation
- Commit messages should be clear and concise, focusing on the what and why of the change
