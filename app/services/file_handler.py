import os
import aiofiles
from fastapi import UploadFile
import logging
from typing import Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class FileHandler:
    """檔案處理服務"""
    
    def __init__(self):
        self.upload_path = settings.upload_path
        self.output_path = settings.output_path
        
    async def save_upload(self, file: UploadFile, task_id: str) -> str:
        """
        儲存上傳的檔案
        
        Args:
            file: 上傳的檔案物件
            task_id: 任務 ID
            
        Returns:
            str: 儲存的檔案路徑
        """
        # 取得檔案副檔名
        extension = os.path.splitext(file.filename)[1].lower()
        
        # 生成檔案名稱
        filename = f"{task_id}_original{extension}"
        filepath = os.path.join(self.upload_path, filename)
        
        # 確保目錄存在
        os.makedirs(self.upload_path, exist_ok=True)
        
        try:
            # 非同步寫入檔案
            async with aiofiles.open(filepath, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            logger.info(f"檔案已儲存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"儲存檔案失敗: {e}")
            # 如果寫入失敗，嘗試刪除部分寫入的檔案
            if os.path.exists(filepath):
                os.remove(filepath)
            raise
    
    def get_output_path(self, task_id: str, format: str) -> str:
        """
        取得輸出檔案路徑
        
        Args:
            task_id: 任務 ID
            format: 輸出格式 (mp4, webm, gif)
            
        Returns:
            str: 輸出檔案路徑
        """
        filename = f"{task_id}_output.{format}"
        return os.path.join(self.output_path, filename)
    
    def cleanup_task_files(self, task_id: str):
        """
        清理任務相關的檔案
        
        Args:
            task_id: 任務 ID
        """
        # 清理上傳的檔案
        for filename in os.listdir(self.upload_path):
            if filename.startswith(task_id):
                filepath = os.path.join(self.upload_path, filename)
                try:
                    os.remove(filepath)
                    logger.info(f"已刪除檔案: {filepath}")
                except Exception as e:
                    logger.error(f"刪除檔案失敗: {filepath}, 錯誤: {e}")
        
        # 清理輸出檔案
        for filename in os.listdir(self.output_path):
            if filename.startswith(task_id):
                filepath = os.path.join(self.output_path, filename)
                try:
                    os.remove(filepath)
                    logger.info(f"已刪除檔案: {filepath}")
                except Exception as e:
                    logger.error(f"刪除檔案失敗: {filepath}, 錯誤: {e}")
    
    def get_file_info(self, filepath: str) -> dict:
        """
        取得檔案資訊
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            dict: 檔案資訊
        """
        if not os.path.exists(filepath):
            return None
        
        stat = os.stat(filepath)
        return {
            "path": filepath,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime)
        }
    
    async def validate_image(self, filepath: str) -> bool:
        """
        驗證圖片檔案
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            bool: 是否為有效的圖片
        """
        try:
            from PIL import Image
            
            # 嘗試開啟圖片
            with Image.open(filepath) as img:
                # 檢查圖片格式
                if img.format.lower() not in ['jpeg', 'jpg', 'png']:
                    return False
                
                # 檢查圖片尺寸
                width, height = img.size
                if width < 100 or height < 100:
                    logger.warning(f"圖片尺寸過小: {width}x{height}")
                    return False
                
                if width > 8192 or height > 8192:
                    logger.warning(f"圖片尺寸過大: {width}x{height}")
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"驗證圖片失敗: {e}")
            return False
    
    def ensure_directories(self):
        """確保必要的目錄存在"""
        os.makedirs(self.upload_path, exist_ok=True)
        os.makedirs(self.output_path, exist_ok=True)
        logger.info(f"已確保目錄存在: {self.upload_path}, {self.output_path}")