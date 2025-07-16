from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from fastapi.responses import FileResponse
from typing import List, Optional
import uuid
import os
import logging
import json
from datetime import datetime

from app.config import settings
from app.models.schemas import (
    ProcessRequest, TaskResponse, TaskDetail, 
    SystemStatus, PresetConfig, ErrorResponse
)
from app.api.dependencies import verify_api_key, validate_file_extension
from app.services.file_handler import FileHandler
from app.tasks.processing import process_image_task

logger = logging.getLogger(__name__)
router = APIRouter()

# 暫時的任務儲存（實際應使用資料庫）
tasks_db = {}


@router.post("/process", response_model=TaskResponse)
async def process_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: Optional[str] = Form(default="{}"),
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    上傳圖片並開始處理
    
    - **file**: 要處理的圖片檔案 (JPEG/PNG)
    - **request**: 處理參數的 JSON 字符串（可選）
    """
    # 解析 JSON 參數
    try:
        request_data = json.loads(request) if request else {}
        process_request = ProcessRequest(**request_data)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="invalid_json",
                message="請求參數必須是有效的 JSON 格式",
                detail={"received": request}
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="parameter_validation_error",
                message="請求參數驗證失敗",
                detail={"error": str(e)}
            ).model_dump()
        )
    
    # 驗證檔案
    if not validate_file_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="invalid_file_format",
                message=f"不支援的檔案格式。支援的格式: {', '.join(settings.allowed_extensions)}",
                detail={"filename": file.filename}
            ).model_dump()
        )
    
    # 檢查檔案大小
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)  # 重置檔案指標
    
    if file_size > settings.max_upload_size:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="file_too_large",
                message=f"檔案大小超過限制 ({settings.max_upload_size / 1024 / 1024:.1f} MB)",
                detail={"file_size": file_size}
            ).model_dump()
        )
    
    # 生成任務 ID
    task_id = str(uuid.uuid4())
    
    # 儲存檔案
    file_handler = FileHandler()
    try:
        file_path = await file_handler.save_upload(file, task_id)
    except Exception as e:
        logger.error(f"儲存檔案失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="file_save_error",
                message="儲存檔案失敗",
                detail={"error": str(e)}
            ).model_dump()
        )
    
    # 建立任務記錄
    task = {
        "task_id": task_id,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "progress": 0,
        "message": "任務已建立，等待處理",
        "parameters": process_request.parameters,
        "file_path": file_path,
        "webhook_url": process_request.webhook_url
    }
    tasks_db[task_id] = task
    
    # 加入背景任務（暫時使用 FastAPI 的 BackgroundTasks，之後改用 Celery）
    background_tasks.add_task(
        process_image_task,
        task_id=task_id,
        file_path=file_path,
        parameters=process_request.parameters.model_dump(),
        tasks_db=tasks_db
    )
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        created_at=task["created_at"],
        updated_at=task["updated_at"]
    )


@router.get("/task/{task_id}", response_model=TaskDetail)
async def get_task_status(
    task_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """查詢任務狀態"""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="task_not_found",
                message="找不到指定的任務",
                detail={"task_id": task_id}
            ).model_dump()
        )
    
    return TaskDetail(
        task_id=task["task_id"],
        status=task["status"],
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        progress=task.get("progress", 0),
        message=task.get("message"),
        result_url=f"{settings.api_prefix}/result/{task_id}" if task.get("result_path") else None,
        error_message=task.get("error_message"),
        parameters=task.get("parameters"),
        metadata=task.get("metadata")
    )


@router.get("/result/{task_id}")
async def download_result(
    task_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """下載處理結果"""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="task_not_found",
                message="找不到指定的任務",
                detail={"task_id": task_id}
            ).model_dump()
        )
    
    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="task_not_completed",
                message="任務尚未完成",
                detail={"status": task["status"]}
            ).model_dump()
        )
    
    result_path = task.get("result_path")
    if not result_path or not os.path.exists(result_path):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="result_not_found",
                message="找不到處理結果檔案",
                detail={"task_id": task_id}
            ).model_dump()
        )
    
    # 根據輸出格式設定 MIME 類型
    output_format = task.get("parameters", {}).get("output_format", "mp4")
    media_type = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "gif": "image/gif"
    }.get(output_format, "application/octet-stream")
    
    return FileResponse(
        path=result_path,
        media_type=media_type,
        filename=f"depthflow_{task_id}.{output_format}"
    )


@router.get("/status", response_model=SystemStatus)
async def get_system_status(
    api_key: Optional[str] = Depends(verify_api_key)
):
    """取得系統狀態"""
    import psutil
    
    # 取得系統資訊
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    # 計算任務統計
    active_tasks = sum(1 for task in tasks_db.values() if task["status"] == "processing")
    queue_length = sum(1 for task in tasks_db.values() if task["status"] == "pending")
    
    # GPU 狀態（簡化版本，實際應該使用 nvidia-ml-py 或類似工具）
    gpu_available = False
    gpu_memory_used = None
    
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_memory_used = (torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated()) * 100
    except ImportError:
        pass
    
    return SystemStatus(
        gpu_available=gpu_available,
        gpu_memory_used=gpu_memory_used,
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        queue_length=queue_length,
        active_tasks=active_tasks
    )


@router.get("/presets", response_model=List[PresetConfig])
async def get_presets(
    api_key: Optional[str] = Depends(verify_api_key)
):
    """取得預設配置列表"""
    # 預設配置（實際應從資料庫或配置檔案讀取）
    presets = [
        PresetConfig(
            name="快速預覽",
            description="快速生成低解析度預覽",
            parameters={
                "depth_strength": 1.0,
                "animation_duration": 2.0,
                "fps": 24,
                "output_format": "mp4",
                "resolution": 720
            },
            is_default=True
        ),
        PresetConfig(
            name="高品質",
            description="適合社群媒體分享的高品質設定",
            parameters={
                "depth_strength": 2.0,
                "animation_duration": 5.0,
                "fps": 60,
                "output_format": "mp4",
                "resolution": 1920
            },
            is_default=False
        ),
        PresetConfig(
            name="GIF 動圖",
            description="生成 GIF 格式的動圖",
            parameters={
                "depth_strength": 1.5,
                "animation_duration": 3.0,
                "fps": 15,
                "output_format": "gif",
                "resolution": 480
            },
            is_default=False
        )
    ]
    
    return presets


@router.delete("/task/{task_id}")
async def cancel_task(
    task_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """取消任務"""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="task_not_found",
                message="找不到指定的任務",
                detail={"task_id": task_id}
            ).model_dump()
        )
    
    if task["status"] in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="task_not_cancellable",
                message="任務已經結束，無法取消",
                detail={"status": task["status"]}
            ).model_dump()
        )
    
    # 更新任務狀態
    task["status"] = "cancelled"
    task["updated_at"] = datetime.utcnow()
    task["message"] = "任務已取消"
    
    return {"message": "任務已成功取消", "task_id": task_id}