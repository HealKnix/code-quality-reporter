import asyncio
import os
import uuid
import shutil
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Create reports directory if it doesn't exist
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

# Store report file paths for each generated report
report_files = {}


# Function to sanitize filename to be compatible with Windows file system
def sanitize_filename(filename):
    # Windows doesn't allow these characters in filenames: \ / : * ? " < > |
    invalid_chars = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    return filename


# Function to sanitize date string for filename
def sanitize_date_for_filename(date_str):
    if not date_str:
        return ""
    # Replace colons, periods and other invalid characters with underscores
    return sanitize_filename(date_str)


# Function to generate a report file and return its path
async def create_report_file(
    owner: str,
    repo: str,
    contributor_login: str,
    start_date: str = None,
    end_date: str = None,
):
    # Create folder structure for reports if it doesn't exist
    repo_dir = REPORTS_DIR / owner / repo
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize dates for filename
    safe_start_date = sanitize_date_for_filename(start_date)
    safe_end_date = sanitize_date_for_filename(end_date)

    # Generate a filename with date range if provided
    date_part = ""
    if safe_start_date and safe_end_date:
        date_part = f"_{safe_start_date}_to_{safe_end_date}"
    elif safe_start_date:
        date_part = f"_from_{safe_start_date}"
    elif safe_end_date:
        date_part = f"_to_{safe_end_date}"

    # Create a timestamped filename to avoid overwriting
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{contributor_login}{date_part}_{timestamp}.pdf"
    file_path = repo_dir / filename

    # Generate a simple PDF report (in a real app, you'd use a PDF library)
    # For now, we'll create a dummy PDF file
    with open(file_path, "w") as f:
        f.write(f"Report for {contributor_login} in {owner}/{repo}\n")
        f.write(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if start_date or end_date:
            f.write(f"Date range: {start_date or 'beginning'} to {end_date or 'now'}\n")

    # Return the file path
    return file_path, filename


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


async def send_email_report(
    email: str,
    report_data: dict,
    task_id: str,
    owner: str = None,
    repo: str = None,
    contributor_login: str = None,
):
    """Send email with report"""
    try:
        sender_email = os.getenv("EMAIL_SENDER")
        password = os.getenv("SMTP_PASSWORD")
        smtp_server = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT"))

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
        download_link = ""
        if owner and repo and contributor_login:
            base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")
            download_url = f"{base_url}/api/download-report/{owner}/{repo}/{report_data['filename']}"
            download_link = f"""
            <p><a href="{download_url}" style="display: inline-block; background-color: #4CAF50; color: white; padding: 10px 20px; 
               text-align: center; text-decoration: none; border-radius: 4px; font-weight: bold;">Download Report</a></p>
            """

        html = f"""
        <html>
            <body>
                <h2>GitHub Code Quality Report</h2>
                <p>Your report for repository {report_data["repo_owner"]}/{report_data["repo_name"]} is ready.</p>
                <p>Report generated for {report_data["contributor_name"]} in the date range: {report_data.get("date_range", "All time")}</p>
                {download_link}
                <p>You can also view the details by returning to the application.</p>
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
    """Background task to generate GitHub report for a specific contributor"""
    try:
        # Original get_github_repo code
        # Формирование фильтра по датам
        if date_filter != "":
            date_filter = f"+created:{date_filter}"

        # Ensure contributor login is lowercase for case-insensitive comparisons
        if contributor_login_filter != "":
            contributor_login_filter = contributor_login_filter.lower()
        if contributor_email_filter != "":
            contributor_email_filter = contributor_email_filter.lower()

        # Update task status to indicate which contributor is being processed
        if task_id in report_tasks:
            if "processing_contributor" not in report_tasks[task_id]:
                report_tasks[task_id]["processing_contributor"] = (
                    contributor_login_filter
                )

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

        # Формирование результата для текущего контрибьютера
        result = schemas.GitHubRepo(
            **merged_prs,
            language=repo_info.get("language"),
            topics=topics,
            contributor_name=contributor_name,
            contributor_email=contributor_email,
            contributor_login=contributor_login_filter,  # Add login to help identify this report
        )

        # Generate the report file
        try:
            date_filter_cleaned = (
                date_filter.replace("+created:", "") if date_filter else ""
            )
            file_path, filename = await create_report_file(
                owner,
                repo,
                contributor_login_filter,
                start_date=date_filter_cleaned.split("..")[0]
                if ".." in date_filter_cleaned
                else None,
                end_date=date_filter_cleaned.split("..")[1]
                if ".." in date_filter_cleaned
                else None,
            )

            # Store the report file path in the global dictionary
            key = f"{owner}/{repo}/{contributor_login_filter}"
            report_files[key] = str(file_path)

            # Add the report file path to the result
            result_dict = result.dict()
            result_dict["report_file"] = str(file_path)
            result_dict["report_filename"] = filename

            # Use the updated result dictionary
            result = schemas.GitHubRepo(**result_dict)
        except Exception as e:
            print(f"Error generating report file: {str(e)}")

        # Store the result in the task's results dictionary
        if task_id in report_tasks:
            # Update task status for multiple contributors
            if (
                "pending_contributors" in report_tasks[task_id]
                and contributor_login_filter
                in report_tasks[task_id]["pending_contributors"]
            ):
                # Remove from pending list
                report_tasks[task_id]["pending_contributors"].remove(
                    contributor_login_filter
                )
                # Add to completed list
                if "completed_contributors" in report_tasks[task_id]:
                    report_tasks[task_id]["completed_contributors"].append(
                        contributor_login_filter
                    )

                # Store this contributor's report in the results dictionary
                if "results" in report_tasks[task_id]:
                    report_tasks[task_id]["results"][contributor_login_filter] = (
                        result.dict()
                    )

                # Update overall status
                if not report_tasks[task_id]["pending_contributors"]:
                    # All contributors processed
                    report_tasks[task_id]["status"] = "completed"
                    print(f"All reports for task {task_id} generated successfully")
                else:
                    # More contributors to process
                    report_tasks[task_id]["status"] = "partial"
                    print(
                        f"Report for {contributor_name} ({contributor_login_filter}) generated successfully. {len(report_tasks[task_id]['pending_contributors'])} contributors remaining."
                    )
            else:
                # Single contributor workflow or fallback
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
                "contributor_login": contributor_login_filter,  # Add login to identify this report
                "filename": filename,
                "date_range": date_filter.replace("+created:", "")
                if date_filter
                else "All time",
            },
            task_id,
            owner=owner,
            repo=repo,
            contributor_login=contributor_login_filter,
        )

    except Exception as e:
        # Mark this specific contributor as failed
        if (
            task_id in report_tasks
            and "pending_contributors" in report_tasks[task_id]
            and contributor_login_filter
            in report_tasks[task_id]["pending_contributors"]
        ):
            report_tasks[task_id]["pending_contributors"].remove(
                contributor_login_filter
            )
            if "failed_contributors" not in report_tasks[task_id]:
                report_tasks[task_id]["failed_contributors"] = []
            report_tasks[task_id]["failed_contributors"].append(
                contributor_login_filter
            )

            # If all contributors have been processed (either succeeded or failed)
            if not report_tasks[task_id]["pending_contributors"]:
                if not report_tasks[task_id].get("completed_contributors"):
                    # All contributors failed
                    report_tasks[task_id]["status"] = "failed"
                else:
                    # Some succeeded, some failed
                    report_tasks[task_id]["status"] = "partial"
        else:
            # Fallback for single-contributor workflow or other errors
            report_tasks[task_id]["status"] = "failed"

        report_tasks[task_id]["error"] = str(e)
        print(f"Error generating report for {contributor_login_filter}: {str(e)}")


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
    github_service: services.GitHubService = Depends(services.GitHubService),
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

    # Store initial task info
    report_tasks[task_id] = {
        "status": "processing",
        "owner": owner,
        "repo": repo,
        "email": email_data.email,
        "contributors": contributor_logins,
        "contributor_email": contributor_email_filter,
        "date_filter": date_filter,
        "pending_contributors": contributor_logins.copy() if contributor_logins else [],
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
            )
    else:
        # Fallback to old behavior if no contributors specified
        background_tasks.add_task(
            generate_github_report,
            task_id,
            owner,
            repo,
            "",
            contributor_email_filter,
            date_filter,
            email_data.email,
            github_service,
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
    if task_id not in report_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task_info = report_tasks[task_id]
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
        # Also return the first result in the standard location for backward compatibility
        if task_info["results"] and len(task_info["results"]) > 0:
            first_contributor = list(task_info["results"].keys())[0]
            response["result"] = task_info["results"][first_contributor]
            response["contributor_login"] = first_contributor
    # For single contributor reports (legacy support)
    elif task_info["status"] == "completed" and "result" in task_info:
        response["result"] = task_info["result"]
        if "contributor_login" in task_info:
            response["contributor_login"] = task_info["contributor_login"]

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


# Routes for file downloads
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
    file_path = f"./reports/{owner}/{repo}/{filename}"  # Путь к файлу
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, filename=filename, media_type="application/octet-stream"
        )
    return {"error": "Файл не найден"}


# Add static files handling for reports directory
app.mount("/reports", StaticFiles(directory="reports"), name="reports")
app.include_router(router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
