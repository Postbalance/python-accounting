# Proposed Upstream Enhancements to python-accounting

## Context

This document outlines proposed general-purpose enhancements to python-accounting that would benefit any production deployment, particularly multi-user systems. These proposals stem from work on **PostBalance**, a terminal-based financial workstation that uses python-accounting as its accounting engine.

The goal is to contribute meaningful improvements back to python-accounting while maintaining a clean separation between:
- **General-purpose accounting library features** (belong in python-accounting)
- **Application-specific features** (belong in PostBalance or other applications)

---

## Architecture Philosophy

### Proposed System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                Application Layer (PostBalance)          │
│  (TUI Interface, User Auth, Import Wizards, Reports)    │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│         Application Service Layer (PostBalance)         │
│  • User authentication & session management             │
│  • Import/export wizards (CSV, XLSX, PDF)               │
│  • Reconciliation workflows                             │
│  • Report formatting (terminal, PDF)                    │
│  • Application-specific business logic                  │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│           python-accounting (Enhanced)                  │
│  • Core double-entry accounting ✓                       │
│  • Transaction integrity & hashing ✓                    │
│  • Financial reports ✓                                  │
│  + User tracking (proposed)                             │
│  + Concurrency control (proposed)                       │
│  + Batch posting (proposed)                             │
│  + Correction tracking (proposed)                       │
│  + Report data export (proposed)                        │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                Database (PostgreSQL/SQLite)             │
└─────────────────────────────────────────────────────────┘
```

### Design Principle: Clean Separation

**python-accounting should remain:**
- A general-purpose accounting engine
- Framework-agnostic (usable from web apps, TUIs, CLIs, APIs)
- Focused on accounting fundamentals and GAAP/IFRS compliance
- Free of application-specific assumptions

**Applications (like PostBalance) should handle:**
- User interface concerns (web, TUI, API)
- Authentication and authorization
- Application-specific workflows
- Presentation formatting
- Import/export file parsing

---

## General-Purpose Enhancements (Suitable for python-accounting)

### 1. User Tracking & Audit Logging ✅

**Problem**: Currently, models track `created_at` and `updated_at` timestamps but not *who* made changes. This makes it impossible to:
- Track which user created/modified transactions
- Meet regulatory audit requirements (SOX, GDPR)
- Investigate errors or fraud
- Provide accountability in multi-user environments

**Proposed Solution**:

Add user tracking fields to base models:

```python
# models/base.py
class Base(Recyclable):
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    # NEW: User tracking
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    updated_by: Mapped["User"] = relationship("User", foreign_keys=[updated_by_id])
```

Add user context to session:

```python
# database/session.py
class AccountingSession(Session):
    entity: Entity
    current_user: User | None  # NEW: Track current user

    def set_user(self, user: User):
        """Set the current user for this session."""
        self.current_user = user
```

Add event listener to auto-populate user fields:

```python
# database/event_listeners.py
@event.listens_for(Session, "before_flush")
def auto_populate_user_fields(session, flush_context, instances):
    """Automatically populate created_by_id and updated_by_id."""
    if not hasattr(session, 'current_user') or session.current_user is None:
        return

    for instance in session.new:
        if hasattr(instance, 'created_by_id'):
            instance.created_by_id = session.current_user.id

    for instance in session.dirty:
        if hasattr(instance, 'updated_by_id'):
            instance.updated_by_id = session.current_user.id
```

**Benefits**:
- Regulatory compliance (audit trails)
- Accountability in multi-user systems
- Forensic investigation capabilities
- Backwards compatible (fields are nullable)

**Migration Strategy**:
- Fields are nullable for backwards compatibility
- Existing deployments can leave user tracking disabled
- New deployments can enable by calling `session.set_user(user)`

**Scope**: PR #3 (Medium risk, high value)

---

### 2. Concurrency Control ✅

**Problem**: Currently no locking mechanisms exist for:
- Period closures (multiple users could transition OPEN → ADJUSTING → CLOSED simultaneously)
- Transaction posting (race conditions possible)
- Assignment operations (could over-clear invoices)

This makes the library unsafe for production multi-user deployments.

**Proposed Solution**:

**A. Optimistic Locking (Version Column)**

Add version tracking for conflict detection:

```python
# models/transaction.py
class Transaction(Base):
    # ... existing fields ...
    version: Mapped[int] = mapped_column(default=1)

    __mapper_args__ = {
        "version_id_col": version  # SQLAlchemy automatic optimistic locking
    }

# models/reporting_period.py
class ReportingPeriod(Base):
    # ... existing fields ...
    version: Mapped[int] = mapped_column(default=1)

    __mapper_args__ = {
        "version_id_col": version
    }
```

SQLAlchemy will automatically:
- Increment version on each update
- Raise `StaleDataError` if another session modified the row

**B. Pessimistic Locking Helpers**

Add helper methods for critical operations:

```python
# models/reporting_period.py
class ReportingPeriod(Base):
    # ... existing fields ...

    def close_with_lock(self, session):
        """Close period with row-level lock to prevent race conditions."""
        # Re-fetch with FOR UPDATE lock
        locked_period = session.query(ReportingPeriod)\
            .with_for_update()\
            .filter_by(id=self.id)\
            .one()

        if locked_period.status == ReportingPeriod.Status.ADJUSTING:
            locked_period.status = ReportingPeriod.Status.CLOSED
            session.commit()
        else:
            raise ValueError(f"Cannot close period in status {locked_period.status}")
```

**C. Documentation**

Add multi-user deployment guide covering:
- Database isolation levels
- Connection pooling configuration
- Locking best practices
- Handling `StaleDataError`

**Benefits**:
- Production-grade multi-user safety
- Prevents data corruption from race conditions
- Industry-standard concurrency patterns

**Scope**: PR #4 (Higher risk, high value)

---

### 3. Performance - Batch Posting ✅

**Problem**: Current ledger posting commits after EVERY ledger entry:

```python
# models/ledger.py (current implementation)
session.add(post)
session.flush()
session.add(folio)
session.commit()  # ← Commits after each entry!
```

For bulk imports:
- 1000 transactions × 2 line items = 2000 ledger entries = 2000 commits
- This is **extremely slow** (can take hours)

**Proposed Solution**:

Refactor posting to collect all entries, then commit once:

```python
# models/transaction.py
def post(self, session, batch_mode=False):
    """
    Post transaction to ledger.

    Args:
        session: Database session
        batch_mode: If True, caller will commit. If False, commits automatically.
    """
    # ... validation ...

    # Create ledger entries
    entries = self._create_ledger_entries(session)

    for entry in entries:
        session.add(entry)

    # Only commit if not in batch mode
    if not batch_mode:
        session.commit()
    else:
        session.flush()  # Just flush for ID assignment
```

Usage for bulk imports:

```python
# Batch posting example
transactions = [...]  # 1000 transactions

for txn in transactions:
    txn.post(session, batch_mode=True)

# Single commit for all 1000 transactions
session.commit()
```

**Benefits**:
- Makes bulk imports viable (hours → minutes)
- Backwards compatible (batch_mode defaults to False)
- Atomic bulk imports (all-or-nothing)

**Scope**: PR #2 (Medium risk, critical value)

---

### 4. Correction Tracking ✅

**Problem**: When transactions are corrected via Credit Notes or Debit Notes, there's no link between:
- The original (incorrect) transaction
- The reversal transaction
- The corrected transaction

This makes audit trails harder to follow.

**Proposed Solution**:

Add optional correction tracking:

```python
# models/transaction.py
class Transaction(Base):
    # ... existing fields ...

    # NEW: Track corrections
    corrects_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=True
    )

    # Relationships
    corrects_transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        foreign_keys=[corrects_transaction_id],
        remote_side=[id],
        backref="corrections"
    )

    def get_correction_chain(self, session):
        """
        Get the full chain of corrections for this transaction.

        Returns:
            List of (original, reversal, correction) tuples
        """
        chain = []
        current = self

        # Walk backwards to find original
        while current.corrects_transaction_id:
            current = session.get(Transaction, current.corrects_transaction_id)

        # Walk forwards through all corrections
        original = current
        for correction in original.corrections:
            chain.append((original, correction))

        return chain
```

Usage:

```python
# Create correction
credit_note = CreditNote(
    narration="Reversal of incorrect invoice",
    corrects_transaction_id=original_invoice.id,  # Link to original
    # ... other fields ...
)

# Later, view correction history
chain = original_invoice.get_correction_chain(session)
for original, correction in chain:
    print(f"{original.transaction_no} → {correction.transaction_no}")
```

**Benefits**:
- Audit compliance (trace correction history)
- Better financial reporting
- Backwards compatible (field is nullable)

**Scope**: PR #1 (Low risk, high value)

---

### 5. Report Data Export 🤔

**Problem**: Reports currently only return formatted text strings:

```python
report = IncomeStatement(session)
print(report)  # Text output only
```

Applications that want to export to CSV, XLSX, JSON, or build custom formatters must parse the text output.

**Proposed Solution**:

Add structured data methods to reports:

```python
# reports/financial_statement.py
class FinancialStatement:
    # ... existing code ...

    def to_dict(self) -> dict:
        """
        Export report as structured dictionary.

        Returns:
            {
                'title': 'Income Statement',
                'entity': 'My Company',
                'period': '2024-01-01 to 2024-12-31',
                'sections': [
                    {
                        'name': 'Revenue',
                        'accounts': [
                            {'name': 'Operating Revenue', 'amount': 10000.00}
                        ],
                        'total': 10000.00
                    },
                    ...
                ],
                'total': 8000.00
            }
        """
        pass

    def to_list(self) -> list[dict]:
        """
        Export report as flat list of rows (for CSV export).

        Returns:
            [
                {'section': 'Revenue', 'account': 'Operating Revenue', 'amount': 10000.00},
                {'section': 'Revenue', 'account': 'Total Revenue', 'amount': 10000.00},
                ...
            ]
        """
        pass
```

**Why This Belongs in python-accounting**:
- Exposes accounting logic in structured format
- Enables programmatic report consumption
- Format-agnostic (dict/list can be converted to anything)

**Why Formatters Belong in Applications**:
- CSV formatting (column order, headers, delimiters)
- XLSX styling (colors, fonts, borders)
- PDF generation (layout, branding)
- These are presentation concerns, not accounting logic

**Benefits**:
- Enables programmatic report consumption
- Separates data from presentation
- Applications can build custom formatters

**Scope**: PR #5 (Low risk, nice-to-have)

---

### 6. Query/Filter Helpers 🤔

**Problem**: Common query patterns require writing SQLAlchemy queries directly:

```python
# Current: Manual SQLAlchemy
bank_accounts = session.query(Account)\
    .filter(Account.account_type == Account.AccountType.BANK)\
    .all()

# Current: Manual date filtering
from sqlalchemy import and_
transactions = session.query(Transaction)\
    .filter(and_(
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    ))\
    .all()
```

**Proposed Solution**:

Add common filter class methods:

```python
# models/account.py
class Account(Base):
    # ... existing code ...

    @classmethod
    def by_type(cls, session, account_type):
        """Filter accounts by type."""
        return session.query(cls).filter(cls.account_type == account_type).all()

    @classmethod
    def by_code_range(cls, session, start_code, end_code):
        """Filter accounts by code range."""
        return session.query(cls).filter(
            cls.code >= start_code,
            cls.code <= end_code
        ).all()

# models/transaction.py
class Transaction(Base):
    # ... existing code ...

    @classmethod
    def in_period(cls, session, start_date, end_date):
        """Filter transactions by date range."""
        return session.query(cls).filter(
            cls.transaction_date >= start_date,
            cls.transaction_date <= end_date
        ).all()

    @classmethod
    def by_type(cls, session, transaction_type):
        """Filter transactions by type."""
        return session.query(cls).filter(
            cls.__class__ == transaction_type
        ).all()
```

Usage:

```python
# Cleaner API
bank_accounts = Account.by_type(session, Account.AccountType.BANK)
recent_txns = Transaction.in_period(session, datetime(2024, 1, 1), datetime(2024, 12, 31))
```

**Why This Might Belong in python-accounting**:
- Common accounting query patterns
- Reduces boilerplate for all applications

**Why This Might Belong in Applications**:
- Different apps have different query needs
- Could bloat the API surface
- Simple queries are fine with SQLAlchemy

**Recommendation**: Start with a few essential helpers, gather feedback

**Benefits**:
- Reduces boilerplate
- More readable code
- Consistent query patterns

**Scope**: Optional - gather maintainer feedback

---

## PostBalance-Specific Features (NOT for python-accounting)

These features are application-specific and belong in PostBalance or similar applications:

### 1. TUI Interface ❌ Application Layer
- Textual/Rich rendering
- Keyboard navigation
- Forms and input handling
- Screen layouts
- Command palette
- Color schemes

**Why**: These are presentation concerns specific to terminal UIs.

### 2. User Authentication & Session Management ❌ Application Layer
- Login/logout workflows
- Password hashing
- Session duration tracking
- Permission/role management
- Multi-factor authentication

**Why**: Authentication strategies vary by deployment (LDAP, OAuth, local, etc.). python-accounting should remain auth-agnostic.

### 3. Import/Export Wizards ❌ Application Layer
- CSV parsing logic
- File upload handling
- Import validation UI
- Progress bars
- Duplicate detection strategies
- File format detection (CSV vs XLSX vs QBO)

**Why**: File formats and import workflows are application-specific. python-accounting provides the posting API; applications handle parsing.

### 4. Report Formatting ❌ Application Layer
- Terminal-specific formatting
- Color-coded amounts (red for debits, green for credits)
- Box drawing characters
- Interactive drill-down
- PDF generation (reportlab, weasyprint)
- XLSX styling (openpyxl with formatting)
- CSV column ordering and headers

**Why**: Presentation format varies by application (web, TUI, API, print). python-accounting provides structured data via `.to_dict()`; applications format it.

### 5. Reconciliation UI ❌ Application Layer
- Bank statement upload/parsing
- Transaction matching UI
- Matching algorithm tuning (fuzzy match, date tolerance)
- Reconciliation approval workflow
- Suggested matches

**Why**: Reconciliation workflows vary significantly by organization. python-accounting provides the Assignment model; applications build matching logic.

### 6. Workflow Automation ❌ Application Layer
- Recurring transactions
- Approval workflows (multi-step approvals)
- Notification system (email, Slack, etc.)
- Scheduled report generation
- Period-end checklists

**Why**: Business process automation is organization-specific. python-accounting provides accounting primitives; applications orchestrate workflows.

### 7. Export File Generation ❌ Application Layer
- CSV file writing
- XLSX file generation with styling
- PDF rendering
- Email attachment generation

**Why**: While python-accounting should provide `.to_dict()` for structured data, the actual file generation logic (headers, styling, layout) is application-specific.

**PostBalance will**:
```python
# PostBalance exports (application layer)
from postbalance.exporters import CSVExporter, XLSXExporter, PDFExporter

report = IncomeStatement(session)
data = report.to_dict()  # ← python-accounting provides this

# PostBalance formatters
CSVExporter.export(data, "income_statement.csv")
XLSXExporter.export(data, "income_statement.xlsx", style="professional")
PDFExporter.export(data, "income_statement.pdf", letterhead=True)
```

---

## Recommended PR Sequence

To build trust with maintainers and minimize risk, propose PRs in this order:

### PR #1: Correction Tracking
- **Risk**: Very low (just adding optional field)
- **Value**: High (audit compliance)
- **Scope**:
  - Add `corrects_transaction_id` field
  - Add helper methods for correction chains
  - Update tests
  - Document usage

### PR #2: Performance - Batch Posting
- **Risk**: Medium (touches core posting logic)
- **Value**: Critical (enables bulk imports)
- **Scope**:
  - Refactor ledger posting to reduce commits
  - Add optional `batch_mode` parameter
  - Benchmark tests showing improvement
  - Migration guide for existing code

### PR #3: User Tracking
- **Risk**: Medium (adds fields, needs migration strategy)
- **Value**: High (multi-user audit trail)
- **Scope**:
  - Add `created_by_id`, `updated_by_id` to models
  - Add user context to session
  - Event listeners to auto-populate
  - Migration guide for existing databases
  - Document disabling if not needed

### PR #4: Concurrency Control
- **Risk**: Higher (changes core transaction semantics)
- **Value**: High (production-grade multi-user safety)
- **Scope**:
  - Add `version` column for optimistic locking
  - Add locking helpers for period closure
  - Documentation on multi-user patterns
  - Handle `StaleDataError` gracefully

### PR #5: Report Data Export
- **Risk**: Very low (additive only)
- **Value**: Nice-to-have (enables programmatic reports)
- **Scope**:
  - Add `.to_dict()` and `.to_list()` methods on reports
  - Enable structured data extraction
  - Document usage

---

## Validation with Maintainers

Before starting implementation, recommend opening a GitHub Discussion or Issue:

**Title**: "Proposal: Multi-user enhancements for production deployments"

**Summary**:
```markdown
We're building PostBalance, a TUI-based financial workstation using python-accounting
as the engine. We'd like to contribute several enhancements back upstream that would
benefit any multi-user production deployment:

1. User tracking (created_by_id, updated_by_id) for audit trails
2. Optimistic locking (version column) for concurrency safety
3. Performance optimization for bulk imports (batch posting)
4. Correction tracking (link reversals to original transactions)
5. Report data export (structured data methods)

Would the maintainers be interested in PRs for these features? Are there any
architectural preferences or concerns we should address first?

We want to ensure these remain general-purpose enhancements suitable for the
library, not PostBalance-specific code.

Our design philosophy is to keep python-accounting as a general-purpose accounting
engine while application-specific features (UI, auth, import wizards) stay in
PostBalance.
```

**Benefits of Early Discussion**:
- Shows you're a serious contributor
- Gets buy-in before writing code
- Might reveal existing work or different architectural preferences
- Builds relationship with maintainers
- Clarifies priorities and preferences

---

## Summary: What Goes Where

| Feature | python-accounting | PostBalance |
|---------|-------------------|-------------|
| Double-entry accounting | ✅ Core feature | |
| User tracking (created_by_id) | ✅ Proposed PR | |
| Concurrency control (version) | ✅ Proposed PR | |
| Batch posting optimization | ✅ Proposed PR | |
| Correction tracking | ✅ Proposed PR | |
| Report `.to_dict()` | ✅ Proposed PR | |
| Query helpers (maybe) | 🤔 Discuss with maintainers | |
| TUI interface | | ✅ Application |
| User authentication | | ✅ Application |
| CSV/XLSX/PDF formatters | | ✅ Application |
| Import wizards | | ✅ Application |
| Reconciliation UI | | ✅ Application |
| Workflow automation | | ✅ Application |

---

## Timeline Estimate

Assuming each PR includes:
- Implementation
- Tests
- Documentation
- Review cycles

**Estimated Timeline**:
- PR #1 (Correction Tracking): 1 week
- PR #2 (Batch Posting): 2 weeks
- PR #3 (User Tracking): 2 weeks
- PR #4 (Concurrency Control): 2-3 weeks
- PR #5 (Report Export): 1 week

**Total**: 8-9 weeks (assuming sequential, with review time)

Can be parallelized if maintainers approve multiple PRs simultaneously.

---

## Questions for python-accounting Maintainers

1. **Architecture**: Do these enhancements align with the project's vision?
2. **Breaking Changes**: Are nullable fields acceptable, or do you prefer feature flags?
3. **Migration**: What's the preferred migration strategy for existing deployments?
4. **Testing**: Are there specific test coverage requirements?
5. **Documentation**: Where should multi-user deployment guides live?
6. **Priorities**: Which PRs would provide the most value to other users?
7. **Existing Work**: Is anyone already working on similar features?

---

## Conclusion

These proposed enhancements maintain python-accounting's focus as a general-purpose accounting library while enabling production-grade multi-user deployments. The clean separation between library features and application concerns ensures PostBalance and other applications can build rich user experiences on top of a solid accounting foundation.

We're committed to contributing these improvements upstream to benefit the entire python-accounting community.
