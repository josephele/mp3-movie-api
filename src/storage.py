import logging
import sqlite3
import pandas as pd 

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)

MOVIE_COLUMNS = ["title", "release_year", "rating","genre"]
                 

class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        df = df.astype(object).where(pd.notnull(df), None)
        rows = list(df[MOVIE_COLUMNS].itertuples(index=False, name=None))
        connection = get_connection(self.db_path)
        try:
            sql_statement = "DELETE FROM movies"
            connection.execute(sql_statement)
            sql_statement = '''INSERT INTO movies (title, release_year, rating, genre)VALUES(?, ?, ?, ?)'''
            connection.executemany(sql_statement, rows)
            connection.commit()
            logger.debug(f"Saved movie count: rows = {len(rows)}")
        except sqlite3.Error:
            connection.rollback()
            raise
        finally: 
            connection.close()


    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = """
            SELECT title, release_year, rating, genre FROM movies
            ORDER BY id"""
            rows = connection.execute(sql_statement).fetchall()
            return pd.DataFrame(rows, columns= MOVIE_COLUMNS)
        finally: 
            connection.close()

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")
        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")
        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"SELECT {selected_columns} FROM movies ORDER BY id LIMIT ?"
            rows = connection.execute(sql_statement, (limit,)).fetchall()
            movies = [dict(row) for row in rows]
            logger.debug(f"returned {len(movies)} movie records""")
            return movies
        finally:
            connection.close()
             
    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = "SELECT COUNT(*) AS numMovie FROM movies"
            row = connection.execute(sql_statement).fetchone()
            return row["numMovie"]
        finally:
            connection.close()
    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        if not columns:
            logger.error("No column selected")
            raise ValueError
        for column in columns:
            if column not in MOVIE_COLUMNS: 
                logger.error(f"column not found: { column}")
                raise ValueError
        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try: 
            sql_statement = f""" SELECT {selected_columns} FROM movies WHERE rating >= ? ORDER BY rating DESC, id ASC LIMIT ?"""
            rows = connection.execute(sql_statement, (min_rating, limit)).fetchall()
            movies = [dict(row) for row in rows]
            logger.debug(f"number of movies: columns = {columns}, rows={len(movies)}")
            return movies 
        finally: 
            connection.close()

