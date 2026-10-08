from pathlib import Path

from db import get_connection

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"

def main() -> None:
    schema_sql = SCHEMA_PATH.read_text()

    connection = get_connection()
    cur = connection.cursor()
    cur.execute(schema_sql)  
    connection.commit()

    cur.close()
    connection.close()
    print("Schema applied.")


if __name__ == "__main__":
    main()