"""File serving endpoints for downloading case PDFs."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pathlib import Path
import logging
from urllib.parse import unquote

logger = logging.getLogger(__name__)
router = APIRouter()

# Base directory for case files
CASE_FILES_BASE = Path(__file__).parent.parent.parent.parent / "tool" / "data" / "case_files"
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def validate_file_path(file_path: str) -> Path:
    """
    Validate that the requested file path is safe and within the allowed directory.
    
    Args:
        file_path: The requested file path (may be URL-encoded)
        
    Returns:
        Path: The validated absolute file path
        
    Raises:
        HTTPException: If the path is invalid or outside the allowed directory
    """
    # Decode URL-encoded characters
    decoded_path = unquote(file_path)
    
    # Remove leading/trailing whitespace
    decoded_path = decoded_path.strip()
    
    # Convert to Path object
    requested_path = Path(decoded_path)
    
    # Resolve to absolute path to catch directory traversal attempts
    try:
        if requested_path.is_absolute():
            absolute_requested = requested_path.resolve()
        else:
            # Paths from the retriever are repo-relative, e.g. tool/data/case_files/A Raja.pdf
            absolute_requested = (PROJECT_ROOT / requested_path).resolve()
        absolute_base = CASE_FILES_BASE.resolve()
        
        # Verify the file is within the allowed directory
        try:
            absolute_requested.relative_to(absolute_base)
        except ValueError:
            logger.warning(f"Directory traversal attempt detected: {decoded_path}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: File must be in case_files directory"
            )
        
        # Verify the file exists
        if not absolute_requested.exists():
            logger.warning(f"File not found: {absolute_requested}")
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {decoded_path}"
            )
        
        # Verify it's a file, not a directory
        if not absolute_requested.is_file():
            logger.warning(f"Path is not a file: {absolute_requested}")
            raise HTTPException(
                status_code=400,
                detail="Requested path is not a file"
            )
        
        return absolute_requested
        
    except ValueError:
        logger.warning(f"Invalid path provided: {decoded_path}")
        raise HTTPException(
            status_code=400,
            detail="Invalid file path"
        )


@router.get("/files/download")
async def download_file(file_path: str = Query(..., description="Path to the file to download (e.g., tool/data/case_files/A Raja.pdf)")):
    """
    Download a case PDF file.
    
    Args:
        file_path: The relative file path to download (URL-encoded)
        
    Returns:
        FileResponse: The file as a downloadable attachment
        
    Raises:
        HTTPException: If the file path is invalid or file doesn't exist
    """
    try:
        # Validate and get the absolute path
        absolute_path = validate_file_path(file_path)
        
        # Extract filename for download
        filename = absolute_path.name
        
        logger.info(f"Serving file download: {filename}")
        
        # Return the file as an attachment
        return FileResponse(
            path=absolute_path,
            media_type="application/pdf",
            filename=filename,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error serving file"
        )
