import asyncio
import os

import aiohttp
import model
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

headers = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
}

app = FastAPI()

# CORS allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)


async def get_async(urls, text=False):
    async with aiohttp.ClientSession() as session:

        async def fetch(url):
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    if text:
                        return await response.text()
                    return await response.json()
                else:
                    raise HTTPException(
                        status_code=response.status, detail=await response.text()
                    )

        return await asyncio.gather(*[fetch(url) for url in urls])


@app.get("/github/repo/merged/{owner}/{repo}/{contributor}/{date_start}/{date_end}")
async def get_github_repo(
    owner: str, repo: str, contributor: str, date_start: str, date_end: str
):
    if date_start == "0" or date_end == "0":
        date_str = ""
    else:
        date_str = f"+created:{date_start}..{date_end}"

    response_repo = (await get_async([f"https://api.github.com/repos/{owner}/{repo}"]))[
        0
    ]

    response_merges = (
        await get_async(
            [
                f"https://api.github.com/search/issues?q=repo:{owner}/{repo}+author:{contributor}+is:pr+is:merged{date_str}"
            ]
        )
    )[0]

    response_users = await get_async(
        [
            f"https://api.github.com/users/{item['user']['login']}"
            for item in response_merges["items"]
        ]
    )

    for index, item in enumerate(response_merges["items"]):
        item["user"] = model.User(
            **item["user"],
            name=response_users[index]["name"],
            email=response_users[index]["email"],
        )

    response_commits = await get_async(
        [
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{item['number']}/commits"
            for item in response_merges["items"]
        ]
    )

    for index, item in enumerate(response_merges["items"]):
        commits = []
        commits_with_files_dict = {}

        for commit in response_commits[index]:
            if not commits_with_files_dict.get(index):
                commits_with_files_dict[index] = []
            commits_with_files_dict[index].append(commit["url"])

        commits_with_files_in_merge = []
        for key in commits_with_files_dict:
            commits_with_files_in_merge = await get_async(commits_with_files_dict[key])

        for commit in commits_with_files_in_merge:
            file_list = []

            for commit_with_files in commits_with_files_in_merge:
                for file in commit_with_files["files"]:
                    patch = ""

                    if file.get("patch"):
                        patch = file["patch"]

                    file_list.append(
                        model.File(
                            filename=file["filename"],
                            additions=file["additions"],
                            deletions=file["deletions"],
                            changes=file["changes"],
                            status=file["status"],
                            patch=patch,
                            raw=file["raw_url"],
                        )
                    )

            commits.append(
                model.Commit(
                    sha=commit["sha"],
                    url=commit["url"],
                    author=model.CommitAuthor(**commit["commit"]["author"]),
                    message=commit["commit"]["message"],
                    files=file_list,
                )
            )

        item["commits"] = commits

    topics = response_repo["topics"]

    if len(topics) == 0:
        topics = response_repo["source"]["topics"]

    return model.GitHubRepo(
        **response_merges, language=response_repo["language"], topics=topics
    )
