import os
import sqlite3
import argparse
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


def reset_database(db_path="ainews.db", mode="clear"):
    """
    Reset the database by either clearing tables or deleting the file

    Args:
        db_path: Path to the database file
        mode: 'clear' to empty tables, 'delete' to remove the file entirely
    """
    if not os.path.exists(db_path):
        logging.warning(f"Database file {db_path} does not exist.")
        return False

    try:
        if mode == "delete":
            # Delete the entire database file
            os.remove(db_path)
            logging.info(f"Database file {db_path} deleted successfully.")
            return True
        else:  # clear mode
            # Connect and clear all tables
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all tables in the database
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            for table in tables:
                table_name = table[0]
                if table_name != "sqlite_sequence":  # Skip internal SQLite tables
                    cursor.execute(f"DELETE FROM {table_name}")
                    logging.info(f"Cleared table: {table_name}")

            conn.commit()
            conn.close()
            logging.info(f"All tables in {db_path} cleared successfully.")
            return True

    except Exception as e:
        logging.error(f"Error resetting database: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Reset the AI News Scraper database')
    parser.add_argument('--db', default="ainews.db", help='Path to the database file')
    parser.add_argument('--mode', choices=['clear', 'delete'], default='clear',
                        help='Mode: clear tables or delete file')

    args = parser.parse_args()

    if reset_database(args.db, args.mode):
        logging.info("Database reset operation completed successfully.")
    else:
        logging.error("Database reset operation failed.")