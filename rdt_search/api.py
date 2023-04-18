import sqlite3
from functools import lru_cache

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from rdt_search import db, queries

router = APIRouter(prefix="/api/v1", tags=["api"])


@lru_cache(maxsize=1)
def get_db():
    return db.get_cursor("./data/radiot.db")


@lru_cache(maxsize=1)
def get_last_episode(db=Depends(get_db)) -> int:
    return queries.LastEpisode(db).execute()


class Stats(BaseModel):
    last_episode: int = Field(..., example=850, description="Last episode number in database")


@router.get("/", response_model=Stats)
def root(last_episode: int = Depends(get_last_episode)):
    return Stats(last_episode=last_episode)


class SearchResult(BaseModel):
    episode_number: int = Field(..., example=649, description="Episode number")
    start_time: str = Field(..., example="00:00:00", description="Start time of the fragment")
    end_time: str = Field(..., example="00:01:22", description="End time of the fragment")
    text: str = Field(..., example="кто-то опять щелкает", description="Text of the fragment")
    link: str = Field(
        ...,
        example=queries.link_to_fragment_start(853, 60),
        description="Link to the fragment start",
    )


@router.get("/search", response_model=list[SearchResult])
def search(
    q: str = Query(
        ...,
        example="бобок",
        description="FTS5 query. See https://www.sqlite.org/fts5.html#full_text_query_syntax",
    ),
    episode_number: int = Query(None, description="Episode number to search in"),
    order_by: queries.Search.OrderBy = queries.Search.OrderBy.RANK_ASC,
    db: sqlite3.Cursor = Depends(get_db),
):
    query = queries.Search(db)
    try:
        result = query.execute(q, episode_number=episode_number, order_by=order_by)
    except queries.SyntaxError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "loc": ["query", "q"],
                "msg": e.message,
                "type": "value_error",
            },
        )

    return [
        SearchResult(
            episode_number=item.episode_number,
            start_time=item.start_time.humanized,
            end_time=item.end_time.humanized,
            text=item.text,
            link=queries.link_to_fragment_start(
                episode_number=item.episode_number, seconds=item.start_time.seconds
            ),
        )
        for item in result
    ]


app = FastAPI()
app.include_router(router)
