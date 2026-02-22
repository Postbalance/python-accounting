# Audit Logging Feature Design for Python Accounting

**Status:** Planning / Not Implemented
**Created:** 2025-11-24
**Purpose:** Reference document for implementing comprehensive audit logging in Python Accounting

---

## Executive Summary

For a production financial system, comprehensive audit logging is recommended for:
- Regulatory compliance (SOX, SOC 2, GDPR)
- Fraud detection and prevention
- Dispute resolution and investigation
- Operational intelligence and debugging

This document outlines what to track, how to implement it, and trade-offs to consider.

---

## Current State Analysis

### What EXISTS (Partial Audit Trail)

1. **Ledger Table** - Financial transactions only
   - Append-only for posted transactions (`ondelete="RESTRICT"`)
   - Cryptographically hashed (blockchain-style chain)
   - Has `created_at` timestamp
   - **Limitation:** Only logs financial transactions that are `.post()`ed

2. **Recycled Table** - Soft deletion tracking
   - Records when models are deleted/restored
   - Tracks: `deleted_at`, `restored_at`, `destroyed_at`
   - **Limitation:** Only logs delete/restore operations

3. **Base Model Timestamps**
   - `created_at`: When record was created
   - `updated_at`: When record was last modified
   - **Limitation:** No attribution, no change history, no old values

### What DOES NOT EXIST

❌ No comprehensive audit log tracking:
- Read operations (who viewed what)
- Update details (what changed, old vs new values)
- User attribution (who performed actions)
- Failed operations or validation errors
- Session/request context
- Query patterns or bulk operations

---

## Recommended Audit Log Schema

```python
class AuditLog(IsolatingMixin, Base):
    """Comprehensive append-only audit trail"""
    __tablename__ = "audit_log"

    # Make truly append-only
    __table_args__ = (
        CheckConstraint('created_at IS NOT NULL'),
        Index('idx_audit_timestamp_entity', 'timestamp', 'entity_id'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_model', 'model_type', 'model_id'),
    )

    # Core identification
    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        default=datetime.now,
        index=True
    )

    # Actor (who performed the action)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"),
        nullable=True
    )
    session_id: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),  # IPv6 length
        nullable=True
    )
    user_agent: Mapped[str] = mapped_column(
        String(500),
        nullable=True
    )

    # Action (what was done)
    action_type: Mapped[str] = mapped_column(
        String(50),
        index=True
    )
    # Enum values: READ, INSERT, UPDATE, DELETE, RESTORE, DESTROY,
    #              POST, ASSIGN, REPORT, EXPORT, AUTH

    model_type: Mapped[str] = mapped_column(
        String(100),
        index=True
    )  # e.g., "Transaction", "Account", "User"

    model_id: Mapped[int] = mapped_column(nullable=True, index=True)

    # Context
    operation_context: Mapped[str] = mapped_column(
        String(100),
        nullable=True
    )
    # Examples: "POST_TRANSACTION", "GENERATE_INCOME_STATEMENT",
    #           "BULK_DELETE", "DATA_EXPORT"

    query_type: Mapped[str] = mapped_column(
        String(50),
        nullable=True
    )
    # For reads: "GET", "LIST", "SEARCH", "REPORT", "BULK"

    # Change tracking (for writes)
    old_values: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {"field_name": old_value, ...}

    new_values: Mapped[dict] = mapped_column(JSON, nullable=True)
    # {"field_name": new_value, ...}

    changed_fields: Mapped[list] = mapped_column(JSON, nullable=True)
    # ["field1", "field2", ...]

    # Business context
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transaction.id"),
        nullable=True
    )

    # Query details (for reads)
    query_summary: Mapped[str] = mapped_column(
        String(1000),
        nullable=True
    )
    record_count: Mapped[int] = mapped_column(nullable=True)

    # Result
    success: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[str] = mapped_column(
        String(1000),
        nullable=True
    )

    # Performance metrics
    duration_ms: Mapped[int] = mapped_column(nullable=True)

    # Description for human readability
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    transaction: Mapped["Transaction"] = relationship(
        foreign_keys=[transaction_id]
    )

    # Prevent modifications (truly append-only)
    def __setattr__(self, key, value):
        if key in self.__dict__ and key != '_sa_instance_state':
            raise ValueError("Audit log records are immutable")
        super().__setattr__(key, value)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action_type} {self.model_type}:{self.model_id} by User:{self.user_id}>"
```

---

## Tiered Tracking Strategy

### Tier 1: Always Track (Critical Path) ✅ MANDATORY

**What:**
- All WRITE operations (INSERT, UPDATE, DELETE, RESTORE, DESTROY)
  - Full before/after values
  - Who, when, where
- Financial transaction posts/modifications
- Assignment create/delete
- User authentication events (login, logout, failed attempts)
- Permission/role changes
- Report generation (type, parameters, date range, who ran it)
- Data exports (what data, format, destination)
- Configuration changes (Entity settings, Tax rates, etc.)

**Storage Impact:** ~1-10 KB per operation
- Expected: 1,000-10,000 writes/day
- Daily: 10-100 MB
- Yearly: 3.6-36 GB

### Tier 2: Selective Read Tracking (High-Value) ⚠️ RECOMMENDED

**What:**
- Access to sensitive records:
  - Individual Transaction/Ledger reads (by ID)
  - Client/Supplier account details
  - Financial report views
- Bulk queries (>100 records returned)
- Search operations (track search terms)
- Failed queries/authorization failures

**Skip:**
- Account balance checks (routine)
- List pagination (UI navigation)
- Dropdown population queries

**Storage Impact:** ~500 bytes per read event
- Expected: 5,000-50,000 reads/day
- Daily: 2.5-25 MB
- Yearly: 0.9-9 GB

### Tier 3: Sampled/Aggregated (Optional) 📊

**What:**
- Query performance metrics (aggregated hourly/daily)
- User activity summaries (sessions, not clicks)
- Popular report types (aggregated counts)
- System health metrics

**Storage Impact:** Minimal (aggregated)

---

## Configuration Approach

Add to `config.toml`:

```toml
[audit]
enabled = true
track_writes = true  # Always
track_sensitive_reads = true  # Individual high-value records
track_bulk_reads = true  # Queries returning >100 records
track_routine_reads = false  # Balance checks, list views
read_sampling_rate = 0.01  # Sample 1% of routine reads for analytics

# Async processing
async_logging = true
batch_size = 100  # Write in batches
batch_interval_seconds = 5

# Retention
retention_days = 2555  # 7 years
archive_after_days = 1825  # 5 years

[audit.sensitive_tables]
# These tables always log reads
tables = [
    "transaction",
    "ledger",
    "assignment",
    "user",
    "balance",
]

[audit.aggregate_only]
# These only track aggregated metrics, not individual reads
tables = [
    "account",
    "currency",
    "tax",
    "category",
]

[audit.action_types]
# Define all action types
READ = "READ"
INSERT = "INSERT"
UPDATE = "UPDATE"
DELETE = "DELETE"
RESTORE = "RESTORE"
DESTROY = "DESTROY"
POST = "POST"
ASSIGN = "ASSIGN"
REPORT = "REPORT"
EXPORT = "EXPORT"
AUTH = "AUTH"
```

---

## Implementation Options

### Option 1: Database Triggers ⚡
```sql
CREATE TRIGGER audit_transaction_changes
AFTER UPDATE ON transaction
FOR EACH ROW
INSERT INTO audit_log (...)
```

**Pros:**
- Works at database level
- Can't be bypassed by application code
- No application changes needed

**Cons:**
- Hard to get user/session context
- Performance impact on main queries
- Complex trigger logic
- Limited to database-visible changes

**Recommendation:** ❌ Not recommended for this use case

---

### Option 2: SQLAlchemy Event Listeners ⭐ RECOMMENDED

```python
# In database/event_listeners.py

from python_accounting.models import AuditLog

class AuditingMixin:
    """Mixin for audit logging"""

    @event.listens_for(Session, "after_flush")
    def audit_changes(self, flush_context):
        """Audit all changes after flush"""

        for obj in self.new:
            # New records (INSERT)
            self._create_audit_log(
                action_type="INSERT",
                obj=obj,
                new_values=self._get_object_values(obj),
            )

        for obj in self.dirty:
            # Modified records (UPDATE)
            changes = {}
            old_values = {}
            new_values = {}

            for attr in inspect(obj).attrs:
                hist = attr.load_history()
                if hist.has_changes():
                    changes[attr.key] = True
                    old_values[attr.key] = hist.deleted[0] if hist.deleted else None
                    new_values[attr.key] = hist.added[0] if hist.added else None

            if changes:
                self._create_audit_log(
                    action_type="UPDATE",
                    obj=obj,
                    old_values=old_values,
                    new_values=new_values,
                    changed_fields=list(changes.keys()),
                )

        for obj in self.deleted:
            # Deleted records (DELETE)
            self._create_audit_log(
                action_type="DELETE",
                obj=obj,
                old_values=self._get_object_values(obj),
            )

    def _create_audit_log(self, action_type, obj, **kwargs):
        """Create audit log entry"""

        # Skip auditing the audit log itself!
        if isinstance(obj, AuditLog):
            return

        audit_entry = AuditLog(
            timestamp=datetime.now(),
            action_type=action_type,
            model_type=obj.__class__.__name__,
            model_id=obj.id if hasattr(obj, 'id') else None,
            entity_id=obj.entity_id if hasattr(obj, 'entity_id') else self.entity.id,
            user_id=getattr(self, 'current_user_id', None),
            session_id=getattr(self, 'session_id', None),
            **kwargs
        )

        # Add to session but don't flush yet (avoid recursion)
        self.add(audit_entry)

    def _get_object_values(self, obj):
        """Extract all values from an object"""
        return {
            attr.key: getattr(obj, attr.key)
            for attr in inspect(obj).attrs
            if not attr.key.startswith('_')
        }

# Add to AccountingSession
class AccountingSession(
    SessionOverridesMixin,
    AuditingMixin,  # <-- Add this
    EventListenersMixin,
    AccountingFunctionsMixin,
    Session
):
    entity: Entity
    current_user_id: int | None = None  # Set by application
    session_id: str | None = None  # Set by application
```

**Pros:**
- Full Python context available
- Can customize per model
- Access to user/session info
- Can make async/batched
- Type-safe

**Cons:**
- Can be bypassed with raw SQL (acceptable trade-off)
- Need to avoid recursion (audit log auditing itself)

**Recommendation:** ✅ **Recommended approach**

---

### Option 3: Application-Level Decorator

```python
# In utils/audit.py

def audit_action(action_type: str, sensitivity: str = "LOW"):
    """Decorator to audit function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(session, *args, **kwargs):
            start_time = time.time()
            success = True
            error_msg = None

            try:
                result = func(session, *args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)

                # Create audit log
                audit_log = AuditLog(
                    action_type=action_type,
                    timestamp=datetime.now(),
                    success=success,
                    error_message=error_msg,
                    duration_ms=duration_ms,
                    description=f"{func.__name__}({args}, {kwargs})",
                    # ... other fields
                )
                session.add(audit_log)
                session.commit()

        return wrapper
    return decorator

# Usage:
@audit_action(action_type="READ", sensitivity="HIGH")
def get_transaction(session, transaction_id):
    return session.get(Transaction, transaction_id)

@audit_action(action_type="REPORT", sensitivity="HIGH")
def generate_income_statement(session, start_date, end_date):
    return IncomeStatement(session, start_date, end_date)
```

**Pros:**
- Explicit and controlled
- Best performance (only audit what you mark)
- Easy to customize per function
- Good for high-level operations (reports, exports)

**Cons:**
- Easy to forget to add decorator
- Not automatic
- More code changes required

**Recommendation:** ⚠️ Use in combination with Option 2 for high-level operations

---

### Option 4: Change Data Capture (CDC)

Tools like Debezium, AWS DMS, or PostgreSQL logical replication.

**Pros:**
- Zero application code changes
- Highly scalable
- Works at binary log level
- Can stream to separate systems

**Cons:**
- Infrastructure complexity
- Additional cost
- Overkill for single-application system
- Still need user context enrichment

**Recommendation:** ❌ Not recommended unless scaling to large deployment

---

## Recommended Implementation Plan

### Phase 1: Foundation (Week 1-2)

1. **Create AuditLog model** (python_accounting/models/audit_log.py)
2. **Add to models/__init__.py** and create migration
3. **Extend AccountingSession** with user/session tracking:
   ```python
   session.current_user_id = user.id
   session.session_id = uuid.uuid4().hex
   session.ip_address = request.remote_addr  # If web framework
   ```
4. **Add audit config** to config.toml
5. **Write tests** for audit log creation

### Phase 2: Write Auditing (Week 3-4)

1. **Implement AuditingMixin** with after_flush event listener
2. **Track all INSERTs, UPDATEs, DELETEs** automatically
3. **Special handling** for:
   - Transaction.post() → action_type="POST"
   - Assignment creation → action_type="ASSIGN"
   - Recycled operations → action_type="RESTORE"/"DESTROY"
4. **Test extensively** to avoid recursion/performance issues

### Phase 3: Read Auditing (Week 5-6)

1. **Override Session.get()** to audit sensitive reads
2. **Add decorator** for report generation
3. **Track bulk queries** in do_orm_execute listener
4. **Implement sampling** for routine reads

### Phase 4: Query Interface (Week 7-8)

1. **Create AuditLog query helpers:**
   ```python
   # Who modified this transaction?
   AuditLog.get_history(Transaction, transaction_id)

   # What did this user do today?
   AuditLog.get_user_activity(user_id, start_date, end_date)

   # What changed on this record?
   AuditLog.get_changes(model_type, model_id)

   # Find all reads of sensitive data
   AuditLog.find_reads(model_type="Transaction", user_id=5)
   ```
2. **Admin UI/API** for viewing audit logs
3. **Export functionality** for auditors

### Phase 5: Optimization (Ongoing)

1. **Async/batched writes** to avoid performance impact
2. **Archival strategy** (move old logs to cold storage)
3. **Retention policy enforcement**
4. **Performance monitoring** and tuning

---

## Storage Estimates

### Medium-Sized Deployment (5-10 users)

**Assumptions:**
- 1,000-10,000 write operations/day
- 5,000-50,000 read operations/day (if tracking selectively)
- Average audit log record: 1-2 KB

**Storage:**
- **Per day:** 10-125 MB
- **Per month:** 300 MB - 3.75 GB
- **Per year:** 3.6-45 GB
- **5 years (retention):** 18-225 GB
- **7 years (compliance):** 25-315 GB

**Costs (AWS S3 storage):**
- Monthly: $0.50-$7.50
- 7 years: $42-$525 total

**Conclusion:** Storage cost is negligible compared to value provided.

---

## Security & Privacy Considerations

### Security Features

1. **Immutability:** Once created, audit logs cannot be modified
   - Implement at application level (raise on setattr)
   - Consider database-level constraints (append-only table)
   - Optional: Blockchain-style chaining (hash includes previous hash)

2. **Access Control:** Who can view audit logs?
   - Admin-only by default
   - Entity isolation (can't see other entities' logs)
   - Redaction for sensitive fields (passwords, tokens)

3. **Tamper Detection:**
   ```python
   def verify_audit_log_integrity(session):
       """Verify no audit logs were tampered with"""
       logs = session.query(AuditLog).order_by(AuditLog.id).all()
       for i, log in enumerate(logs[1:], 1):
           expected_hash = compute_hash(logs[i-1])
           if log.prev_hash != expected_hash:
               raise TamperDetectedException(f"Log {log.id} tampered!")
   ```

### Privacy Considerations

1. **PII Handling:**
   - Don't log sensitive fields (passwords, credit cards, SSN)
   - Redact PII in audit logs based on compliance requirements
   - Allow users to request their audit history (GDPR)

2. **Retention:**
   - Balance compliance (need to keep) vs privacy (right to deletion)
   - GDPR: Users can request deletion after retention period
   - Anonymize instead of delete (preserve data integrity)

3. **Access Logging:**
   - Log who accessed audit logs (meta-audit!)
   - Alert on suspicious patterns (mass export, unusual queries)

---

## Query Examples

### Common Audit Queries

```python
# 1. Who modified this transaction?
audit_logs = session.query(AuditLog)\
    .filter(AuditLog.model_type == "Transaction")\
    .filter(AuditLog.model_id == transaction_id)\
    .filter(AuditLog.action_type.in_(["UPDATE", "DELETE"]))\
    .order_by(AuditLog.timestamp.desc())\
    .all()

# 2. What changed on this record between dates?
changes = session.query(AuditLog)\
    .filter(AuditLog.model_id == record_id)\
    .filter(AuditLog.timestamp.between(start_date, end_date))\
    .all()

# 3. What did user X do today?
user_activity = session.query(AuditLog)\
    .filter(AuditLog.user_id == user_id)\
    .filter(AuditLog.timestamp >= datetime.today())\
    .order_by(AuditLog.timestamp.desc())\
    .all()

# 4. Who viewed this sensitive transaction?
views = session.query(AuditLog)\
    .filter(AuditLog.action_type == "READ")\
    .filter(AuditLog.model_type == "Transaction")\
    .filter(AuditLog.model_id == transaction_id)\
    .all()

# 5. All failed operations in last hour
failures = session.query(AuditLog)\
    .filter(AuditLog.success == False)\
    .filter(AuditLog.timestamp >= datetime.now() - timedelta(hours=1))\
    .all()

# 6. Who ran reports today?
reports = session.query(AuditLog)\
    .filter(AuditLog.action_type == "REPORT")\
    .filter(AuditLog.timestamp >= datetime.today())\
    .all()

# 7. Bulk operations (potential data exfiltration)
bulk_ops = session.query(AuditLog)\
    .filter(AuditLog.record_count > 1000)\
    .filter(AuditLog.timestamp >= datetime.now() - timedelta(days=7))\
    .all()

# 8. Reconstruct record state at point in time
def get_record_at_time(session, model_type, model_id, target_time):
    """Reconstruct record state at a specific time"""
    # Get current state
    current = session.get(eval(model_type), model_id)

    # Get all changes after target_time
    changes = session.query(AuditLog)\
        .filter(AuditLog.model_type == model_type)\
        .filter(AuditLog.model_id == model_id)\
        .filter(AuditLog.timestamp > target_time)\
        .order_by(AuditLog.timestamp.asc())\
        .all()

    # Reverse changes
    state = current.__dict__.copy()
    for change in reversed(changes):
        if change.old_values:
            state.update(change.old_values)

    return state
```

---

## Performance Considerations

### Write Performance

**Problem:** Every database write now requires an additional audit log write (2x writes).

**Solutions:**

1. **Async/Batched Writes:**
   ```python
   # Use a queue
   audit_queue = Queue()

   def audit_worker():
       while True:
           batch = []
           while len(batch) < 100 and not audit_queue.empty():
               batch.append(audit_queue.get())

           if batch:
               session.bulk_insert_mappings(AuditLog, batch)
               session.commit()

           time.sleep(5)  # Batch every 5 seconds

   # In application
   Thread(target=audit_worker, daemon=True).start()
   ```

2. **Separate Database/Schema:**
   - Write audit logs to different database
   - Reduces contention on main tables
   - Can optimize separately (different indexes, storage)

3. **Minimal Fields First:**
   - Start with essential fields only
   - Add detail later if performance allows

### Read Performance

**Problem:** Audit log queries can be slow (millions of records).

**Solutions:**

1. **Proper Indexing:**
   ```python
   Index('idx_audit_timestamp_entity', 'timestamp', 'entity_id')
   Index('idx_audit_user_time', 'user_id', 'timestamp')
   Index('idx_audit_model', 'model_type', 'model_id')
   Index('idx_audit_action', 'action_type', 'timestamp')
   ```

2. **Partitioning:**
   - Partition by date (monthly/yearly)
   - Older partitions on slower storage
   - Automatic pruning

3. **Archival:**
   - Move logs >1 year old to archive table
   - Move logs >5 years to cold storage (S3)
   - Keep hot storage lean

4. **Summary Tables:**
   - Pre-aggregate common queries
   - Daily user activity summaries
   - Report generation frequency
   - Update via scheduled job

---

## Testing Strategy

### Unit Tests

```python
def test_audit_log_insert(session, entity, user):
    """Test that INSERT operations are audited"""
    account = Account(
        name="Test Account",
        account_type=Account.AccountType.BANK,
        entity_id=entity.id,
    )
    session.current_user_id = user.id
    session.add(account)
    session.commit()

    audit = session.query(AuditLog)\
        .filter(AuditLog.model_type == "Account")\
        .filter(AuditLog.model_id == account.id)\
        .filter(AuditLog.action_type == "INSERT")\
        .first()

    assert audit is not None
    assert audit.user_id == user.id
    assert audit.new_values["name"] == "Test Account"

def test_audit_log_update(session, entity, account, user):
    """Test that UPDATE operations are audited"""
    old_name = account.name
    account.name = "Updated Account"
    session.current_user_id = user.id
    session.commit()

    audit = session.query(AuditLog)\
        .filter(AuditLog.model_type == "Account")\
        .filter(AuditLog.model_id == account.id)\
        .filter(AuditLog.action_type == "UPDATE")\
        .order_by(AuditLog.timestamp.desc())\
        .first()

    assert audit is not None
    assert audit.old_values["name"] == old_name
    assert audit.new_values["name"] == "Updated Account"
    assert "name" in audit.changed_fields

def test_audit_log_immutable(session, entity):
    """Test that audit logs cannot be modified"""
    audit = AuditLog(
        action_type="TEST",
        model_type="Test",
        entity_id=entity.id,
    )
    session.add(audit)
    session.commit()

    with pytest.raises(ValueError, match="immutable"):
        audit.action_type = "MODIFIED"

def test_audit_log_transaction_post(session, entity, transaction, user):
    """Test that transaction posts are audited with special action type"""
    session.current_user_id = user.id
    transaction.post(session)

    audit = session.query(AuditLog)\
        .filter(AuditLog.action_type == "POST")\
        .filter(AuditLog.transaction_id == transaction.id)\
        .first()

    assert audit is not None
    assert audit.user_id == user.id
```

### Integration Tests

```python
def test_audit_trail_reconstruction(session, entity, account, user):
    """Test reconstructing record history from audit trail"""
    # Make several changes
    session.current_user_id = user.id

    account.name = "Version 1"
    session.commit()
    time_1 = datetime.now()

    time.sleep(0.1)
    account.name = "Version 2"
    session.commit()
    time_2 = datetime.now()

    time.sleep(0.1)
    account.name = "Version 3"
    session.commit()

    # Reconstruct at time_1
    state = get_record_at_time(session, "Account", account.id, time_1)
    assert state["name"] == "Version 1"

    # Reconstruct at time_2
    state = get_record_at_time(session, "Account", account.id, time_2)
    assert state["name"] == "Version 2"

def test_audit_performance(session, entity, user):
    """Test that audit logging doesn't significantly degrade performance"""
    import time

    # Measure without audit
    start = time.time()
    for i in range(100):
        account = Account(name=f"Account {i}", entity_id=entity.id)
        session.add(account)
    session.commit()
    duration_without_audit = time.time() - start

    # Enable audit
    session.current_user_id = user.id

    # Measure with audit
    start = time.time()
    for i in range(100):
        account = Account(name=f"Audit Account {i}", entity_id=entity.id)
        session.add(account)
    session.commit()
    duration_with_audit = time.time() - start

    # Should not be more than 2x slower
    assert duration_with_audit < duration_without_audit * 2
```

---

## Migration Strategy

### For Existing Deployments

1. **Add audit_log table** via migration
2. **Deploy code** with audit disabled
3. **Test in staging** environment
4. **Enable audit gradually:**
   - Week 1: Only track Transaction posts
   - Week 2: Add all writes
   - Week 3: Add sensitive reads
   - Week 4: Full deployment
5. **Monitor performance** and adjust

### Database Migration

```python
# migrations/add_audit_log.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('model_type', sa.String(100), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=True),
        sa.Column('operation_context', sa.String(100), nullable=True),
        sa.Column('query_type', sa.String(50), nullable=True),
        sa.Column('old_values', postgresql.JSON(), nullable=True),
        sa.Column('new_values', postgresql.JSON(), nullable=True),
        sa.Column('changed_fields', postgresql.JSON(), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('query_summary', sa.String(1000), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.String(1000), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(['entity_id'], ['entity.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['transaction.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for performance
    op.create_index('idx_audit_timestamp_entity', 'audit_log', ['timestamp', 'entity_id'])
    op.create_index('idx_audit_user', 'audit_log', ['user_id'])
    op.create_index('idx_audit_model', 'audit_log', ['model_type', 'model_id'])
    op.create_index('idx_audit_action', 'audit_log', ['action_type', 'timestamp'])

def downgrade():
    op.drop_index('idx_audit_action', table_name='audit_log')
    op.drop_index('idx_audit_model', table_name='audit_log')
    op.drop_index('idx_audit_user', table_name='audit_log')
    op.drop_index('idx_audit_timestamp_entity', table_name='audit_log')
    op.drop_table('audit_log')
```

---

## Open Questions & Decisions Needed

1. **Hash Chaining:** Should audit logs be cryptographically chained like Ledger entries?
   - Pro: Tamper-evident
   - Con: More complexity, can't delete single entries

2. **Read Tracking Scope:** How aggressive should read tracking be?
   - Option A: Only sensitive reads (recommended)
   - Option B: All reads (storage explosion)
   - Option C: Sampled reads (complex)

3. **User Context:** How to get user info in session?
   - Need integration with authentication system
   - Middleware to set session.current_user_id?

4. **Performance SLA:** What's acceptable overhead?
   - Target: <10% performance degradation
   - May need async logging for high-volume

5. **Compliance Requirements:** What are actual regulatory needs?
   - Different requirements for different jurisdictions
   - May need to be configurable per Entity

6. **Archival Strategy:** Where to store old logs?
   - Database partitioning?
   - Export to S3/cold storage?
   - When to delete vs archive?

---

## References & Resources

### Standards & Compliance
- **SOX (Sarbanes-Oxley):** Section 404 - Internal Controls
- **SOC 2 Type II:** CC6.2 - Logical and Physical Access Controls
- **GDPR:** Article 15 (Right of Access), Article 30 (Records of Processing)
- **PCI-DSS:** Requirement 10 - Track and Monitor Network Access

### Technical Resources
- SQLAlchemy Event System: https://docs.sqlalchemy.org/en/20/orm/events.html
- Database Auditing Best Practices: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- Temporal Tables (SQL Server): https://learn.microsoft.com/en-us/sql/relational-databases/tables/temporal-tables

### Similar Implementations
- Django Simple History: https://django-simple-history.readthedocs.io/
- SQLAlchemy Continuum: https://sqlalchemy-continuum.readthedocs.io/
- Audit Trail for Rails: https://github.com/paper-trail-gem/paper_trail

---

## Next Steps

1. **Review & Approve** this design document
2. **Choose implementation approach** (recommended: Option 2 - Event Listeners)
3. **Define specific compliance requirements** for target users
4. **Create detailed technical specification** from this document
5. **Implement in phases** (Foundation → Writes → Reads → Query Interface)
6. **Test thoroughly** in staging environment
7. **Document** for end users and auditors
8. **Deploy** with monitoring

---

**Document Status:** Draft for Review
**Last Updated:** 2025-11-24
**Author:** Analysis based on Python Accounting codebase review
