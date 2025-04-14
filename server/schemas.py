from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class PullRequest(BaseModel):
    url: str
    merged_at: datetime


class User(BaseModel):
    id: int
    login: str
    name: str
    email: str | None
    node_id: str
    avatar_url: str


class CommitAuthor(BaseModel):
    name: str
    email: str
    date: datetime


class File(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    raw: str
    patch: str


class Commit(BaseModel):
    sha: str
    author: CommitAuthor
    message: str
    url: str
    files: List[File]


class Item(BaseModel):
    id: int
    title: str
    body: str | Any
    pull_request: PullRequest
    commits: List[Commit]
    user: User
    number: int


class GitHubRepo(BaseModel):
    total_count: int
    incomplete_results: bool
    language: str
    topics: List[str]
    contributor_name: str | None
    contributor_email: str | None
    items: List[Item]
