# Refactoring Opportunities

## ~~1. Transaction Type Duplication~~ (Complete)

~~All 10 transaction types (`CashSale`, `ClientInvoice`, `CreditNote`, `ClientReceipt`, `CashPurchase`, `SupplierBill`, `DebitNote`, `SupplierPayment`, `ContraEntry`, `JournalEntry`) have nearly identical `__init__` methods — ~37 lines each, totaling ~370 lines of duplicated boilerplate. Each one does the same thing: sets `main_account_types`, `credited`, `transaction_type`, and an `account_type_map`.~~

Resolved: Replaced `__init__` boilerplate with declarative class-level attributes (`_main_account_types`, `_credited`, `_line_item_types`, `_account_type_map`, `_no_tax`). Base `Transaction.__init__` resolves string declarations via `_configure_from_class_attrs()`. Removed 12 late imports. Added 52 characterization tests in `tests/test_transaction_config.py`.

## ~~2. Account.statement() is 160 Lines~~ (Complete)

~~The `Account.statement()` method combines two distinct concerns:~~
~~- Generating account statements (transaction listings with running balances)~~
~~- Generating account schedules (for receivables/payables)~~

Resolved: Split into `statement()` (chronological transaction listing with running balance), `schedule()` (outstanding clearable transactions with aging for RECEIVABLE/PAYABLE accounts), and `_ledger_transactions()` (shared base query). Removed the `schedule: bool` parameter from `statement()`. Updated callers in `aging_schedule.py` and `assigning.py`. Added characterization tests in `tests/test_account_schedule.py`.

## 3. Deep Mixin Inheritance Chains (Critical)

Transaction classes use 3-4 levels of multiple inheritance. For example:
- `ClientInvoice(SellingMixin, ClearingMixin, Transaction)`
- `SellingMixin → TradingMixin`
- `Transaction → IsolatingMixin, Recyclable`

The MRO complexity makes the code hard to reason about and debug. Consider replacing deep inheritance with composition.

## 4. Circular Import Workarounds (High)

There are ~20 late imports (`from python_accounting.models import Account` inside `__init__` methods) throughout the codebase to avoid circular dependencies. This indicates the models module needs restructuring, potentially into sub-packages:
- `models/core/` (Entity, Account, Currency)
- `models/transactions/` (Transaction, LineItem)
- `models/ledger/` (Ledger, Balance)

## 5. Ledger Posting Logic (High)

Posting logic is split across `Transaction` and `Ledger` models with complex recursive methods (`_post_simple()`, `_post_compound()`, `_allocate_amount()`). Could be extracted into a dedicated `LedgerPostingEngine` that's easier to test in isolation.

## 6. Report Generation (High)

Reports have hardcoded formulas and section calculations in `__init__`. There is no shared abstraction for report generation — each report reimplements formatting and section logic. A template-based or strategy pattern approach would reduce duplication and make it easier to add new report types.

## 7. Validation Scattered (Medium)

Validation logic is spread across:
- `validate()` methods on models
- Mixin methods (e.g., `_validate_subclass_line_items()`)
- SQLAlchemy event listeners (`before_flush`)

Patterns are inconsistent. Could benefit from a centralized validation framework with composable validation rules.

## 8. ~~Base Exception Typo~~ (Complete)

~~The base exception class is named `AccountingExeption` (missing 'c' in Exception). This typo propagates to all 37 custom exception classes. Simple rename but touches many files.~~

Resolved: Renamed `AccountingExeption` → `AccountingException`. Added tests for the base exception class.

## Suggested Priority Order

1. ~~**Exception typo fix** (#8) — Quick win, low risk warm-up~~ Done
2. ~~**Transaction duplication** (#1) — Highest line-count reduction~~ Done
3. ~~**Account.statement() split** (#2) — Improves cohesion~~ Done
4. **Flatten mixin hierarchy** (#3) — Simplifies inheritance
5. **Resolve circular imports** (#4) — Enables better structure
6. **Extract ledger posting engine** (#5) — Isolates complex logic
7. **Report generation abstraction** (#6) — Consolidates formulas
8. **Centralize validation** (#7) — Standardizes validation flow
