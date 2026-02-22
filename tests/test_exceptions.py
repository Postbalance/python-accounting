from python_accounting.exceptions import AccountingException


def test_base_exception_exists():
    """The base accounting exception class should be named AccountingException."""
    assert issubclass(AccountingException, Exception)


def test_base_exception_message():
    """The base accounting exception should display its message when converted to string."""
    exc = AccountingException()
    exc.message = "test error"
    assert str(exc) == "test error"


def test_subclasses_inherit_from_base():
    """All accounting exceptions should inherit from AccountingException."""
    from python_accounting.exceptions import (
        InvalidAccountTypeError,
        MissingEntityError,
        PostedTransactionError,
    )

    assert issubclass(InvalidAccountTypeError, AccountingException)
    assert issubclass(MissingEntityError, AccountingException)
    assert issubclass(PostedTransactionError, AccountingException)
