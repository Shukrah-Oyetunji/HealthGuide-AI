from sqlalchemy import inspect, text

from database import engine


def migrate():
    inspector = inspect(engine)

    columns = {
        column["name"]
        for column in inspector.get_columns("question_history")
    }

    new_columns = {
        "answer": "TEXT",
        "sources": "JSON",
        "topic": "VARCHAR(100)",
    }

    with engine.begin() as connection:
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                connection.execute(
                    text(
                        f"ALTER TABLE question_history "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )
                print(f"Added column: {column_name}")

    print("Health Library database migration completed.")


if __name__ == "__main__":
    migrate()