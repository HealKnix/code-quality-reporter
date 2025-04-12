import asyncio
import os
from typing import List, Dict, Any

import aiohttp
import model
import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Константы и конфигурация
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN не найден в переменных окружения")

GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
}

GITHUB_API_URL = "https://api.github.com"

app = FastAPI(
    title="GitHub Code Quality Reporter API",
    description="API для анализа PR и коммитов в GitHub репозиториях",
    version="1.0.0",
)

# CORS конфигурация
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Сервис для работы с GitHub API
class GitHubService:
    def __init__(self, headers: dict):
        self.headers = headers

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

            return await asyncio.gather(*[fetch(url) for url in urls])

    async def get_repo_info(self, owner: str, repo: str) -> dict:
        """Получает информацию о репозитории."""
        results = await self.get_async([f"{GITHUB_API_URL}/repos/{owner}/{repo}"])
        return results[0] if results else {}

    async def get_merged_prs(
        self, owner: str, repo: str, contributor: str, date_filter: str = ""
    ) -> dict:
        """Получает список объединенных PR от указанного контрибьютора."""
        query = f"repo:{owner}/{repo}+author:{contributor}+is:pr+is:merged{date_filter}"
        url = f"{GITHUB_API_URL}/search/issues?q={query}"
        results = await self.get_async([url])
        return results[0] if results else {"items": []}

    async def get_users_details(self, logins: List[str]) -> Dict[str, dict]:
        """Получает детальную информацию о нескольких пользователях."""
        if not logins:
            return {}

        unique_logins = list(set(logins))
        urls = [f"{GITHUB_API_URL}/users/{login}" for login in unique_logins]
        results = await self.get_async(urls)

        return {login: result for login, result in zip(unique_logins, results)}

    async def get_prs_commits(
        self, owner: str, repo: str, pr_numbers: List[int]
    ) -> Dict[int, List[dict]]:
        """Получает коммиты для нескольких PR."""
        if not pr_numbers:
            return {}

        urls = [
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/commits"
            for pr_number in pr_numbers
        ]
        results = await self.get_async(urls)

        return {pr_number: commits for pr_number, commits in zip(pr_numbers, results)}

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


# Зависимость для внедрения GitHubService
def get_github_service():
    return GitHubService(GITHUB_HEADERS)


@app.get(
    "/github/repo/merged/{owner}/{repo}/{contributor}/{date_start}/{date_end}",
    response_model=model.GitHubRepo,
    summary="Получить информацию о слитых PR в репозитории",
    description="Возвращает информацию о слитых PR от указанного контрибьютора в заданном диапазоне дат",
)
async def get_github_repo(
    owner: str,
    repo: str,
    contributor: str,
    date_start: str,
    date_end: str,
    github_service: GitHubService = Depends(get_github_service),
):
    # Формирование фильтра по датам
    date_filter = ""
    if date_start != "0" and date_end != "0":
        date_filter = f"+created:{date_start}..{date_end}"

    # Получение информации о репозитории
    try:
        # Запрашиваем информацию о репозитории и PR параллельно
        repo_info, merged_prs = await asyncio.gather(
            github_service.get_repo_info(owner, repo),
            github_service.get_merged_prs(owner, repo, contributor, date_filter),
        )

        if not merged_prs.get("items"):
            # Если PR не найдены, возвращаем пустой результат
            return model.GitHubRepo(
                items=[],
                total_count=0,
                language=repo_info.get("language"),
                topics=repo_info.get("topics", []),
            )

        # Получаем уникальные логины пользователей
        user_logins = [item["user"]["login"] for item in merged_prs["items"]]

        # Получаем номера PR
        pr_numbers = [item["number"] for item in merged_prs["items"]]

        # Запрашиваем информацию о пользователях и коммитах параллельно
        user_details, pr_commits = await asyncio.gather(
            github_service.get_users_details(user_logins),
            github_service.get_prs_commits(owner, repo, pr_numbers),
        )

        # Собираем все URL коммитов
        commit_urls = []
        for commits in pr_commits.values():
            commit_urls.extend([commit["url"] for commit in commits])

        # Получаем детали коммитов
        commit_details = {}
        if commit_urls:
            commit_details_list = await github_service.get_commits_details(commit_urls)
            commit_details = {detail["url"]: detail for detail in commit_details_list}

        # Обогащаем данные пользователей
        for item in merged_prs["items"]:
            user_login = item["user"]["login"]
            user_info = user_details.get(user_login, {})
            item["user"] = model.User(
                **item["user"], name=user_info.get("name"), email=user_info.get("email")
            )

        raw_files = await github_service.get_row_files(
            merged_prs, pr_commits, commit_details
        )

        # Обогащаем данные о коммитах
        for pr_index, item in enumerate(merged_prs["items"]):
            pr_number = item["number"]
            commits_for_pr = pr_commits.get(pr_number, [])

            commits = []
            for commit_index, commit_info in enumerate(commits_for_pr):
                # Получение детальной информации о коммите
                commit_detail = commit_details.get(commit_info["url"], {})

                # Обработка файлов в коммите
                file_list = []
                for file_index, file in enumerate(commit_detail.get("files", [])):
                    file_list.append(
                        model.File(
                            filename=file["filename"],
                            additions=file["additions"],
                            deletions=file["deletions"],
                            changes=file["changes"],
                            status=file["status"],
                            patch=file.get("patch", ""),
                            raw=raw_files[pr_index][commit_index][file_index],
                        )
                    )

                # Создание объекта коммита
                commits.append(
                    model.Commit(
                        sha=commit_info["sha"],
                        url=commit_info["url"],
                        author=model.CommitAuthor(**commit_info["commit"]["author"]),
                        message=commit_info["commit"]["message"],
                        files=file_list,
                    )
                )

            item["commits"] = commits

        # Получение топиков репозитория
        topics = repo_info.get("topics", [])
        if not topics and "source" in repo_info:
            topics = repo_info["source"].get("topics", [])

        # Формирование и возврат результата
        return model.GitHubRepo(
            **merged_prs, language=repo_info.get("language"), topics=topics
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении данных из GitHub: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
