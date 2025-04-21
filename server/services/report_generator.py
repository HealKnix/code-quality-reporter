from typing import Dict

import schemas
from utils.file_utils import create_report_file

from services.github_service import GitHubService
from services.email_service import send_email_report


async def generate_github_report(
    task_id: str,
    owner: str,
    repo: str,
    contributor_login_filter: str,
    contributor_email_filter: str,
    date_filter: str,
    user_email: str,
    github_service: GitHubService,
    report_tasks: Dict[str, Dict],
):
    # Импортируем блокировку для безопасного доступа к словарю report_tasks
    from api.routes import report_tasks_lock

    """Background task to generate GitHub report for a specific contributor"""
    try:
        # Original get_github_repo code
        # Формирование фильтра по датам
        if date_filter != "":
            date_filter = f"+created:{date_filter}"

        # Update task status to indicate which contributor is being processed
        with report_tasks_lock:
            if task_id in report_tasks:
                print(contributor_login_filter)
                report_tasks[task_id]["processing_contributor"] = (
                    contributor_login_filter
                )

        contributor_details = await github_service.get_repo_contributors(owner, repo)

        # Получение информации о репозитории
        repo_info = await github_service.get_repo_info(owner, repo)

        # Построение запроса
        contributor_login = contributor_login_filter
        contributor_details = {c["login"]: c for c in contributor_details}

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
            with report_tasks_lock:
                report_tasks[task_id]["result"] = result.dict()
                report_tasks[task_id]["status"] = "completed"

            if user_email != "":
                await send_email_report(
                    user_email,
                    {
                        "repo_owner": owner,
                        "repo_name": repo,
                        "contributor_name": result.contributor_name
                        or "all contributors",
                        "date_range": date_filter.replace("+created:", "")
                        if date_filter
                        else "All time",
                    },
                    task_id,
                    report_tasks,
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
                    contributor_login = str(item["user"]["login"])
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
                    files_extension = ""

                    if repo_info.get("language") == "Python":
                        files_extension = ".py"
                    elif repo_info.get("language") == "Java":
                        files_extension = ".java"

                    if files_extension in file.get("filename", ""):
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

        contributor_id = (
            contributor_details.get(contributor_login_filter, {}).get("id")
            if contributor_details.get(contributor_login_filter, {}).get("id")
            else None
        )

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
            contributor_id=contributor_id,
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
                result,
                contributor_details,
                contributor_login_filter,
                start_date=date_filter_cleaned.split("..")[0]
                if ".." in date_filter_cleaned
                else None,
                end_date=date_filter_cleaned.split("..")[1]
                if ".." in date_filter_cleaned
                else None,
            )

            # Store the report file path in the global dictionary
            from utils.file_utils import report_files

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
        with report_tasks_lock:
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
                    if len(report_tasks[task_id]["pending_contributors"]) == 0:
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

        if user_email != "":
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
                report_tasks,
                owner=owner,
                repo=repo,
                contributor_login=contributor_login_filter,
            )

    except Exception as e:
        # Mark this specific contributor as failed
        with report_tasks_lock:
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
