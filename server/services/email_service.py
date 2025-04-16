import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


async def send_email_report(
    email: str,
    report_data: dict,
    task_id: str,
    report_tasks: dict,
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

            if len(report_tasks[task_id]["pending_contributors"]) == 0:
                report_tasks[task_id]["status"] = "completed"
                report_tasks[task_id]["processing_contributor"] = ""
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
