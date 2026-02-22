# Using python-accounting with PostBalance

## Executive Summary

Python-Accounting is a mature double-entry bookkeeping library with strong financial reporting capabilities aligned with IFRS/GAAP standards. The codebase demonstrates excellent architectural patterns, comprehensive data validation, and transaction integrity mechanisms. However, there are several significant gaps and limitations for a TUI-based financial workstation like PostBalance.

---

## 1. AUDIT LOGGING AND USER TRACKING

### Current State

**Limited User Tracking:**
- **User Model** (`/Users/lc3/src/python-accounting/python_accounting/models/user.py`, lines 19-28): Only stores `name` and `email` fields. No tracking of which user performed actions.
  ```python
  class User(IsolatingMixin, Base):
      name: Mapped[str] = mapped_column(String(255))
      email: Mapped[str] = mapped_column(String(255))
  ```

- **Entity Relationship**: Users can belong to Entities (`entity.py`, lines 62-63) but there's no mechanism to associate database changes with specific users.

**Soft Deletion/Recycling** (`/Users/lc3/src/python-accounting/python_accounting/models/recycled.py`):
- Records deletion events with `deleted_at` and `destroyed_at` timestamps
- Tracks restoration via `Recycled` model with `restored_at` timestamp
- However, NO USER ID field to track WHO deleted/restored

**Base Timestamps** (`/Users/lc3/src/python-accounting/python_accounting/models/base.py`, lines 24-30):
- All models inherit `created_at` and `updated_at` timestamps
- These are updated automatically but NOT linked to users

**Ledger Hashing** (`/Users/lc3/src/python-accounting/python_accounting/models/ledger.py`, lines 235-271):
- Cryptographic hashing prevents tampering with posted ledger entries
- Hash includes ledger data but NOT user information
- Good for integrity but lacks audit trail

**Validation Events** (`/Users/lc3/src/python-accounting/python_accounting/database/event_listeners.py`, lines 120-124):
- SQLAlchemy event listeners call model `.validate()` before flush
- No audit logging of validation failures or changes

### Gaps for TUI Workstation

1. **No User Action Audit Trail**: Cannot track which user created/modified/deleted transactions
2. **No Change Logging**: No before/after change records
3. **No Period Closure Audit**: When periods transition from OPEN → ADJUSTING → CLOSED, no audit of who performed this
4. **No Report Generation Tracking**: Cannot log which user generated which report
5. **No Reconciliation Tracking**: No audit of reconciliation actions
6. **No Session/Login Tracking**: No way to track user login/logout or session duration

### Files for Reference
- User model: `/Users/lc3/src/python-accounting/python_accounting/models/user.py`
- Recycled model: `/Users/lc3/src/python-accounting/python_accounting/models/recycled.py`
- Event listeners: `/Users/lc3/src/python-accounting/python_accounting/database/event_listeners.py`

---

## 2. API SURFACE AND INTEGRATION POINTS

### Primary Integration Pattern

The library uses SQLAlchemy ORM directly. A TUI would interact through an `AccountingSession` class, which extends SQLAlchemy's `Session`:

**Session Architecture** (`/Users/lc3/src/python-accounting/python_accounting/database/session.py`, lines 20-59):
```python
class AccountingSession(
    SessionOverridesMixin, EventListenersMixin, AccountingFunctionsMixin, Session
):
    entity: Entity
```

Key entry points:
- **Session initialization**: `get_session(engine)` returns an `AccountingSession`
- **Entity scoping**: Session automatically filters queries by `session.entity`
- **Soft deletion**: Records excluded by default unless `include_deleted=True`

### High-Level Use Cases for TUI

**1. Create Accounts**
- Direct SQLAlchemy: Create `Account` model, add to session, commit
- Account codes auto-assigned via event listener (`event_listeners.py`, lines 87-108)
- Files: `/Users/lc3/src/python-accounting/python_accounting/models/account.py` (lines 1-80)

**2. Post Transactions**
- Create Transaction subclass (e.g., `ClientInvoice`, `SupplierBill`)
- Add LineItems
- Call `transaction.post(session)` → creates immutable Ledger entries
- Files:
  - `/Users/lc3/src/python-accounting/python_accounting/models/transaction.py` (lines 228-250)
  - `/Users/lc3/src/python-accounting/python_accounting/models/ledger.py` (lines 221-233)

**3. Run Reports**
```python
from python_accounting.reports import IncomeStatement, BalanceSheet, TrialBalance

report = IncomeStatement(session)  # with session.entity set
print(report)  # Returns formatted string
```
- Files: `/Users/lc3/src/python-accounting/python_accounting/reports/` directory
- Available reports:
  - `IncomeStatement` (P&L)
  - `BalanceSheet` (Statement of position)
  - `CashflowStatement`
  - `TrialBalance`
  - `AgingSchedule` (receivables/payables aging)

**4. Close Periods**
- Transition `ReportingPeriod.status` from OPEN → ADJUSTING → CLOSED
- Validation prevents posting to CLOSED periods
- Files: `/Users/lc3/src/python-accounting/python_accounting/models/reporting_period.py` (lines 35-46)

**5. Manage Assignments (Payments/Receipts)**
- Link receivables/payables to payments via `Assignment` model
- Use `transaction.balance(session)` to get available balance
- Use `transaction.bulk_assign(session)` for FIFO assignment
- Files:
  - `/Users/lc3/src/python-accounting/python_accounting/models/assignment.py` (lines 82-98)
  - `/Users/lc3/src/python-accounting/python_accounting/mixins/assigning.py` (lines 25-122)
  - `/Users/lc3/src/python-accounting/python_accounting/mixins/clearing.py` (lines 23-79)

### API Limitations

1. **No High-Level Service Layer**: Must interact directly with SQLAlchemy models
2. **No Batch/Bulk APIs**: Cannot bulk-insert transactions efficiently
3. **No Query Builders**: Must write SQLAlchemy queries manually
4. **No Search API**: No built-in search/filter helper methods beyond `statement()`
5. **No Export Functions**: No built-in CSV/XLSX/PDF export
6. **No REST/GraphQL Layer**: Library is ORM-only

### Key Classes for TUI Integration

| Class | Location | Purpose |
|-------|----------|---------|
| `AccountingSession` | `database/session.py` | Main database interaction |
| `Entity` | `models/entity.py` | Company/organization |
| `Account` | `models/account.py` | Ledger accounts |
| `Transaction` | `models/transaction.py` | Base transaction |
| `Transaction` subclasses | `transactions/*.py` | Specific transaction types (9 types) |
| `LineItem` | `models/line_item.py` | Double-entry side of transaction |
| `Assignment` | `models/assignment.py` | Payment/receipt matching |
| `ReportingPeriod` | `models/reporting_period.py` | Accounting period |
| `Ledger` | `models/ledger.py` | Immutable posted entries |
| Financial Reports | `reports/*.py` | Reporting classes |

---

## 3. MULTI-USER AND CONCURRENCY

### Current State

**Entity Isolation** (`database/event_listeners.py`, lines 57-69):
```python
# Entity filter applied to all queries automatically
if not execute_state.execution_options.get("ignore_isolation"):
    execute_state.statement = execute_state.statement.options(
        orm.with_loader_criteria(
            IsolatingMixin,
            lambda cls: cls.entity_id == session_entity_id
        )
    )
```

**Session Management** (`database/session.py`, lines 37-59):
- `get_session(engine)` creates per-request sessions
- Entity is detected from first added object or must be set explicitly
- No user context propagation

**Soft Deletion** (`database/session_overrides.py`, lines 44-74):
- Records marked `deleted_at = datetime.now()` (soft delete)
- `Recycled` table tracks deletion history
- Allows deletion without hard constraints

### Concurrency Issues

**No Pessimistic Locking:**
- No `SELECT ... FOR UPDATE` or row-level locks
- Period closure is susceptible to race conditions

**No Optimistic Locking:**
- No version columns for conflict detection
- Multiple users can modify same transaction simultaneously

**No Transaction Isolation Control:**
- Session isolation level not configurable
- Default SQLAlchemy behavior (database-dependent)

**Period Closure Not Thread-Safe** (`reporting_period.py`, lines 116-152):
```python
# No locks; multiple users could transition period simultaneously
if period.status == ReportingPeriod.Status.OPEN:
    period.status = ReportingPeriod.Status.ADJUSTING  # ← Race condition
```

**Assignment Operations Not Protected** (`assignment.py`, lines 99-170+):
- Validates but doesn't lock when creating assignments
- Multiple concurrent assignments could over-clear an invoice

### Gaps for Multi-User TUI

1. **No Built-in Concurrency Control**: Cannot safely handle multiple users in same entity
2. **No Period Lock**: Period closure vulnerable to race conditions
3. **No Posting Lock**: Multiple users could post same transaction twice
4. **No User Context**: Sessions don't track current user automatically
5. **No Optimistic Locking**: No version columns for conflict resolution
6. **No Connection Pooling Guidance**: Library doesn't document best practices

### Recommendations

For a multi-user TUI, you would need to:
1. Implement application-level pessimistic locking around period transitions
2. Add `version` columns for optimistic locking
3. Add `user_id` to track ownership
4. Use database-level constraints to prevent concurrent modifications
5. Implement row-level locking around posting operations

---

## 4. PERFORMANCE AND BULK OPERATIONS

### Current State

**Bulk Assign Method** (`mixins/assigning.py`, lines 85-122):
- Only method for bulk operations: `transaction.bulk_assign(session)`
- FIFO-based assignment of payments to invoices
- Iterates in Python, not optimized SQL

**Account Statement** (`models/account.py`, lines 261-330+):
- Retrieves all transactions for an account with balances
- Uses aliased Ledger with cartesian product (suppressed warning)
- Calculates opening/closing balances in Python

**Ledger Posting** (`models/ledger.py`, lines 175-233):
- Simple transactions: 1 insert per line item (2 ledger entries)
- Compound transactions: Recursive allocation algorithm
- Commits after each ledger entry (`session.commit()`)

### Performance Characteristics

| Operation | Approach | Performance |
|-----------|----------|-------------|
| Post simple transaction | Direct inserts | O(n) where n = line items; SLOW due to commit per entry |
| Post compound transaction | Recursive allocation | O(n²) worst case; multiple commits |
| Bulk assign | Python loop with flush | O(n) assignments; multiple flushes |
| Account statement | Full ledger scan | O(all ledger entries) for one account |
| Trial balance | Full scan of accounts | O(accounts) × O(ledger entries) |

### Limitations for Bulk Imports

1. **No Batch Insert API**: Transactions inserted one-at-a-time
2. **Commit-Per-Entry**: Ledger posts with `session.commit()` after each entry (VERY SLOW)
3. **Python-Based Aggregation**: Balances calculated in Python, not SQL
4. **No Insert Ignore**: Duplicate imports cause validation errors
5. **No Streaming**: Must load entire transaction set into memory
6. **No Progress Tracking**: No hooks for import progress callbacks

**Example bottleneck** (`ledger.py`, lines 203-219):
```python
session.add(tax_post)
session.flush()
session.add(tax_folio)
session.flush()
post.amount = folio.amount = amount
session.add(post)
session.flush()
session.add(folio)
session.commit()  # ← Commits after EVERY ledger entry!
```

For 1000 transactions with 2 line items each = 2000 ledger entries = 2000 commits = EXTREMELY SLOW

### Gaps for TUI Workstation

1. **Cannot Import 1000+ Transactions Efficiently**: Would take hours
2. **No Batch Post API**: Each transaction must be posted individually
3. **No Progress Tracking**: UI cannot show import progress
4. **No Transaction Rollback**: If one transaction fails, entire import affected
5. **No Streaming/Chunking**: Memory constraints for large files
6. **No Duplicate Detection**: Cannot skip already-imported transactions
7. **No Query Performance Tuning**: All account statements load full ledger

### Recommendations for TUI

1. Add batch posting API:
   ```python
   session.bulk_post(transactions)  # Batch posting with single commit
   ```
2. Optimize ledger posting to reduce commits
3. Add `duplicate_handling` parameter to transactions
4. Implement streaming import for large files
5. Cache account balances instead of recalculating each time
6. Add import/export progress callbacks

---

## 5. TRANSACTION LIFECYCLE AND CORRECTIONS

### Current State

**Transaction States:**
1. **Unposted**: Created but not posted to ledger
   - Can be modified (add/remove line items)
   - Can be deleted

2. **Posted**: Has ledger entries
   - Cannot be modified (frozen)
   - Cannot be deleted
   - Cannot be edited

**Correction Mechanisms:**

**1. Credit Notes/Debit Notes** (Reversals)
- `CreditNote`: Reversal for `ClientInvoice` (negative revenue)
- `DebitNote`: Reversal for `SupplierBill` (negative expense)
- Files:
  - `/Users/lc3/src/python-accounting/python_accounting/transactions/credit_note.py`
  - `/Users/lc3/src/python-accounting/python_accounting/transactions/debit_note.py`

**2. Contra Entry**
- Opposite transaction type (e.g., reverse a sale with a purchase)
- File: `/Users/lc3/src/python-accounting/python_accounting/transactions/contra_entry.py`

**3. Deletion (Unposted Only)**
- Soft delete: Sets `deleted_at` timestamp
- Tracked in `Recycled` table
- Can be restored: `session.restore(transaction)`
- Files: `/Users/lc3/src/python-accounting/python_accounting/database/session_overrides.py` (lines 44-94)

**Posting Validation** (`models/transaction.py`, lines 285-344):
```python
def validate(self, session) -> None:
    if self.is_posted:
        raise PostedTransactionError("A Posted Transaction cannot be modified.")
    # ... other validations
```

**No Direct Edit**: Posted transactions CANNOT be edited; only reversed via new transactions

### Gaps for TUI Workstation

1. **No Transaction Correction Workflow**: No single "Edit Transaction" feature
2. **No Adjustment/Amendment Transactions**: Must use reversal + new entry (clunky)
3. **No Bulk Corrections**: Cannot bulk-fix multiple transactions at once
4. **No Correction Tracking**: No link between original and correction
5. **No Reason/Comment on Reversals**: Why was this reversed?
6. **No Audit Trail of Corrections**: Cannot see correction history
7. **No Reversal Suggestions**: UI must know to create credit note
8. **No Auto-Reversal**: Cannot auto-reverse with a single action

### Workflow Comparison

**Current (Immutable Ledger):**
```
1. Post Invoice: INV/2024/0001
2. Need to fix → Create Credit Note: CN/2024/0001
3. Optionally reassign to correct invoice
```

**TUI Users Expect:**
```
1. Post Invoice
2. Click "Edit" → Shows form with current values
3. Change amount or other fields
4. Click "Save" → Auto-creates reversal + new entry (behind scenes)
```

---

## 6. REPORTING AND EXPORT

### Current State

**Available Reports:**

1. **IncomeStatement** (`reports/income_statement.py`)
   - P&L statement
   - Sections: Revenue, Expenses, Profit/Loss

2. **BalanceSheet** (`reports/balance_sheet.py`)
   - Statement of financial position
   - Sections: Assets, Liabilities, Equity

3. **CashflowStatement** (`reports/cashflow_statement.py`)
   - Cash inflows/outflows
   - Operating, Investing, Financing activities

4. **TrialBalance** (`reports/trial_balance.py`)
   - All accounts with debit/credit balances

5. **AgingSchedule** (`reports/aging_schedule.py`)
   - Receivables/Payables aging analysis
   - Brackets: Current, 31-90 days, 91-180 days, etc.

**Base Architecture** (`reports/financial_statement.py`, lines 42-78):
- Reports configured via `config.toml`
- Section structure defined in config
- Result enums for totals
- Printout tuples for string formatting

**Account Statement** (`models/account.py`, lines 261-330+):
- Per-account transaction listing
- Opening/closing balances
- Receivable/Payable schedules

**Report Output:**

```python
report = IncomeStatement(session)
print(report)  # Returns formatted string (text table)
```

Output is **text-only**, formatted with underlines and spacing:
```
Income Statement
================
Revenue
_______
  Operating Revenue        10,000.00

Expenses
________
  Operating Expense        -2,000.00

Net Profit
==========
                            8,000.00
```

### No Export Capabilities

**CRITICAL GAP**: Library has **ZERO** export functionality:
- No CSV export
- No XLSX/Excel export
- No PDF export
- No JSON export
- No XML export

Reports are text strings only, must be:
1. Printed to console
2. Copied/pasted
3. User manually converts to other formats

### Extensibility

**How to Add Custom Reports:**
1. Extend `FinancialStatement` class
2. Implement sections and results using config
3. Return printout tuple with formatted lines

**Example** (`reports/financial_statement.py`):
```python
class CustomReport(FinancialStatement):
    config = "custom_report"  # Must define in config.toml

    def __init__(self, session):
        super().__init__(session)
        # Custom report logic
```

Limited to text output unless you override string methods.

### Gaps for TUI Workstation

1. **No Export Formats**: Cannot export to CSV/XLSX/PDF
2. **No Report Scheduling**: Cannot schedule recurring reports
3. **No Comparative Reports**: Cannot compare multiple periods side-by-side
4. **No Custom Columns**: Cannot add custom fields to standard reports
5. **No Filtering**: Reports always full-period
6. **No Date Range Reports**: Must generate full-period reports
7. **No Drill-Down**: Cannot click into report totals to see details
8. **No Interactive Reports**: Text output only
9. **No Report Templates**: Cannot save custom report layouts
10. **No Email Distribution**: Cannot email reports

### Recommendations

For TUI, implement:
1. **Report Builder API**: Abstract report structure from SQLAlchemy queries
2. **Export Adapters**: CSV, XLSX (via openpyxl), JSON output formatters
3. **Filter/Date Range API**: `report.filter(start_date, end_date).export('csv')`
4. **Custom Column API**: Allow adding fields to standard reports
5. **Report Templates**: Save/restore custom report layouts
6. **Caching**: Cache report results for performance

---

## INTEGRATION POINTS: DETAILED REFERENCE

### 1. Core Models to Import

```python
from python_accounting.models import (
    Entity,           # Company/org
    Account,          # Ledger accounts
    Transaction,      # Base transaction type
    LineItem,         # Double-entry details
    Assignment,       # Payment/receipt matching
    ReportingPeriod,  # Accounting periods
    Ledger,           # Posted entries (immutable)
    Balance,          # Opening balances
    Currency,         # Multi-currency support
    User,             # Users (limited fields)
    Recycled,         # Deletion history
)
```

### 2. Transaction Types

```python
from python_accounting.transactions import (
    ClientInvoice,      # Sales invoice
    CreditNote,         # Sales return
    ClientReceipt,      # Customer payment
    SupplierBill,       # Purchase invoice
    DebitNote,          # Purchase return
    SupplierPayment,    # Supplier payment
    CashSale,           # Immediate sale
    CashPurchase,       # Immediate purchase
    JournalEntry,       # Manual posting
    ContraEntry,        # Opposite transaction
)
```

### 3. Session Management

```python
from python_accounting.database.session import get_session

# Create engine
from sqlalchemy import create_engine
engine = create_engine("sqlite://")

# Get session for entity
with get_session(engine) as session:
    session.entity = my_entity  # Set context
    # All queries auto-filtered by entity_id
    accounts = session.query(Account).all()
```

### 4. Key Methods by Use Case

| Use Case | Method | File |
|----------|--------|------|
| Create account | `Account(...)` + `session.add()` | `models/account.py` |
| List accounts | `session.query(Account).all()` | Standard SQLAlchemy |
| Post transaction | `transaction.post(session)` | `models/transaction.py:228-250` |
| Check if posted | `transaction.is_posted` property | `models/transaction.py:180-182` |
| Get posting security | `transaction.is_secure(session)` | `models/transaction.py:224-226` |
| Clear invoice | `assignment = Assignment(...)` | `models/assignment.py` |
| Get balance | `transaction.balance(session)` | `mixins/assigning.py:25-53` |
| Bulk assign | `transaction.bulk_assign(session)` | `mixins/assigning.py:85-122` |
| Get cleared amount | `transaction.cleared(session)` | `mixins/clearing.py:23-46` |
| Account statement | `account.statement(session, start, end, schedule=False)` | `models/account.py:261+` |
| Close period | `period.status = ReportingPeriod.Status.CLOSED` | `models/reporting_period.py:56` |
| Generate report | `IncomeStatement(session)` | `reports/income_statement.py` |
| Soft delete | `session.delete(model)` | `database/session_overrides.py:44-74` |
| Restore | `session.restore(model)` | `database/session_overrides.py:76-94` |
| Hard delete | `session.destroy(model)` | `database/session_overrides.py:96-110` |

---

## CRITICAL LIMITATIONS SUMMARY

### High Priority (Must Address for TUI)

1. **User Tracking**: No `user_id` field on models → Cannot audit who changed what
2. **Audit Logging**: No change history → Cannot explain transaction corrections
3. **Concurrency Control**: No locking → Race conditions in multi-user scenarios
4. **Bulk Operations**: Extremely slow for imports → Cannot handle large datasets
5. **Export**: No export API → Reports stuck in text format
6. **Error Recovery**: No transaction rollback on bulk operations → All-or-nothing

### Medium Priority (Impacts UX)

7. **Period Closure Audit**: No tracking of who closed periods
8. **Correction Workflow**: Reversal-based only → Clunky UX vs edit-in-place
9. **Search/Filter**: No built-in query helpers → TUI must write raw SQLAlchemy
10. **Balance Caching**: All balances recalculated → Performance hit for large charts
11. **Assignment Automation**: Only FIFO bulk assign → No partial/manual matching UI
12. **Report Filtering**: No date range filtering → Always full-period
13. **Reporting Period Management**: No locking on transitions → Could corrupt state

### Lower Priority (Nice to Have)

14. **API Documentation**: Limited docstrings on integration points
15. **Batch Exceptions**: No way to identify which transactions failed in bulk import
16. **Progress Callbacks**: No hooks for import progress UI
17. **Streaming**: Cannot process files larger than memory
18. **Duplicate Handling**: No skip-if-exists logic

---

## RECOMMENDATIONS FOR POSTBALANCE INTEGRATION

### Phase 1: Foundation (Required for MVP)

1. **Add Audit Logging Mixin**
   - Add `user_id` and `action` fields to core models
   - Create `AuditLog` table tracking all changes
   - Integrate with event listeners

2. **Implement Concurrency Control**
   - Add `version` columns for optimistic locking
   - Add row-level locks for period transitions
   - Document multi-user best practices

3. **Build High-Level Service Layer**
   - Wrap model operations (post_transaction, create_account, etc.)
   - Handle error cases and rollbacks
   - Provide progress callbacks for bulk operations

4. **Add Export Layer**
   - CSV exporter for reports
   - JSON exporter for API integration
   - XLSX exporter for Excel compatibility

### Phase 2: UX Improvements

5. **Implement Transaction Amendment Workflow**
   - `transaction.amend(session, new_values)` → Auto-reverses + posts correction
   - Track original transaction ID in amendment
   - Show amendment audit trail

6. **Add Query Builder**
   - Fluent API for filtering accounts, transactions
   - `Account.filter(name="Bank*").list(session)`
   - Chainable filters

7. **Optimize Posting**
   - Reduce commits in ledger posting (batch all entries)
   - Cache account balances
   - Implement lazy calculation for large ledgers

8. **Add Period Locking**
   - Lock periods during closure
   - Prevent concurrent modifications
   - Add closed-period audit trail

### Phase 3: Advanced Features

9. **Implement Batch Import API**
   - `session.import_transactions(file_path, format='csv')`
   - Progress callbacks
   - Duplicate detection
   - Rollback on error

10. **Add Reporting Templates**
    - Save/load custom report layouts
    - Parameterized reports
    - Scheduled report generation

11. **Implement Multi-Currency Management**
    - Exchange rate history
    - Currency revaluation calculations
    - Multi-currency reports

12. **Add Reconciliation Workflow**
    - Bank reconciliation
    - Payment reconciliation
    - Reconciliation audit trail

---

## CODE INTEGRATION PATTERNS

### Pattern 1: Create & Post Transaction

```python
from python_accounting.database.session import get_session
from python_accounting.transactions import ClientInvoice
from python_accounting.models import LineItem, Account

with get_session(engine) as session:
    session.entity = entity  # Set entity context

    # Create transaction (unposted)
    invoice = ClientInvoice(
        narration="Invoice for services",
        transaction_date=datetime.now(),
        account_id=receivable_account.id,
        entity_id=entity.id,
    )
    session.add(invoice)
    session.flush()  # Get ID without posting

    # Add line items
    line_item = LineItem(
        narration="Professional services",
        account_id=revenue_account.id,
        amount=Decimal("1000.00"),
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    invoice.line_items.add(line_item)
    session.add(invoice)

    # Post to ledger (creates immutable entries)
    try:
        invoice.post(session)
    except Exception as e:
        session.rollback()
        raise
```

### Pattern 2: Query Transactions for Account

```python
from python_accounting.models import Account, Transaction

account = session.get(Account, account_id)

# Get all transactions
stmt = account.statement(session,
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
    schedule=False  # Full statement, not aging schedule
)

print(f"Opening: {stmt['opening_balance']}")
for txn in stmt['transactions']:
    print(f"  {txn.transaction_no}: {txn.amount}")
print(f"Closing: {stmt['closing_balance']}")
```

### Pattern 3: Assign Payment to Invoice

```python
from python_accounting.transactions import ClientReceipt
from python_accounting.models import Assignment

# Create payment transaction
receipt = ClientReceipt(
    narration="Customer payment",
    transaction_date=datetime.now(),
    account_id=bank_account.id,
    entity_id=entity.id,
)
session.add(receipt)
session.flush()

# Add payment line item
payment_item = LineItem(
    narration="Payment received",
    account_id=receivable_account.id,
    amount=Decimal("500.00"),
    entity_id=entity.id,
)
session.add(payment_item)
receipt.line_items.add(payment_item)

# Post payment
receipt.post(session)

# Create assignment to invoice
assignment = Assignment(
    assignment_date=datetime.now(),
    transaction_id=receipt.id,
    assigned_id=invoice.id,
    assigned_type="ClientInvoice",
    amount=Decimal("500.00"),
    entity_id=entity.id,
)
session.add(assignment)
session.commit()

# Check cleared amount
cleared = invoice.cleared(session)  # Returns Decimal
balance = invoice.balance(session) if hasattr(invoice, 'balance') else 0
# Note: balance() is for AssigningMixin (payments), not ClearingMixin (invoices)
```

### Pattern 4: Close Period

```python
from python_accounting.models import ReportingPeriod

# Get current period
period = session.entity.reporting_period

# Transition to ADJUSTING (allows only Journal Entries)
period.status = ReportingPeriod.Status.ADJUSTING
session.add(period)
session.commit()

# After adjustments done, close period
period.status = ReportingPeriod.Status.CLOSED
session.add(period)
session.commit()

# Future transactions CANNOT be posted to closed period
# Will raise ClosedReportingPeriodError
```

### Pattern 5: Generate Report

```python
from python_accounting.reports import IncomeStatement, BalanceSheet, AgingSchedule

# Income statement (entire period)
income_stmt = IncomeStatement(session)
print(income_stmt)  # Text output

# Balance sheet
balance_sheet = BalanceSheet(session)
print(balance_sheet)

# Aging schedule (receivables aged 30/60/90 days)
aging = AgingSchedule(session)
print(aging)
```

### Pattern 6: Soft Delete & Restore

```python
# Delete (soft-delete)
session.delete(transaction)
session.commit()  # Sets deleted_at, creates Recycled record

# Later, restore
session.restore(transaction)
session.commit()  # Clears deleted_at, updates Recycled record

# Hard delete (permanent)
session.destroy(transaction)
session.commit()  # Sets destroyed_at (cannot be restored)
```

---

## FILE STRUCTURE REFERENCE

```
python_accounting/
├── models/                    # Core ORM models
│   ├── base.py               # Base class (id, created_at, updated_at)
│   ├── recyclable.py         # Soft delete mixin (deleted_at, destroyed_at)
│   ├── recycled.py           # Deletion history
│   ├── entity.py             # Company/organization
│   ├── user.py               # User (name, email only - LIMITED)
│   ├── currency.py           # Multi-currency support
│   ├── account.py            # Ledger accounts
│   ├── category.py           # Account grouping
│   ├── reporting_period.py   # Accounting periods (OPEN/ADJUSTING/CLOSED)
│   ├── transaction.py        # Base transaction (abstract)
│   ├── line_item.py          # Double-entry detail lines
│   ├── ledger.py             # Posted entries (immutable + hashed)
│   ├── balance.py            # Opening balances from prior periods
│   ├── assignment.py         # Payment/receipt matching
│   ├── tax.py                # Tax definitions
│   └── __init__.py           # Exports all models
├── transactions/             # Transaction subclasses
│   ├── client_invoice.py     # Customer sales invoice
│   ├── client_receipt.py     # Customer payment
│   ├── credit_note.py        # Sales return
│   ├── supplier_bill.py      # Vendor purchase invoice
│   ├── supplier_payment.py   # Vendor payment
│   ├── debit_note.py         # Purchase return
│   ├── cash_sale.py          # Point-of-sale
│   ├── cash_purchase.py      # Direct purchase
│   ├── journal_entry.py      # Manual posting
│   ├── contra_entry.py       # Opposite transaction
│   └── __init__.py
├── mixins/                   # Behavior mixins
│   ├── isolating.py          # Entity-scoped queries (entity_id filter)
│   ├── selling.py            # Revenue validation (SellingMixin)
│   ├── buying.py             # Expense validation (BuyingMixin)
│   ├── clearing.py           # Receivable/Payable marking (ClearingMixin)
│   ├── assigning.py          # Payment/receipt tracking (AssigningMixin)
│   ├── trading.py            # Currency trading
│   └── __init__.py
├── database/                 # Database layer
│   ├── engine.py             # Engine creation
│   ├── session.py            # AccountingSession (main entry point)
│   ├── session_overrides.py  # delete/restore/destroy operations
│   ├── accounting_functions.py # Period transitions, helpers
│   ├── event_listeners.py    # SQLAlchemy events (validation, hashing, isolation)
│   ├── database_init.py      # Schema creation
│   └── __init__.py
├── reports/                  # Financial reports
│   ├── financial_statement.py # Base report class (abstract)
│   ├── income_statement.py   # P&L
│   ├── balance_sheet.py      # Statement of position
│   ├── cashflow_statement.py # Cash flow
│   ├── trial_balance.py      # Account balances
│   ├── aging_schedule.py     # Receivable/Payable aging
│   └── __init__.py           # Exports report classes
├── config.py                 # Config loader
├── exceptions/               # Accounting-specific exceptions
│   └── __init__.py
└── utils/                    # Utility functions
    └── dates.py              # Date handling
```

---

## CONCLUSION

**Python-Accounting is production-ready for single-user systems** with strong financial reporting and transaction integrity. However, **it requires significant extensions for a multi-user TUI workstation like PostBalance**.

### Must-Have Additions:
1. User audit trail (who changed what, when)
2. Concurrency control (row locking, optimistic versions)
3. Bulk operation APIs (batch posting, imports)
4. Export functionality (CSV, XLSX)
5. Amendment/correction workflows
6. Period closure safeguards

### Time Estimate for Integration:
- **Phase 1 (Foundation)**: 4-6 weeks
- **Phase 2 (UX)**: 3-4 weeks
- **Phase 3 (Advanced)**: 4-6 weeks

The codebase is well-structured and extensible. Most gaps can be filled without modifying core models, though audit logging will require ORM-level changes. The CLAUDE.md file and comprehensive test suite make onboarding smooth.
