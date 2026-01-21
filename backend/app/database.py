"""
Database connection and session management.

Supports optional SQLCipher encryption for SQLite databases.
"""

import os
from collections.abc import Generator
from typing import Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings


def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign keys and other SQLite pragmas."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _set_sqlcipher_key(dbapi_conn, connection_record):
    """Set SQLCipher encryption key if configured."""
    if settings.database_encryption_key:
        cursor = dbapi_conn.cursor()
        # Set the encryption key
        cursor.execute(f"PRAGMA key='{settings.database_encryption_key}'")
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON")
        # Optimize for performance
        cursor.execute("PRAGMA cipher_page_size=4096")
        cursor.execute("PRAGMA kdf_iter=256000")
        cursor.close()


def _verify_encryption(dbapi_conn, connection_record):
    """Verify database encryption is working."""
    if settings.database_encryption_key:
        cursor = dbapi_conn.cursor()
        try:
            # Try to read from the database - will fail if key is wrong
            cursor.execute("SELECT count(*) FROM sqlite_master")
            cursor.fetchone()
        except Exception as e:
            raise RuntimeError(
                f"Database encryption verification failed. "
                f"Check ENCRYPTION_KEY is correct: {e}"
            )
        finally:
            cursor.close()


def create_database_engine(
    database_url: Optional[str] = None,
    encryption_key: Optional[str] = None,
    echo: bool = False,
):
    """
    Create SQLAlchemy engine with optional encryption.

    Args:
        database_url: Database URL (default from settings)
        encryption_key: Encryption key for SQLCipher (default from settings)
        echo: Echo SQL statements

    Returns:
        SQLAlchemy engine
    """
    db_url = database_url or settings.database_url
    enc_key = encryption_key or settings.database_encryption_key

    # For SQLCipher, we need to use the sqlcipher dialect
    if enc_key and "sqlite" in db_url:
        # Check if pysqlcipher3 is available
        try:
            import pysqlcipher3
            # Replace sqlite with sqlcipher dialect
            db_url = db_url.replace("sqlite:///", "sqlite+pysqlcipher:///")
        except ImportError:
            # Fall back to standard SQLite with warning
            import warnings
            warnings.warn(
                "SQLCipher not available (pysqlcipher3 not installed). "
                "Database will NOT be encrypted. Install with: pip install pysqlcipher3"
            )
            enc_key = None

    # Create engine
    connect_args = {}
    if "sqlite" in db_url:
        connect_args["check_same_thread"] = False

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        echo=echo,
    )

    # Set up event listeners
    if "sqlite" in db_url:
        if enc_key:
            event.listen(engine, "connect", _set_sqlcipher_key)
            event.listen(engine, "connect", _verify_encryption)
        else:
            event.listen(engine, "connect", _set_sqlite_pragma)

    return engine


# Create default engine
engine = create_database_engine(
    settings.database_url,
    settings.database_encryption_key,
    settings.debug,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    from app.models.base import Base

    # Import all models to register them
    from app.models import company, transaction, invoice, asset, user, knowledge, osvc

    # Create tables
    Base.metadata.create_all(bind=engine)


def is_database_encrypted() -> bool:
    """Check if database encryption is enabled."""
    return bool(settings.database_encryption_key)


def change_encryption_key(old_key: str, new_key: str) -> bool:
    """
    Change database encryption key.

    WARNING: This requires the database to be re-encrypted.
    Only works with SQLCipher databases.

    Args:
        old_key: Current encryption key
        new_key: New encryption key

    Returns:
        True if successful
    """
    if not is_database_encrypted():
        raise ValueError("Database is not encrypted")

    try:
        import pysqlcipher3.dbapi2 as sqlcipher
    except ImportError:
        raise ImportError("SQLCipher not available")

    # Get database path from URL
    db_path = settings.database_url.replace("sqlite:///", "")

    # Open with old key and rekey
    conn = sqlcipher.connect(db_path)
    conn.execute(f"PRAGMA key='{old_key}'")
    conn.execute(f"PRAGMA rekey='{new_key}'")
    conn.close()

    return True


def export_database_unencrypted(output_path: str) -> bool:
    """
    Export encrypted database to unencrypted SQLite file.

    WARNING: Creates unencrypted copy. Handle with care.

    Args:
        output_path: Path for unencrypted database

    Returns:
        True if successful
    """
    if not is_database_encrypted():
        raise ValueError("Database is not encrypted")

    try:
        import pysqlcipher3.dbapi2 as sqlcipher
        import sqlite3
    except ImportError:
        raise ImportError("SQLCipher not available")

    db_path = settings.database_url.replace("sqlite:///", "")
    enc_key = settings.database_encryption_key

    # Open encrypted database
    enc_conn = sqlcipher.connect(db_path)
    enc_conn.execute(f"PRAGMA key='{enc_key}'")

    # Create unencrypted database
    plain_conn = sqlite3.connect(output_path)

    # Copy all data
    enc_conn.backup(plain_conn)

    enc_conn.close()
    plain_conn.close()

    return True


def import_database_encrypted(input_path: str, encryption_key: str) -> bool:
    """
    Import unencrypted SQLite database and encrypt it.

    Args:
        input_path: Path to unencrypted database
        encryption_key: Key to use for encryption

    Returns:
        True if successful
    """
    try:
        import pysqlcipher3.dbapi2 as sqlcipher
        import sqlite3
    except ImportError:
        raise ImportError("SQLCipher not available")

    db_path = settings.database_url.replace("sqlite:///", "")

    # Open unencrypted database
    plain_conn = sqlite3.connect(input_path)

    # Create encrypted database
    enc_conn = sqlcipher.connect(db_path)
    enc_conn.execute(f"PRAGMA key='{encryption_key}'")

    # Copy all data
    plain_conn.backup(enc_conn)

    plain_conn.close()
    enc_conn.close()

    return True
