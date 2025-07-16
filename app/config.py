from pydantic_settings import BaseSettings
from typing import List
import os
from functools import lru_cache


class Settings(BaseSettings):
    # 應用程式設定
    app_name: str = "DepthFlow API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_prefix: str = "/api/v1"
    
    # 檔案上傳設定
    max_upload_size: int = 10485760  # 10MB
    allowed_extensions: List[str] = ["jpg", "jpeg", "png"]
    
    # 儲存路徑
    upload_path: str = "./storage/uploads"
    output_path: str = "./storage/outputs"
    
    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Celery 配置
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # DepthFlow 設定
    depthflow_max_resolution: int = 2048
    depthflow_default_fps: int = 30
    depthflow_default_duration: int = 3  # 秒
    
    # 安全設定
    api_key_enabled: bool = False
    api_key: str = "your-secret-api-key"
    
    # CORS
    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    def get_redis_url(self) -> str:
        """取得 Redis 連接 URL"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    def ensure_directories(self):
        """確保必要的目錄存在"""
        os.makedirs(self.upload_path, exist_ok=True)
        os.makedirs(self.output_path, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """取得設定單例"""
    return Settings()


# 初始化設定
settings = get_settings()
settings.ensure_directories()