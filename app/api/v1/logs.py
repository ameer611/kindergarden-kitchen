import os
import glob
from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User as UserModel, UserRole
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=dict)
def get_all_logs(
        db: Session = Depends(deps.get_db),
        current_user: UserModel = Depends(deps.get_current_active_user),
        log_type: Optional[str] = Query(None, description="Filter by log type (application, error, access)"),
        limit: int = Query(100, description="Maximum number of log entries to return"),
        level: Optional[str] = Query(None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"),
        search: Optional[str] = Query(None, description="Search term to filter log entries")
) -> Any:
    """
    Retrieve all application logs.
    Requires Manager or Admin role for security reasons.
    """
    # Authorization: Only Manager or Admin can view logs
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view system logs."
        )

    try:
        # Define potential log file locations
        log_directories = [
            "./logs",
            "/var/log/kindergarten-kitchen",
            "/app/logs",
            "./app/logs"
        ]

        log_files = []

        # Search for log files in various locations
        for log_dir in log_directories:
            if os.path.exists(log_dir):
                # Common log file patterns
                patterns = [
                    f"{log_dir}/*.log",
                    f"{log_dir}/*.txt",
                    f"{log_dir}/application*.log",
                    f"{log_dir}/error*.log",
                    f"{log_dir}/access*.log"
                ]

                for pattern in patterns:
                    log_files.extend(glob.glob(pattern))

        # Also check for common log files in current directory
        current_dir_patterns = [
            "*.log",
            "app.log",
            "error.log",
            "access.log",
            "application.log"
        ]

        for pattern in current_dir_patterns:
            log_files.extend(glob.glob(pattern))

        # Remove duplicates and sort by modification time (newest first)
        log_files = list(set(log_files))
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        all_logs = []
        total_entries = 0

        for log_file in log_files:
            if total_entries >= limit:
                break

            try:
                # Filter by log type if specified
                if log_type:
                    file_name = os.path.basename(log_file).lower()
                    if log_type.lower() not in file_name:
                        continue

                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                # Process log lines (newest first)
                for line in reversed(lines[-1000:]):  # Limit to last 1000 lines per file
                    if total_entries >= limit:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # Filter by log level if specified
                    if level:
                        if level.upper() not in line.upper():
                            continue

                    # Filter by search term if specified
                    if search:
                        if search.lower() not in line.lower():
                            continue

                    # Parse log entry
                    log_entry = {
                        "timestamp": extract_timestamp(line),
                        "level": extract_log_level(line),
                        "source_file": os.path.basename(log_file),
                        "message": line,
                        "file_path": log_file
                    }

                    all_logs.append(log_entry)
                    total_entries += 1

            except Exception as e:
                # If we can't read a specific file, log the error but continue
                error_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "source_file": os.path.basename(log_file),
                    "message": f"Error reading log file: {str(e)}",
                    "file_path": log_file
                }
                all_logs.append(error_entry)
                total_entries += 1

        # Sort all logs by timestamp (newest first)
        all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return {
            "status": "success",
            "total_entries": len(all_logs),
            "log_files_found": len(log_files),
            "filters_applied": {
                "log_type": log_type,
                "level": level,
                "search": search,
                "limit": limit
            },
            "logs": all_logs[:limit]  # Ensure we don't exceed the limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving logs: {str(e)}"
        )


@router.get("/files", response_model=dict)
def get_log_files(
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get a list of available log files.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to view log files."
        )

    try:
        log_directories = [
            "./logs",
            "/var/log/kindergarten-kitchen",
            "/app/logs",
            "./app/logs"
        ]

        found_files = []

        for log_dir in log_directories:
            if os.path.exists(log_dir):
                patterns = [
                    f"{log_dir}/*.log",
                    f"{log_dir}/*.txt"
                ]

                for pattern in patterns:
                    files = glob.glob(pattern)
                    for file_path in files:
                        stat = os.stat(file_path)
                        found_files.append({
                            "file_path": file_path,
                            "file_name": os.path.basename(file_path),
                            "size_bytes": stat.st_size,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2),
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "directory": log_dir
                        })

        # Also check current directory
        current_patterns = ["*.log", "app.log", "error.log", "access.log"]
        for pattern in current_patterns:
            files = glob.glob(pattern)
            for file_path in files:
                if file_path not in [f["file_path"] for f in found_files]:
                    stat = os.stat(file_path)
                    found_files.append({
                        "file_path": file_path,
                        "file_name": os.path.basename(file_path),
                        "size_bytes": stat.st_size,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "directory": "."
                    })

        # Sort by last modified (newest first)
        found_files.sort(key=lambda x: x["last_modified"], reverse=True)

        return {
            "status": "success",
            "total_files": len(found_files),
            "files": found_files
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving log files: {str(e)}"
        )


@router.get("/download/{file_name}")
def download_log_file(
        file_name: str,
        current_user: UserModel = Depends(deps.get_current_active_user)
) -> Any:
    """
    Download a specific log file.
    Requires Manager or Admin role.
    """
    if not (current_user.role == UserRole.ADMIN or current_user.role == UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to download log files."
        )

    # Security: Only allow downloading .log and .txt files
    if not (file_name.endswith('.log') or file_name.endswith('.txt')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .log and .txt files can be downloaded."
        )

    # Search for the file in known log directories
    search_paths = [
        f"./logs/{file_name}",
        f"/var/log/kindergarten-kitchen/{file_name}",
        f"/app/logs/{file_name}",
        f"./app/logs/{file_name}",
        f"./{file_name}"
    ]

    file_path = None
    for path in search_paths:
        if os.path.exists(path):
            file_path = path
            break

    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log file '{file_name}' not found."
        )

    try:
        return FileResponse(
            file_path,
            media_type="text/plain",
            filename=file_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )


def extract_timestamp(log_line: str) -> str:
    """Extract timestamp from log line if present, otherwise return current time."""
    try:
        # Common timestamp patterns
        import re

        # ISO format: 2025-06-02T05:33:47
        iso_pattern = r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
        match = re.search(iso_pattern, log_line)
        if match:
            return match.group(0)

        # Other common formats
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # 2025-06-02 05:33:47
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',  # 06/02/2025 05:33:47
            r'\w{3} \d{2} \d{2}:\d{2}:\d{2}',  # Jun 02 05:33:47
        ]

        for pattern in timestamp_patterns:
            match = re.search(pattern, log_line)
            if match:
                return match.group(0)

        return datetime.now().isoformat()
    except:
        return datetime.now().isoformat()


def extract_log_level(log_line: str) -> str:
    """Extract log level from log line."""
    levels = ["CRITICAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG"]
    line_upper = log_line.upper()

    for level in levels:
        if level in line_upper:
            return level

    return "INFO"  # Default level