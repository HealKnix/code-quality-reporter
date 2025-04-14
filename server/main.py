import asyncio
import os
import uuid
from typing import Dict, Optional

import schemas
import services
import uvicorn
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


# Email request model
class EmailRequest(BaseModel):
    email: EmailStr


# Dictionary to store the status of background tasks
report_tasks: Dict[str, Dict] = {}


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


async def send_email_report(email: str, report_data: dict, task_id: str):
    """Send email with report"""
    try:
        sender_email = os.getenv("EMAIL_SENDER")
        password = os.getenv("EMAIL_PASSWORD")
        smtp_server = "smtp.gmail.com"
        smtp_port = 587  # Note: This should be an integer, not a string

        if not sender_email or not password:
            print(
                "Email credentials not configured. Report was generated but not sent."
            )
            report_tasks[task_id]["status"] = "completed-no-email"
            return

        print(f"Attempting to send email from {sender_email} to {email}")

        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = (
            f"GitHub Code Quality Report for {report_data['repo_owner']}/{report_data['repo_name']}"
        )
        message["From"] = sender_email
        message["To"] = email

        # Create HTML content
        html = f"""
        <html>
            <body>
                <h2>GitHub Code Quality Report</h2>
                <p>Your report for repository {report_data["repo_owner"]}/{report_data["repo_name"]} is ready.</p>
                <p>Report generated for {report_data["contributor_name"]} in the date range: {report_data.get("date_range", "All time")}</p>
                <p>You can view the details by returning to the application.</p>
            </body>
        </html>
        """

        part = MIMEText(html, "html")
        message.attach(part)

        # Send email
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                print("Attempting SMTP login...")
                server.login(sender_email, password)
                print("SMTP login successful")
                server.sendmail(sender_email, email, message.as_string())
                print(f"Email sent successfully to {email}")

            report_tasks[task_id]["status"] = "completed"
        except smtplib.SMTPAuthenticationError as auth_error:
            error_msg = str(auth_error)
            print(f"SMTP Authentication Error: {error_msg}")
            print("\nFor Gmail users:\n")
            print(
                "1. Make sure you're using an App Password, not your regular password"
            )
            print(
                "2. Create an App Password at: https://myaccount.google.com/apppasswords"
            )
            print("3. Update your .env file with the new App Password")

            report_tasks[task_id]["status"] = "completed-email-failed"
            report_tasks[task_id]["error"] = (
                f"Authentication failed. Use an App Password for Gmail: {error_msg}"
            )
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            report_tasks[task_id]["status"] = "completed-email-failed"
            report_tasks[task_id]["error"] = str(e)
    except Exception as e:
        print(f"Error preparing email: {str(e)}")
        report_tasks[task_id]["status"] = "completed-email-failed"
        report_tasks[task_id]["error"] = str(e)


async def generate_github_report(
    task_id: str,
    owner: str,
    repo: str,
    contributor_login_filter: str,
    contributor_email_filter: str,
    date_filter: str,
    user_email: str,
    github_service: services.GitHubService,
):
    """Background task to generate GitHub report"""
    try:
        # Original get_github_repo code
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
                matching_logins = [
                    str(contributor["login"]).lower()
                    for contributor in contributor_details
                    if str(contributor["email"]).lower() == contributor_email_filter
                ]
                if matching_logins:  # Check if list is not empty
                    contributor_login_filter = matching_logins[0]
                else:
                    contributor_login_filter = ""
        except Exception as e:
            print(f"Error finding contributor by email: {str(e)}")
            contributor_login_filter = ""

        # Получение информации о репозитории
        repo_info = await github_service.get_repo_info(owner, repo)

        # Построение запроса
        contributor_login = contributor_login_filter
        contributor_details = {c["login"].lower(): c for c in contributor_details}

        # Get merged PRs by the contributor
        merged_prs = await github_service.get_merged_prs(
            owner, repo, [contributor_login], date_filter
        )

        if merged_prs["total_count"] == 0:
            # No merged PRs by this contributor
            result = schemas.GitHubRepo(
                total_count=0,
                items=[],
                contributor_name=contributor_details.get(contributor_login, {}).get(
                    "name", ""
                ),
                contributor_email=contributor_details.get(contributor_login, {}).get(
                    "email", ""
                ),
                language=repo_info.get("language", ""),
                topics=repo_info.get("topics", []),
            )
            report_tasks[task_id]["result"] = result.dict()
            report_tasks[task_id]["status"] = "completed"

            await send_email_report(
                user_email,
                {
                    "repo_owner": owner,
                    "repo_name": repo,
                    "contributor_name": result.contributor_name or "all contributors",
                    "date_range": date_filter.replace("+created:", "")
                    if date_filter
                    else "All time",
                },
                task_id,
            )
            return

        # Get commits for each PR
        if "items" in merged_prs and merged_prs["items"]:
            pr_numbers = [item["number"] for item in merged_prs["items"]]
            pr_commits = await github_service.get_prs_commits(
                owner, repo, contributor_login, pr_numbers
            )
        else:
            # No PRs found, create empty dict
            pr_commits = {}

        # Get commit details
        commit_urls = []
        for commits in pr_commits.values():
            if commits:  # Make sure commits exist
                commit_urls.extend(
                    [commit["url"] for commit in commits if "url" in commit]
                )

        commit_details = {}
        if commit_urls:
            try:
                details = await github_service.get_commits_details(commit_urls)
                if details:  # Make sure details are returned
                    commit_details = dict(zip(commit_urls, details))
            except Exception as e:
                print(f"Error getting commit details: {str(e)}")

        # Enrich the PRs with user info
        if "items" in merged_prs:
            for item in merged_prs["items"]:
                if "user" in item and "login" in item["user"]:
                    contributor_login = str(item["user"]["login"]).lower()
                    contributor_info = contributor_details.get(contributor_login, {})
                    item["user"] = schemas.User(
                        **item["user"],
                        name=contributor_info.get("name"),
                        email=contributor_info.get("email"),
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

        # Формирование и сохранение результата
        result = schemas.GitHubRepo(
            **merged_prs,
            language=repo_info.get("language"),
            topics=topics,
            contributor_name=contributor_name,
            contributor_email=contributor_email,
        )

        # Store the result
        report_tasks[task_id]["result"] = result.dict()
        report_tasks[task_id]["status"] = "completed"

        print("Report generated successfully")

        # Send email with report
        await send_email_report(
            user_email,
            {
                "repo_owner": owner,
                "repo_name": repo,
                "contributor_name": contributor_name or "all contributors",
                "date_range": date_filter.replace("+created:", "")
                if date_filter
                else "All time",
            },
            task_id,
        )

    except Exception as e:
        report_tasks[task_id]["status"] = "failed"
        report_tasks[task_id]["error"] = str(e)
        print(f"Error generating report: {str(e)}")


@router.post(
    "/github/repo/merged/{owner}/{repo}/async",
    summary="Асинхронно сгенерировать отчет о PR в репозитории и отправить на почту",
    tags=["GitHub"],
)
async def get_github_repo_async(
    request: Request,
    owner: str,
    repo: str,
    email_data: EmailRequest,
    background_tasks: BackgroundTasks,
    contributor_login_filter: Optional[str] = Query(""),
    contributor_email_filter: Optional[str] = Query(""),
    date_filter: Optional[str] = Query(""),
    github_service: services.GitHubService = Depends(services.GitHubService),
):
    github_service.set_authorization_header(request)

    # Generate a unique task ID
    task_id = str(uuid.uuid4())

    # Store initial task info
    report_tasks[task_id] = {
        "status": "processing",
        "owner": owner,
        "repo": repo,
        "email": email_data.email,
        "contributor_login": contributor_login_filter,
        "contributor_email": contributor_email_filter,
        "date_filter": date_filter,
    }

    # Schedule background task
    background_tasks.add_task(
        generate_github_report,
        task_id,
        owner,
        repo,
        contributor_login_filter,
        contributor_email_filter,
        date_filter,
        email_data.email,
        github_service,
    )

    return {"task_id": task_id, "status": "processing"}


@router.get(
    "/task/{task_id}",
    summary="Получить статус выполнения задачи",
    tags=["Tasks"],
)
async def get_task_status(task_id: str):
    if task_id not in report_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = report_tasks[task_id]

    response = {
        "task_id": task_id,
        "status": task_info["status"],
    }

    if task_info["status"] == "failed":
        response["error"] = task_info.get("error", "Unknown error")
    elif task_info["status"].startswith("completed"):
        response["result"] = task_info.get("result")

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
    deprecated=True,
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
