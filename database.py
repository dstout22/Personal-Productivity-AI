import sqlite3

import os

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "memory.db"
)

CATEGORIES = [
    "Tasks",
    "Projects",
    "Preferences",
    "Context",
    "Miscellaneous"
]


def get_connection():
    return sqlite3.connect(DATABASE)


def initialize_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


def add_memory(category, content):
    if category not in CATEGORIES:
        raise ValueError(f"Invalid category: {category}")

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO memories (category, content)
        VALUES (?, ?)
        """,
        (category, content)
    )

    memory_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return memory_id


def get_memories(category=None):
    connection = get_connection()

    if category is None:
        cursor = connection.execute(
            """
            SELECT id, category, content, created_at, updated_at
            FROM memories
            ORDER BY created_at
            """
        )
    else:
        if category not in CATEGORIES:
            raise ValueError(f"Invalid category: {category}")

        cursor = connection.execute(
            """
            SELECT id, category, content, created_at, updated_at
            FROM memories
            WHERE category = ?
            ORDER BY created_at
            """,
            (category,)
        )

    memories = cursor.fetchall()
    connection.close()

    return memories


def update_memory(memory_id, content, category=None):
    connection = get_connection()

    if category is not None:
        if category not in CATEGORIES:
            raise ValueError(f"Invalid category: {category}")

        connection.execute(
            """
            UPDATE memories
            SET content = ?, category = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (content, category, memory_id)
        )
    else:
        connection.execute(
            """
            UPDATE memories
            SET content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (content, memory_id)
        )

    connection.commit()
    connection.close()


def delete_memory(memory_id):
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM memories
        WHERE id = ?
        """,
        (memory_id,)
    )

    connection.commit()
    connection.close()