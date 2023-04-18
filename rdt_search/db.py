import csv
import re
import sqlite3
from typing import Generator, Iterable, NamedTuple


def get_cursor(db_file: str) -> sqlite3.Cursor:
    conn = sqlite3.connect(db_file)
    conn.enable_load_extension(True)
    # https://github.com/abiliojr/fts5-snowball
    conn.load_extension("rdt_search/lib/fts5stemmer")
    return conn.cursor()


def create_index(cursor: sqlite3.Cursor) -> None:
    cursor.execute("""
        CREATE VIRTUAL TABLE
        radiot_search USING
        fts5(text, episode_number, start_time, end_time, tokenize = 'snowball russian english');
        """)


class Row(NamedTuple):
    text: str
    episode_number: int
    start_time: int
    end_time: int


def insert_rows(cursor: sqlite3.Cursor, rows: Iterable[Row]) -> None:
    cursor.executemany(
        """
        INSERT INTO radiot_search (text, episode_number, start_time, end_time)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )


def stream_data(data: Iterable) -> Generator[Row, None, None]:
    reader = csv.reader(data)
    next(reader)

    for row in reader:
        yield _parse_row(row)


def _parse_row(row: list[str]) -> Row:
    file_name, start, end, text = row
    episode_number = file_name.replace("rt_podcast", "").replace(".tsv", "")
    return Row(
        text=text.lower(),
        episode_number=int(episode_number),
        start_time=int(start),
        end_time=int(end),
    )


# https://github.com/simonw/datasette/blob/5890a20c374fb0812d88c9b0ef26a838bfa06c76/datasette/utils/__init__.py#L886-L897
_escape_fts_re = re.compile(r'\s+|(".*?")')


def escape_fts(query):
    # If query has unbalanced ", add one at end
    if query.count('"') % 2:
        query += '"'
    bits = _escape_fts_re.split(query)
    bits = [b for b in bits if b and b != '""']
    result = " ".join('"{}"'.format(bit) if not bit.startswith('"') else bit for bit in bits)
    print("query")
    print(result)
    return result
