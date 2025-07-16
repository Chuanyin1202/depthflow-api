from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class TaskStatus(str, Enum):
    """任務狀態列舉"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingParams(BaseModel):
    """處理參數模型"""
    depth_strength: float = Field(default=1.0, ge=0.1, le=5.0, description="深度強度")
    animation_duration: float = Field(default=3.0, ge=1.0, le=10.0, description="動畫時長（秒）")
    fps: int = Field(default=30, ge=15, le=60, description="影格率")
    output_format: str = Field(default="mp4", pattern="^(mp4|webm|gif)$", description="輸出格式")
    resolution: Optional[int] = Field(default=None, ge=480, le=2048, description="最大解析度")
    loop: bool = Field(default=True, description="是否循環播放")
    
    # 進階參數
    depth_model: Optional[str] = Field(default="default", description="深度估計模型")
    camera_movement: Optional[str] = Field(
        default="orbit", 
        pattern="^(orbit|zoom|dolly|static)$",
        description="相機運動模式"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "depth_strength": 1.5,
                "animation_duration": 3.0,
                "fps": 30,
                "output_format": "mp4",
                "resolution": 1920,
                "loop": True
            }
        }


class ProcessRequest(BaseModel):
    """處理請求模型"""
    parameters: Optional[ProcessingParams] = Field(default_factory=ProcessingParams)
    webhook_url: Optional[str] = Field(default=None, description="完成時的回調 URL")
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Webhook URL 必須是有效的 HTTP(S) URL')
        return v


class TaskResponse(BaseModel):
    """任務回應模型"""
    task_id: str = Field(..., description="任務 ID")
    status: TaskStatus = Field(..., description="任務狀態")
    created_at: datetime = Field(..., description="建立時間")
    updated_at: datetime = Field(..., description="更新時間")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "created_at": "2024-01-16T10:30:00Z",
                "updated_at": "2024-01-16T10:30:00Z"
            }
        }


class TaskDetail(TaskResponse):
    """任務詳細資訊模型"""
    progress: int = Field(default=0, ge=0, le=100, description="處理進度百分比")
    message: Optional[str] = Field(default=None, description="狀態訊息")
    result_url: Optional[str] = Field(default=None, description="結果檔案 URL")
    error_message: Optional[str] = Field(default=None, description="錯誤訊息")
    parameters: Optional[ProcessingParams] = Field(default=None, description="處理參數")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="額外中繼資料")
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "created_at": "2024-01-16T10:30:00Z",
                "updated_at": "2024-01-16T10:35:00Z",
                "progress": 100,
                "message": "處理完成",
                "result_url": "/api/v1/result/550e8400-e29b-41d4-a716-446655440000",
                "parameters": {
                    "depth_strength": 1.5,
                    "animation_duration": 3.0,
                    "fps": 30,
                    "output_format": "mp4"
                }
            }
        }


class HealthResponse(BaseModel):
    """健康檢查回應模型"""
    status: str = Field(default="healthy", description="服務狀態")
    version: str = Field(..., description="API 版本")
    timestamp: datetime = Field(..., description="時間戳記")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-16T10:30:00Z"
            }
        }


class SystemStatus(BaseModel):
    """系統狀態模型"""
    gpu_available: bool = Field(..., description="GPU 是否可用")
    gpu_memory_used: Optional[float] = Field(default=None, description="GPU 記憶體使用率")
    gpu_temperature: Optional[float] = Field(default=None, description="GPU 溫度")
    gpu_utilization: Optional[float] = Field(default=None, description="GPU 利用率")
    cpu_percent: float = Field(..., description="CPU 使用率")
    memory_percent: float = Field(..., description="記憶體使用率")
    queue_length: int = Field(..., description="任務隊列長度")
    active_tasks: int = Field(..., description="進行中的任務數")
    max_concurrent_tasks: Optional[int] = Field(default=None, description="最大併發任務數")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gpu_available": True,
                "gpu_memory_used": 45.2,
                "gpu_temperature": 65.0,
                "gpu_utilization": 78.5,
                "cpu_percent": 23.5,
                "memory_percent": 67.8,
                "queue_length": 5,
                "active_tasks": 2,
                "max_concurrent_tasks": 3
            }
        }


class ErrorResponse(BaseModel):
    """錯誤回應模型"""
    error: str = Field(..., description="錯誤類型")
    message: str = Field(..., description="錯誤訊息")
    detail: Optional[Dict[str, Any]] = Field(default=None, description="詳細資訊")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "檔案格式不支援",
                "detail": {
                    "allowed_formats": ["jpg", "jpeg", "png"],
                    "received_format": "bmp"
                }
            }
        }


class PresetConfig(BaseModel):
    """預設配置模型"""
    name: str = Field(..., description="預設名稱")
    description: Optional[str] = Field(default=None, description="預設描述")
    parameters: ProcessingParams = Field(..., description="處理參數")
    is_default: bool = Field(default=False, description="是否為預設值")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "高品質動畫",
                "description": "適合社群媒體分享的高品質設定",
                "parameters": {
                    "depth_strength": 2.0,
                    "animation_duration": 5.0,
                    "fps": 60,
                    "output_format": "mp4",
                    "resolution": 1920
                },
                "is_default": False
            }
        }