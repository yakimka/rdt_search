import time
from dataclasses import dataclass
from enum import Enum
from functools import cached_property, lru_cache

from fastapi import APIRouter, Depends, FastAPI

from rdt_search import db

router = APIRouter(prefix="/api/v1", tags=["api"])


@lru_cache(maxsize=1)
def get_db():
    return db.get_cursor("./data/radiot.db")


class Finder:
    INDEX_NAME = "radiot_search"

    class OrderBy(str, Enum):
        RANK_ASC = "rank_asc"
        RANK_DESC = "rank_desc"
        EPISODE_NUMBER_ASC = "episode_number_asc"
        EPISODE_NUMBER_DESC = "episode_number_desc"

        def to_sql(self):
            col, order = self.value.rsplit("_", maxsplit=1)
            print(f"{col} {order.upper()}")
            return f"{col} {order.upper()}"

    def __init__(self, db):
        self._db = db

    @cached_property
    def last_episode(self):
        return self._db.execute(f"SELECT MAX(episode_number) FROM {self.INDEX_NAME}").fetchone()[0]

    def search(self, q: str, order_by: OrderBy, limit: int = 30):
        return list(
            self._db.execute(
                f"SELECT * FROM {self.INDEX_NAME} WHERE text MATCH ? ORDER BY {order_by.to_sql()} LIMIT ?",
                (db.escape_fts(q), limit),
            ).fetchall()
            )


@lru_cache(maxsize=1)
def get_finder(db=Depends(get_db)):
    print("Creating finder")
    return Finder(db)


@router.get("/")
def root(finder=Depends(get_finder)):
    return {"last_episode": finder.last_episode}


@dataclass
class SearchResult:
    episode_number: int
    start_time: str
    end_time: str
    text: str

    @classmethod
    def from_db_row(cls, row):
        ep, start, end, text = row
        return cls(
            episode_number=ep,
            start_time=_miliseconds_to_time(start),
            end_time=_miliseconds_to_time(end),
            text=text,
        )


def _miliseconds_to_time(miliseconds):
    seconds = miliseconds / 1000
    return time.strftime("%H:%M:%S", time.gmtime(seconds))


@router.get("/search", response_model=list[SearchResult])
def search(q: str, order_by: Finder.OrderBy, finder=Depends(get_finder)):
    result = finder.search(q, order_by=order_by)
    return [SearchResult.from_db_row(row) for row in result]


app = FastAPI()
app.include_router(router)
