import asyncio
from typing import Any, Dict, List

import aiohttp
from fastapi import HTTPException, Request


class GitHubService:
    def __init__(self):
        self.GITHUB_API_URL = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def set_authorization_header(self, request: Request):
        """Устанавливает заголовок 'Authorization'."""
        auth_header = request.headers.get("Authorization")
        self.headers = {
            **self.headers,
            "Authorization": auth_header if auth_header else "",
        }

    async def get_async(self, urls: List[str], text: bool = False) -> List[Any]:
        """Выполняет асинхронные GET запросы к списку URL."""
        if not urls:
            return []

        async with aiohttp.ClientSession() as session:

            async def fetch(url: str):
                if url == "":
                    return ""
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.text() if text else await response.json()
                    else:
                        error_detail = await response.text()
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"GitHub API error: {error_detail}",
                        )

            if type(urls) is list:
                return await asyncio.gather(*[fetch(url) for url in urls])
            else:
                return await fetch(urls)

    async def get_repo_info(self, owner: str, repo: str) -> dict:
        """Получает информацию о репозитории."""
        result = await self.get_async(f"{self.GITHUB_API_URL}/repos/{owner}/{repo}")
        return result if result else {}

    async def get_merged_prs(
        self,
        owner: str,
        repo: str,
        contributors: List[str],
        date_filter: str = "",
    ) -> dict:
        """Получает список объединенных PR от указанного контрибьютора."""
        urls = []
        for contributor in contributors:
            author = f"+author:{contributor}" if contributor else ""
            query = f"repo:{owner}/{repo}{author}+is:pr+is:merged{date_filter}"
            urls.append(f"{self.GITHUB_API_URL}/search/issues?q={query}")

        results = await self.get_async(urls)

        if len(contributors) > 1:
            return [
                {"login": contributor, "count": result["total_count"]}
                for result, contributor in zip(results, contributors)
            ]
        else:
            return results[0]

    async def get_prs_commits(
        self, owner: str, repo: str, contributor: str, pr_numbers: List[int]
    ) -> Dict[int, List[dict]]:
        """Получает коммиты для нескольких PR."""
        if not pr_numbers:
            return {}

        urls = [
            f"{self.GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/commits"
            for pr_number in pr_numbers
        ]
        results = await self.get_async(urls)

        return {
            pr_number: [
                commit
                for commit in commits
                if (
                    (str(commit["author"]["login"]).lower() == contributor.lower())
                    if contributor
                    else True
                )
            ]
            for pr_number, commits in zip(pr_numbers, results)
        }

    async def get_repo_contributors(self, owner: str, repo: str) -> Dict[str, dict]:
        """Получает детальную информацию о нескольких коммитах."""
        if not repo:
            return []

        url_contributors = f"{self.GITHUB_API_URL}/repos/{owner}/{repo}/contributors"

        contributors = await self.get_async(url_contributors)
        contributors = await self.get_async(
            [
                f"{self.GITHUB_API_URL}/users/{contributor['login']}"
                for contributor in contributors
            ]
        )

        contributors_email = {
            commits[-1]["author"]["login"]: commits[-1]["commit"]["author"]["email"]
            for commits in (
                await self.get_async(
                    [
                        f"https://api.github.com/repos/{owner}/{repo}/commits?author={contributor['login']}"
                        for contributor in contributors
                    ]
                )
            )
        }

        contributors = [
            {
                **contributor,
                "login": contributor["login"],
                "email": contributors_email[contributor_login],
            }
            for contributor, contributor_login in zip(contributors, contributors_email)
        ]

        return contributors

    async def get_commits_details(self, commit_urls: List[str]) -> List[dict]:
        """Получает детальную информацию о нескольких коммитах."""
        if not commit_urls:
            return []

        return await self.get_async(commit_urls)

    async def get_row_files(
        self, merged_prs: dict, pr_commits: dict, commit_details: dict
    ) -> List[dict]:
        """Получает код файлов в виде текста."""
        result = {}

        for pr_index, item in enumerate(merged_prs["items"]):
            pr_number = item["number"]
            commits_for_pr = pr_commits.get(pr_number, [])

            if not result.get(pr_index):
                result[pr_index] = {}

            for commit_index, commit_info in enumerate(commits_for_pr):
                commit_detail = commit_details.get(commit_info["url"], {})

                if not result.get(pr_index).get(commit_index):
                    result[pr_index][commit_index] = []

                result[pr_index][commit_index] = await self.get_async(
                    [
                        file["raw_url"] if ".json" not in file["filename"] else ""
                        for file in commit_detail.get("files", [])
                    ],
                    text=True,
                )

        return result
