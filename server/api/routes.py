import uuid
from typing import Dict, Optional
import threading

import schemas
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from services.github_service import GitHubService
from services.report_generator import generate_github_report
from utils.file_utils import get_report_file_path

# Dictionary to store the status of background tasks
# Ключ - task_id, значение - информация о задаче
report_tasks: Dict[str, Dict] = {}
# Блокировка для безопасного доступа к словарю report_tasks
report_tasks_lock = threading.Lock()


# Email request model
class EmailRequest(BaseModel):
    email: EmailStr


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
    github_service: GitHubService = Depends(GitHubService),
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


@router.post(
    "/github/repo/merged/{owner}/{repo}/async",
    summary="Асинхронно сгенерировать отчеты о PR в репозитории для выбранных контрибьютеров и отправить на почту",
    tags=["GitHub"],
)
async def get_github_repo_async(
    request: Request,
    owner: str,
    repo: str,
    email_data: EmailRequest,
    background_tasks: BackgroundTasks,
    contributors: Optional[str] = Query(
        ""
    ),  # Now expects comma-separated list of logins
    contributor_email_filter: Optional[str] = Query(""),
    date_filter: Optional[str] = Query(""),
    github_service: GitHubService = Depends(GitHubService),
):
    github_service.set_authorization_header(request)

    # Generate a unique task ID
    task_id = str(uuid.uuid4())

    # Parse contributors list
    contributor_logins = []
    if contributors:
        contributor_logins = [
            login.strip() for login in contributors.split(",") if login.strip()
        ]

    # Store initial task info with thread-safe access
    with report_tasks_lock:
        report_tasks[task_id] = {
            "status": "processing",
            "owner": owner,
            "repo": repo,
            "email": email_data.email,
            "contributors": contributor_logins,
            "date_filter": date_filter,
            "pending_contributors": contributor_logins.copy()
            if contributor_logins
            else [],
            "completed_contributors": [],
            "results": {},
        }

    # Process each contributor in the background
    if contributor_logins:
        for contributor_login in contributor_logins:
            background_tasks.add_task(
                generate_github_report,
                task_id,
                owner,
                repo,
                contributor_login,
                contributor_email_filter,
                date_filter,
                email_data.email,
                github_service,
                report_tasks,
            )

    return {"task_id": task_id, "status": "processing"}


@router.get(
    "/github/tasks/{task_id}",
    summary="Получить статус асинхронной задачи",
    tags=["Tasks"],
)
@router.get(
    "/task/{task_id}",  # Added for backward compatibility with the client
    summary="Получить статус асинхронной задачи",
    tags=["Tasks"],
)
async def get_task_status(task_id: str):
    """Get the status of a background task"""
    # Безопасный доступ к словарю report_tasks
    with report_tasks_lock:
        if task_id not in report_tasks:
            raise HTTPException(status_code=404, detail="Task not found")

        # Создаем копию информации о задаче, чтобы избежать проблем с параллельным доступом
        task_info = dict(report_tasks[task_id])

    response = {
        "task_id": task_id,
        "status": task_info["status"],
    }

    # Include information about pending, completed, and failed contributors
    if "pending_contributors" in task_info:
        response["pending_contributors"] = task_info["pending_contributors"]
    if "completed_contributors" in task_info:
        response["completed_contributors"] = task_info["completed_contributors"]
    if "failed_contributors" in task_info:
        response["failed_contributors"] = task_info["failed_contributors"]

    # Include the contributor currently being processed
    if "processing_contributor" in task_info:
        response["processing_contributor"] = task_info["processing_contributor"]

    # For multi-contributor reports, return all completed results
    if "results" in task_info and task_info["results"]:
        response["results"] = task_info["results"]

    # Error handling
    if task_info["status"] == "failed" and "error" in task_info:
        response["error"] = task_info["error"]

    return response


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
    github_service: GitHubService = Depends(GitHubService),
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
    github_service: GitHubService = Depends(GitHubService),
):
    github_service.set_authorization_header(request)

    # Формирование фильтра по датам
    if date_filter != "":
        date_filter = f"+created:{date_filter}"

    # Формирование фильтра по датам
    if contributor_login_filter != "":
        contributor_login_filter = contributor_login_filter.lower()
    if contributor_email_filter != "":
        contributor_email_filter = contributor_email_filter.lower()

    contributor_details = await github_service.get_repo_contributors(owner, repo)

    try:
        if contributor_email_filter and not contributor_login_filter:
            contributor_login_filter = [
                str(contributor["login"]).lower()
                for contributor in contributor_details
                if str(contributor["email"]).lower() == contributor_email_filter
            ][0]
    except Exception:
        contributor_login_filter = ""

    # Получение информации о репозитории
    try:
        # Запрашиваем информацию о репозитории и PR параллельно
        import asyncio

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
            contributor["login"].lower(): contributor
            for contributor in contributor_details
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

        # Не убирать!
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
                            # Не убирать!
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

        contributor_name = (
            contributor_details.get(contributor_login_filter, {}).get("name")
            if contributor_details.get(contributor_login_filter, {}).get("name")
            else contributor_details.get(contributor_login_filter, {}).get("login")
            if contributor_login_filter or contributor_email_filter
            else None
        )

        contributor_email = (
            contributor_details.get(contributor_login_filter, {}).get("email")
            if contributor_login_filter or contributor_email_filter
            else None
        )

        # Формирование и возврат результата
        return schemas.GitHubRepo(
            **merged_prs,
            language=repo_info.get("language"),
            topics=topics,
            contributor_name=contributor_name,
            contributor_email=contributor_email,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ошибка при получении данных из GitHub: {str(e)}"
        )


@router.get(
    "/download-report/{owner}/{repo}/{filename}",
    summary="Download a PDF report for a specific contributor",
    tags=["Reports"],
)
async def download_report(
    owner: str,
    repo: str,
    filename: str,
):
    file_path = get_report_file_path(owner, repo, filename)  # Путь к файлу
    import os

    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, filename=filename, media_type="application/octet-stream"
        )
    return {"error": "Файл не найден"}
