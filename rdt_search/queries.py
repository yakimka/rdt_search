import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Generator, Iterable

from rdt_search.value_objects import Time

INDEX_NAME = "radiot_search"


class LastEpisode:
    def __init__(self, db: sqlite3.Cursor):
        self._db = db

    def execute(self) -> int:
        return self._db.execute(f"SELECT MAX(episode_number) FROM {INDEX_NAME}").fetchone()[0]


class SyntaxError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)

    @classmethod
    def from_operational_error(cls, error: str):
        message = error.replace("fts5:", "").strip()
        return cls(message)


class Search:
    @dataclass
    class SearchResult:
        episode_number: int
        start_time: Time
        end_time: Time
        text: str
        link: str

    class OrderBy(str, Enum):
        RANK_ASC = "rank_asc"
        RANK_DESC = "rank_desc"
        EPISODE_NUMBER_ASC = "episode_number_asc"
        EPISODE_NUMBER_DESC = "episode_number_desc"

        def to_sql(self):
            col, order = self.value.rsplit("_", maxsplit=1)
            return f"{col} {order.upper()}"

    def __init__(self, db: sqlite3.Cursor):
        self._db = db

    def execute(
        self, q: str, episode_number: int | None, order_by: OrderBy, limit: int = 100
    ) -> list[SearchResult]:
        episode_condition = ""
        if episode_number is not None:
            episode_condition = f" AND episode_number = {int(episode_number)}"

        query = (
            f"SELECT text, episode_number, start_time, end_time FROM {INDEX_NAME} WHERE text MATCH"
            f" ?{episode_condition} ORDER BY {order_by.to_sql()}, start_time LIMIT ?"
        )
        params = (q, limit)
        return list(self._parsed_rows(self._execute(query, params)))

    def _execute(self, query: str, params: tuple):
        try:
            return self._db.execute(query, params).fetchall()
        except sqlite3.OperationalError as e:
            if "syntax error" in e.args[0]:
                raise SyntaxError.from_operational_error(e.args[0])
            raise

    def _parsed_rows(self, rows: Iterable[tuple]) -> Generator[SearchResult, None, None]:
        for row in rows:
            text, ep, start, end = row
            yield self.SearchResult(
                episode_number=ep,
                start_time=Time(start),
                end_time=Time(end),
                text=text,
                link=link_to_fragment_start(episode_number=ep, seconds=Time(start).seconds),
            )


def link_to_fragment_start(episode_number: int, seconds: int) -> str:
    return f"https://cdn.radio-t.com/rt_podcast{episode_number}.mp3#t={seconds}"
