import psycopg2
from psycopg2 import sql
from db_scripts.db_utils import get_db_connection

def generic_create(env: str, schema: str, table_name, data):
    """
    Generic CREATE function for database operations.

    Args:
        env: Environment to use (dev or prod)
        schema (str): Schema to use
        table_name (str): Name of the table to insert data into.
        data (dict): Dictionary containing column names as keys and values to insert.

    Returns:
        dict: Newly created record as a dictionary, or None on failure.
    """
    try:
        conn = get_db_connection(env)
        cursor = conn.cursor()
        columns = list(data.keys())
        values = [data[k] for k in columns]
        query = sql.SQL("INSERT INTO {}.{} ({}) VALUES %s RETURNING *").format(
            sql.Identifier(schema),
            sql.SQL(table_name),
            sql.SQL(', ').join(map(sql.Identifier, columns))
        )
        cursor.execute(query, (tuple(values),))
        created_record = cursor.fetchone()
        conn.commit()
        return dict(zip([col.name for col in cursor.description], created_record)) if created_record else None
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Database error in generic_create: {e}")
        return None


def generic_read(env: str, table_name, condition=None, columns='*', order_by=None, limit=None):
    """
    Generic READ function for database operations.

    Args:
        env: Environment to use (dev or prod)
        table_name (str): Name of the table to read data from.
        condition (dict, optional): WHERE clause conditions. Defaults to None.
        columns (str or list, optional): Columns to select. Defaults to '*'.
        order_by (str, optional): Column to order results by. Defaults to None.
        limit (int, optional): Maximum number of records to retrieve. Defaults to None.

    Returns:
        list: List of records as dictionaries, or None on failure.
    """
    try:
        conn = get_db_connection(env)
        cursor = conn.cursor()
        query_parts = ["SELECT"]
        if columns == '*':
            query_parts.append(sql.SQL("*"))
        else:
            query_parts.append(sql.SQL(', ').join(map(sql.Identifier, columns)))
        query_parts.append(sql.SQL("FROM {}").format(sql.Identifier(table_name)))

        if condition:
            condition_parts = [sql.SQL("{} = %s").format(sql.Identifier(key)) for key in condition.keys()]
            query_parts.append(sql.SQL("WHERE ") + sql.SQL(" AND ").join(condition_parts))

        if order_by:
            query_parts.append(sql.SQL("ORDER BY {}").format(sql.Identifier(order_by)))
        if limit:
            query_parts.append(sql.SQL("LIMIT %s"))

        query = sql.SQL(' ').join(query_parts)
        params = list(condition.values()) if condition else []
        if limit:
            params.append(limit)

        cursor.execute(query, params)
        results = cursor.fetchall()
        return [dict(zip([col.name for col in cursor.description], row)) for row in results]
    except psycopg2.Error as e:
        print(f"Database error in generic_read: {e}")
        return None


def generic_update(env: str, table_name, data, condition):
    """
    Generic UPDATE function for database operations.

    Args:
        env: Environment to use (dev or prod)
        table_name (str): Name of the table to update.
        data (dict): Dictionary containing column names as keys and values to update.
        condition (dict): WHERE clause conditions to identify records to update.

    Returns:
        dict: Updated record as a dictionary, or None on failure.
    """
    try:
        conn = get_db_connection(env)
        cursor = conn.cursor()
        set_parts = [sql.SQL("{} = %s").format(sql.Identifier(key)) for key in data.keys()]
        condition_parts = [sql.SQL("{} = %s").format(sql.Identifier(key)) for key in condition.keys()]

        query = sql.SQL("UPDATE {} SET {} WHERE {} RETURNING *").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(set_parts),
            sql.SQL(" AND ").join(condition_parts)
        )
        params = list(data.values()) + list(condition.values())
        cursor.execute(query, params)
        updated_record = cursor.fetchone()
        conn.commit()
        return dict(zip([col.name for col in cursor.description], updated_record)) if updated_record else None
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Database error in generic_update: {e}")
        return None


def generic_delete(env: str, table_name, condition):
    """
    Generic DELETE function for database operations.

    Args:
        env: Environment to use (dev or prod)
        table_name (str): Name of the table to delete data from.
        condition (dict): WHERE clause conditions to identify records to delete.

    Returns:
        dict: Deleted record as a dictionary, or None on failure.
    """
    try:
        conn = get_db_connection(env)
        cursor = conn.cursor()
        condition_parts = [sql.SQL("{} = %s").format(sql.Identifier(key)) for key in condition.keys()]
        query = sql.SQL("DELETE FROM {} WHERE {} RETURNING *").format(
            sql.Identifier(table_name),
            sql.SQL(" AND ").join(condition_parts)
        )
        params = list(condition.values())
        cursor.execute(query, params)
        deleted_record = cursor.fetchone()
        conn.commit()
        return dict(zip([col.name for col in cursor.description], deleted_record)) if deleted_record else None
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Database error in generic_delete: {e}")
        return None
