import sqlite3
from pathlib import Path

def get_connection(db_path):
    """Return a fresh connection with rows accessible by column name."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok =True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection 

    # TODO: create the parent directory, connect, and set sqlite3.Row.

def initialize_database(db_path):
    """Create the movie table if it does not exist."""
    connection = get_connection(db_path)
    try: 
        sql_statement = """ 
        CREATE TABLE IF NOT EXISTS movies           
            ( id INTEGER  PRIMARY KEY, 
            title TEXT, 
            release_year INT, 
            rating REAL, 
            genre TEXT)""" 
        connection.execute(sql_statement)
        connection.commit()
    finally: 
        connection.close()

    # TODO: create the movie table if needed, commit, and close the connection.