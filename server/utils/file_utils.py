from datetime import datetime
from pathlib import Path

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


# Function to get the path to a report file
def get_report_file_path(owner: str, repo: str, filename: str) -> str:
    """Get the path to a report file"""
    return f"./reports/{owner}/{repo}/{filename}"
