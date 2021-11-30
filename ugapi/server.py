from typing import Optional

from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests
import json
import re
import urllib.parse

from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchQuery(BaseModel):
    query: str
    artist: Optional[str]
    type: Optional[str]


class TabQuery(BaseModel):
    url: str


class UGTabSearchResult(BaseModel):
    id: Optional[int]
    song_id: Optional[int]
    artist_id: Optional[int]
    type: Optional[str]
    part: Optional[str]
    version: Optional[int]
    votes: Optional[int]
    rating: Optional[float]
    artist_name: Optional[str]
    artist_url: Optional[str]
    song_name: Optional[str]
    marketing_type: Optional[str]
    tab_url: Optional[str]


class UGTabMeta(BaseModel):
    capo: Optional[int]
    key: Optional[str]
    tuning: Optional[str]
    difficulty: Optional[str]


class UGTab(BaseModel):
    url: str
    tab: str
    chords: List[str]
    meta: UGTabMeta


def filter_search(tabs: List[UGTabSearchResult], query: SearchQuery) -> List[UGTabSearchResult]:
    new_tabs = []
    for tab in tabs:
        if query.type and query.type != tab.type:
            continue
        if query.artist and query.artist != tab.artist_name:
            continue
        new_tabs.append(tab)
    return new_tabs

def clean_tab(tab: str) -> str:
    tab = re.sub(r"\[\/?ch\]", "", tab)
    tab = re.sub(r"\[\/?tab\]", "", tab)
    return tab

@app.post("/search")
def search(query: SearchQuery) -> List[UGTabSearchResult]:
    url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={urllib.parse.quote(query.query)}"
    search_page = requests.get(url)
    soup = BeautifulSoup(search_page.content, features="html.parser")
    store = soup.find("div", class_="js-store").attrs["data-content"]
    store = json.loads(store)
    search_results = store["store"]["page"]["data"]["results"]
    tabs = [UGTabSearchResult(
        id=result.get("id"),
        song_id=result.get("song_id"),
        artist_id=result.get("artist_id"),
        type=result.get("type"),
        part=result.get("part"),
        version=result.get("version"),
        votes=result.get("votes"),
        rating=result.get("rating"),
        artist_name=result.get("artist_name"),
        artist_url=result.get("artist_url"),
        song_name=result.get("song_name"),
        marketing_type=result.get("marketing_type"),
        tab_url=result.get("tab_url"))
        for result in search_results]
    tabs = filter_search(tabs, query)
    return tabs

@app.post("/tab")
def get_tab(query: TabQuery) -> UGTab:
    tab_page = requests.get(query.url)
    soup = BeautifulSoup(tab_page.content, features="html.parser")
    store = soup.find("div", class_="js-store").attrs["data-content"]
    store = json.loads(store)
    tab = store.get("store", {}).get("page", {}).get("data", {}).get("tab_view", {});
    tab_meta= tab.get("meta")
    return UGTab(url=query.url,
                 meta=UGTabMeta(key=tab_meta.get("tonality"),
                                capo=tab_meta.get("capo"),
                                difficulty=tab_meta.get("difficulty"),
                                tuning=f"{tab_meta.get('tuning').get('name')}: {tab_meta.get('tuning').get('value')}"
                                ),
                 tab=clean_tab(tab.get("wiki_tab").get("content")),
                 chords=list(tab.get("applicature", {}).keys()))

def serve():
    uvicorn.run("ugapi.server:app", host="0.0.0.0", port=8000)

def serve_debug():
    uvicorn.run("ugapi.server:app", host="0.0.0.0", port=8000, reload=True)
