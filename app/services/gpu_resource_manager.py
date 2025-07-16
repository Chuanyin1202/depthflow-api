"""
GPU 資源管理器
處理 GPU 記憶體監控、任務調度和資源限制
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class GPUStatus:
    """GPU 狀態信息"""
    available: bool = False
    memory_total: int = 0
    memory_used: int = 0
    memory_free: int = 0
    memory_percent: float = 0.0
    temperature: Optional[float] = None
    utilization: Optional[float] = None

class GPUResourceManager:
    """GPU 資源管理器"""
    
    def __init__(self, max_concurrent_tasks: int = 3, memory_threshold: float = 0.8):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.memory_threshold = memory_threshold
        self.active_tasks = 0
        self.task_queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._gpu_available = None
        self._last_gpu_check = None
        
    async def get_gpu_status(self) -> GPUStatus:
        """取得 GPU 狀態信息"""
        status = GPUStatus()
        
        try:
            import torch
            if torch.cuda.is_available():
                status.available = True
                device = torch.cuda.current_device()
                
                # 取得記憶體信息
                memory_total = torch.cuda.get_device_properties(device).total_memory
                memory_allocated = torch.cuda.memory_allocated(device)
                memory_cached = torch.cuda.memory_reserved(device)
                
                status.memory_total = memory_total
                status.memory_used = memory_allocated
                status.memory_free = memory_total - memory_cached
                status.memory_percent = (memory_cached / memory_total) * 100
                
                # 取得 GPU 利用率（需要 nvidia-ml-py）
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(device)
                    
                    # 取得溫度
                    temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    status.temperature = temperature
                    
                    # 取得利用率
                    utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    status.utilization = utilization.gpu
                    
                except ImportError:
                    logger.warning("pynvml 未安裝，無法取得詳細 GPU 狀態")
                except Exception as e:
                    logger.warning(f"取得 GPU 狀態時出錯: {e}")
                    
        except ImportError:
            logger.warning("PyTorch 未安裝，GPU 不可用")
        except Exception as e:
            logger.error(f"檢查 GPU 狀態時出錯: {e}")
            
        return status
    
    async def is_gpu_available(self) -> bool:
        """檢查 GPU 是否可用"""
        # 快取 GPU 可用性檢查結果 30 秒
        now = datetime.now()
        if (self._last_gpu_check is None or 
            (now - self._last_gpu_check).total_seconds() > 30):
            
            status = await self.get_gpu_status()
            self._gpu_available = status.available
            self._last_gpu_check = now
            
        return self._gpu_available
    
    async def check_gpu_memory(self) -> Dict[str, Any]:
        """檢查 GPU 記憶體狀態"""
        status = await self.get_gpu_status()
        
        if not status.available:
            return {
                "available": False,
                "error": "GPU 不可用"
            }
        
        memory_usage_percent = status.memory_percent / 100
        
        return {
            "available": True,
            "memory_total": status.memory_total,
            "memory_used": status.memory_used,
            "memory_free": status.memory_free,
            "memory_percent": status.memory_percent,
            "memory_available": memory_usage_percent < self.memory_threshold,
            "temperature": status.temperature,
            "utilization": status.utilization
        }
    
    async def can_process_task(self) -> Dict[str, Any]:
        """檢查是否可以處理新任務"""
        async with self._lock:
            # 檢查併發任務限制
            if self.active_tasks >= self.max_concurrent_tasks:
                return {
                    "can_process": False,
                    "reason": "達到最大併發任務限制",
                    "active_tasks": self.active_tasks,
                    "max_tasks": self.max_concurrent_tasks
                }
            
            # 檢查 GPU 狀態
            gpu_status = await self.check_gpu_memory()
            if not gpu_status["available"]:
                return {
                    "can_process": False,
                    "reason": "GPU 不可用",
                    "gpu_status": gpu_status
                }
            
            if not gpu_status["memory_available"]:
                return {
                    "can_process": False,
                    "reason": "GPU 記憶體不足",
                    "gpu_status": gpu_status
                }
            
            return {
                "can_process": True,
                "active_tasks": self.active_tasks,
                "gpu_status": gpu_status
            }
    
    @asynccontextmanager
    async def acquire_gpu_slot(self, task_id: str):
        """取得 GPU 處理槽位"""
        # 檢查是否可以處理任務
        check_result = await self.can_process_task()
        if not check_result["can_process"]:
            error_msg = f"無法取得 GPU 槽位: {check_result['reason']}"
            logger.warning(f"Task {task_id}: {error_msg}")
            raise RuntimeError(error_msg)
        
        async with self._lock:
            self.active_tasks += 1
            logger.info(f"Task {task_id}: 取得 GPU 槽位 ({self.active_tasks}/{self.max_concurrent_tasks})")
        
        try:
            # 清理 GPU 快取
            await self.cleanup_gpu_memory()
            yield
        finally:
            async with self._lock:
                self.active_tasks -= 1
                logger.info(f"Task {task_id}: 釋放 GPU 槽位 ({self.active_tasks}/{self.max_concurrent_tasks})")
    
    async def cleanup_gpu_memory(self):
        """清理 GPU 記憶體"""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.debug("GPU 記憶體快取已清理")
        except Exception as e:
            logger.warning(f"清理 GPU 記憶體時出錯: {e}")
    
    async def force_cleanup(self):
        """強制清理 GPU 記憶體（緊急情況使用）"""
        try:
            import torch
            if torch.cuda.is_available():
                # 強制清理所有 GPU 記憶體
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                torch.cuda.synchronize()
                logger.info("執行強制 GPU 記憶體清理")
        except Exception as e:
            logger.error(f"強制清理 GPU 記憶體時出錯: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """取得統計信息"""
        return {
            "active_tasks": self.active_tasks,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "memory_threshold": self.memory_threshold,
            "queue_size": self.task_queue.qsize() if hasattr(self.task_queue, 'qsize') else 0
        }

# 全局 GPU 資源管理器實例
gpu_manager = GPUResourceManager()

async def get_gpu_manager() -> GPUResourceManager:
    """取得 GPU 資源管理器實例"""
    return gpu_manager