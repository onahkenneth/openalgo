from sqlalchemy import text

def get_table_columns(conn, table_name):
    """Cross-database replacement for PRAGMA table_info()"""
    dialect = conn.engine.dialect.name

    if dialect == 'sqlite':
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        return [row[1] for row in result.fetchall()]

    elif dialect == 'postgresql':
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table
        """), {"table": table_name})
        return [row[0] for row in result.fetchall()]

    else:
        raise ValueError(f"Unsupported dialect: {dialect}")


def table_exists(conn, table_name):
    """Cross-database replacement for sqlite_master check"""
    dialect = conn.engine.dialect.name

    if dialect == 'sqlite':
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:table"
        ), {"table": table_name})
        return result.fetchone() is not None

    elif dialect == 'postgresql':
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = :table
        """), {"table": table_name})
        return result.fetchone() is not None

    else:
        raise ValueError(f"Unsupported dialect: {dialect}")