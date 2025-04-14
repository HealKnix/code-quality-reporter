import asyncio
from typing import Optional

import schemas
import services
import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

router = APIRouter()


@router.get(
    "/github/repo/{owner}/{repo}/mergedcount",
    summary="Получить список контрибьютеров с количеством мерджей в репозитории",
    tags=["GitHub"],
)
async def get_github_repo_merged_count(
    request: Request,
    owner: str,
    repo: str,
    date_filter: Optional[str] = Query(""),
    github_service: services.GitHubService = Depends(services.GitHubService),
):
    github_service.set_authorization_header(request)

    contributors = await github_service.get_repo_contributors(owner, repo)

    merges = await github_service.get_merged_prs(
        owner,
        repo,
        [contributor["login"] for contributor in contributors],
        f"+created:{date_filter}" if date_filter else "",
    )

    return merges


@router.get(
    "/github/repo/{owner}/{repo}/contributors",
    summary="Получить информацию о всех контрибьютерах в репозитории",
    tags=["GitHub"],
)
async def get_github_repo_contributors(
    request: Request,
    owner: str,
    repo: str,
    contributor_login_filter: Optional[str] = Query(""),
    contributor_email_filter: Optional[str] = Query(""),
    github_service: services.GitHubService = Depends(services.GitHubService),
):
    github_service.set_authorization_header(request)

    contributors = await github_service.get_repo_contributors(owner, repo)

    try:
        if contributor_login_filter:
            return [
                contributor
                for contributor in contributors
                if str(contributor["login"]).lower() == contributor_login_filter.lower()
            ][0]

        if contributor_email_filter:
            return [
                contributor
                for contributor in contributors
                if str(contributor["email"]).lower() == contributor_email_filter.lower()
            ][0]
    except Exception:
        return {}

    return contributors


@router.get(
    "/github/repo/merged/{owner}/{repo}",
    response_model=schemas.GitHubRepo,
    summary="Получить информацию о слитых PR в репозитории",
    description="Возвращает информацию о слитых PR от указанного контрибьютора в заданном диапазоне дат",
    tags=["GitHub"],
)
async def get_github_repo(
    request: Request,
    owner: str,
    repo: str,
    contributor_login_filter: Optional[str] = Query(""),
    contributor_email_filter: Optional[str] = Query(""),
    date_filter: Optional[str] = Query(""),
    github_service: services.GitHubService = Depends(services.GitHubService),
):
    github_service.set_authorization_header(request)

    # Формирование фильтра по датам
    if date_filter != "":
        date_filter = f"+created:{date_filter}"

    contributor_details = await github_service.get_repo_contributors(owner, repo)

    try:
        if contributor_email_filter and not contributor_login_filter:
            contributor_login_filter = [
                str(contributor["login"]).lower()
                for contributor in contributor_details
                if str(contributor["email"]).lower() == contributor_email_filter.lower()
            ][0]
    except Exception:
        contributor_login_filter = ""

    # Получение информации о репозитории
    try:
        # Запрашиваем информацию о репозитории и PR параллельно
        repo_info, merged_prs = await asyncio.gather(
            github_service.get_repo_info(owner, repo),
            github_service.get_merged_prs(
                owner, repo, [contributor_login_filter], date_filter
            ),
        )

        # Получаем номера PR
        pr_numbers = [item["number"] for item in merged_prs["items"]]

        # Запрашиваем информацию о пользователях и коммитах параллельно
        pr_commits = await github_service.get_prs_commits(
            owner, repo, contributor_login_filter, pr_numbers
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

        # Преобразовываем список контрибьютеров в словарь логинов
        contributor_details = {
            contributor["login"]: contributor for contributor in contributor_details
        }

        # Обогащаем данные пользователей
        for item in merged_prs["items"]:
            contributor_login = str(item["user"]["login"]).lower()
            contributor_info = contributor_details.get(contributor_login, {})
            item["user"] = schemas.User(
                **item["user"],
                name=contributor_info.get("name"),
                email=contributor_info.get("email"),
            )

        # raw_files = await github_service.get_row_files(
        #     merged_prs, pr_commits, commit_details
        # )

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
                        schemas.File(
                            filename=file["filename"],
                            additions=file["additions"],
                            deletions=file["deletions"],
                            changes=file["changes"],
                            status=file["status"],
                            patch=file.get("patch", ""),
                            # raw=raw_files[pr_index][commit_index][file_index],
                            raw=file["raw_url"],
                        )
                    )

                # Создание объекта коммита
                commits.append(
                    schemas.Commit(
                        sha=commit_info["sha"],
                        url=commit_info["url"],
                        author=schemas.CommitAuthor(**commit_info["commit"]["author"]),
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
        return schemas.GitHubRepo(
            **merged_prs, language=repo_info.get("language"), topics=topics
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении данных из GitHub: {str(e)}"
        )


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

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
