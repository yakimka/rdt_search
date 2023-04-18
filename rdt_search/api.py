import re
import time
from enum import Enum
from functools import cached_property, lru_cache

from fastapi import APIRouter, Depends, FastAPI, Query
from pydantic import BaseModel, Field

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
            return f"{col} {order.upper()}"

    def __init__(self, db):
        self._db = db

    @cached_property
    def last_episode(self):
        return self._db.execute(f"SELECT MAX(episode_number) FROM {self.INDEX_NAME}").fetchone()[0]

    def search(self, q: str, exact: bool, order_by: OrderBy, limit: int = 30):
        match = "?" if exact else "? || '*'"
        return list(
            self._db.execute(
                (
                    f"SELECT * FROM {self.INDEX_NAME} WHERE text MATCH {match} ORDER BY"
                    f" {order_by.to_sql()} LIMIT ?"
                ),
                (db.escape_fts(q), limit),
            ).fetchall()
        )


@lru_cache(maxsize=1)
def get_finder(db=Depends(get_db)):
    return Finder(db)


class Stats(BaseModel):
    last_episode: int = Field(..., example=850, description="Last episode number in database")


@router.get("/", response_model=Stats)
def root(finder=Depends(get_finder)):
    return {"last_episode": finder.last_episode}


class SearchResult(BaseModel):
    episode_number: int = Field(..., example=649, description="Episode number")
    start_time: str = Field(..., example="00:00:00", description="Start time of the fragment")
    end_time: str = Field(..., example="00:01:22", description="End time of the fragment")
    text: str = Field(..., example="кто-то опять щелкает", description="Text of the fragment")

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
def search(
    q: str = Query(..., example="бобок", description="Search query"),
    exact: bool = Query(False, description="Search by exact match or not"),
    order_by: Finder.OrderBy = Finder.OrderBy.RANK_ASC,
    finder=Depends(get_finder),
):
    result = finder.search(q, exact=exact, order_by=order_by)
    return [SearchResult.from_db_row(row) for row in result]


app = FastAPI()
app.include_router(router)
