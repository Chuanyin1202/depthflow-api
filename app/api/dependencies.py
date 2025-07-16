from fastapi import HTTPException, Header
from typing import Optional
import os

from app.config import settings


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Optional[str]:
    """驗證 API Key"""
    if not settings.api_key_enabled:
        return None
    
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "missing_api_key",
                "message": "缺少 API Key"
            }
        )
    
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_api_key",
                "message": "無效的 API Key"
            }
        )
    
    return x_api_key


def validate_file_extension(filename: Optional[str]) -> bool:
    """驗證檔案副檔名"""
    if not filename:
        return False
    
    extension = os.path.splitext(filename)[1].lower().lstrip('.')
    return extension in settings.allowed_extensions


def validate_file_size(file_size: int) -> bool:
    """驗證檔案大小"""
    return file_size <= settings.max_upload_size