import logging
from typing import Dict, Any
from datetime import datetime
import asyncio

from app.services.depthflow import DepthFlowService
from app.services.file_handler import FileHandler
from app.services.gpu_resource_manager import get_gpu_manager
from app.services.monitoring import get_monitoring_service, performance_monitor

logger = logging.getLogger(__name__)


def should_retry_error(error: Exception) -> bool:
    """
    判斷錯誤是否應該重試
    
    Args:
        error: 發生的錯誤
        
    Returns:
        bool: 是否應該重試
    """
    error_str = str(error).lower()
    
    # 不應該重試的錯誤類型
    non_retryable_errors = [
        "無效的圖片檔案",
        "檔案格式不支援",
        "檔案損壞",
        "parameter_validation_error",
        "invalid_file_format",
        "file_too_large"
    ]
    
    # 檢查是否為不可重試的錯誤
    for non_retryable in non_retryable_errors:
        if non_retryable in error_str:
            return False
    
    # 應該重試的錯誤類型
    retryable_errors = [
        "gpu",
        "memory",
        "timeout",
        "connection",
        "temporary",
        "資源不足",
        "服務器忙碌",
        "processing failed"
    ]
    
    # 檢查是否為可重試的錯誤
    for retryable in retryable_errors:
        if retryable in error_str:
            return True
    
    # 預設情況下，大多數錯誤都可以重試
    return True


@performance_monitor("image_processing")
async def process_image_task(
    task_id: str,
    file_path: str,
    parameters: Dict[str, Any],
    tasks_db: Dict[str, Any]
):
    """
    處理圖片的非同步任務
    
    Args:
        task_id: 任務 ID
        file_path: 輸入檔案路徑
        parameters: 處理參數
        tasks_db: 任務資料庫（暫時）
    """
    logger.info(f"開始處理任務: {task_id}")
    
    # 更新任務狀態
    task = tasks_db.get(task_id)
    if not task:
        logger.error(f"找不到任務: {task_id}")
        return
    
    # 初始化服務
    depthflow_service = DepthFlowService()
    file_handler = FileHandler()
    gpu_manager = await get_gpu_manager()
    monitoring_service = get_monitoring_service()
    
    # 記錄任務開始
    task_start_time = datetime.utcnow()
    monitoring_service.record_metric("task_started_count", 1, {"task_id": task_id})
    
    try:
        # 更新為處理中
        task['status'] = 'processing'
        task['updated_at'] = datetime.utcnow()
        task['message'] = '正在處理圖片...'
        
        # 驗證圖片
        is_valid = await file_handler.validate_image(file_path)
        if not is_valid:
            raise Exception("無效的圖片檔案")
        
        # 進度回調函數
        async def update_progress(progress: int, message: str):
            task['progress'] = progress
            task['message'] = message
            task['updated_at'] = datetime.utcnow()
            logger.info(f"任務 {task_id} 進度: {progress}% - {message}")
        
        # 取得輸出路徑
        output_format = parameters.get('output_format', 'mp4')
        output_path = file_handler.get_output_path(task_id, output_format)
        
        # 檢查 GPU 資源並取得處理槽位
        task['message'] = '等待 GPU 資源...'
        await update_progress(10, '等待 GPU 資源...')
        
        # 使用 GPU 資源管理器取得槽位
        async with gpu_manager.acquire_gpu_slot(task_id):
            task['message'] = '開始 GPU 處理...'
            await update_progress(20, '開始 GPU 處理...')
            
            # 處理圖片
            success = await depthflow_service.process_image(
                input_path=file_path,
                output_path=output_path,
                parameters=parameters,
                progress_callback=update_progress
            )
        
        if success:
            # 更新為完成
            task['status'] = 'completed'
            task['progress'] = 100
            task['message'] = '處理完成'
            task['result_path'] = output_path
            task['updated_at'] = datetime.utcnow()
            
            # 計算處理時間
            processing_time = (task['updated_at'] - task_start_time).total_seconds()
            
            # 取得檔案資訊
            file_info = file_handler.get_file_info(output_path)
            if file_info:
                task['metadata'] = {
                    'output_size': file_info['size'],
                    'processing_time': processing_time
                }
            
            # 記錄成功完成
            monitoring_service.record_task_completed(task_id, processing_time)
            
            logger.info(f"任務完成: {task_id}")
            
            # 如果有 webhook，發送通知
            if task.get('webhook_url'):
                await send_webhook_notification(task)
        else:
            raise Exception("DepthFlow 處理失敗")
            
    except Exception as e:
        logger.error(f"任務失敗: {task_id}, 錯誤: {e}")
        
        # 記錄錯誤到監控服務
        monitoring_service.record_error(e, task_id, {
            "operation": "image_processing",
            "file_path": file_path,
            "parameters": parameters
        })
        
        # 檢查是否應該重試
        retry_count = task.get('retry_count', 0)
        max_retries = task.get('max_retries', 3)
        
        if retry_count < max_retries and should_retry_error(e):
            # 準備重試
            retry_count += 1
            task['retry_count'] = retry_count
            task['status'] = 'pending'
            task['message'] = f'處理失敗，準備重試 ({retry_count}/{max_retries})'
            task['updated_at'] = datetime.utcnow()
            
            # 記錄重試歷史
            if 'retry_history' not in task:
                task['retry_history'] = []
            task['retry_history'].append({
                'attempt': retry_count,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # 記錄重試到監控服務
            monitoring_service.record_task_retry(task_id, retry_count)
            
            # 計算重試延遲（指數退避）
            delay = min(60 * (2 ** (retry_count - 1)), 300)  # 最多 5 分鐘
            logger.info(f"任務 {task_id} 將在 {delay} 秒後重試")
            
            # 清理 GPU 記憶體
            try:
                await gpu_manager.cleanup_gpu_memory()
            except:
                pass
            
            # 安排重試
            await asyncio.sleep(delay)
            await process_image_task(task_id, file_path, parameters, tasks_db)
            return
        else:
            # 已達重試上限或不可重試的錯誤
            task['status'] = 'failed'
            task['message'] = '處理失敗'
            task['error_message'] = str(e)
            task['updated_at'] = datetime.utcnow()
            
            # 記錄最終失敗
            monitoring_service.record_metric("task_failed_count", 1, {"task_id": task_id})
            
            # 清理檔案
            file_handler.cleanup_task_files(task_id)


async def send_webhook_notification(task: Dict[str, Any]):
    """
    發送 Webhook 通知
    
    Args:
        task: 任務資訊
    """
    webhook_url = task.get('webhook_url')
    if not webhook_url:
        return
    
    try:
        import httpx
        
        # 準備通知資料
        notification_data = {
            'task_id': task['task_id'],
            'status': task['status'],
            'message': task.get('message'),
            'result_url': f"/api/v1/result/{task['task_id']}",
            'metadata': task.get('metadata', {})
        }
        
        # 發送 POST 請求
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=notification_data,
                timeout=30.0
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook 通知成功: {webhook_url}")
            else:
                logger.warning(
                    f"Webhook 通知失敗: {webhook_url}, "
                    f"狀態碼: {response.status_code}"
                )
                
    except Exception as e:
        logger.error(f"發送 Webhook 通知失敗: {e}")


# Celery 任務定義（當整合 Celery 時使用）
def setup_celery_tasks(celery_app):
    """
    設定 Celery 任務
    
    Args:
        celery_app: Celery 應用實例
    """
    
    @celery_app.task(name='process_image')
    def celery_process_image_task(
        task_id: str,
        file_path: str,
        parameters: Dict[str, Any]
    ):
        """Celery 任務包裝器"""
        # 在 Celery worker 中執行非同步任務
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 注意：這裡需要存取共享的任務資料庫（Redis 或資料庫）
            # 而不是記憶體中的 tasks_db
            loop.run_until_complete(
                process_image_task(task_id, file_path, parameters, {})
            )
        finally:
            loop.close()
    
    return celery_process_image_task