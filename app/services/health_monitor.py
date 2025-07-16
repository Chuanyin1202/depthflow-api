"""
健康檢查和自動恢復服務
監控系統狀態，自動處理問題和恢復機制
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import psutil

from app.services.gpu_resource_manager import get_gpu_manager

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """健康狀態"""
    timestamp: datetime = field(default_factory=datetime.now)
    overall_status: str = "healthy"  # healthy, warning, critical
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # 系統指標
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_available: bool = False
    gpu_memory_usage: float = 0.0
    gpu_temperature: Optional[float] = None
    
    # 任務相關
    active_tasks: int = 0
    failed_tasks_count: int = 0
    stuck_tasks_count: int = 0

class HealthMonitor:
    """健康監控服務"""
    
    def __init__(self):
        self.check_interval = 30  # 檢查間隔（秒）
        self.task_timeout = 300  # 任務超時時間（5分鐘）
        self.cleanup_interval = 600  # 清理間隔（10分鐘）
        self.last_cleanup = datetime.now()
        self.running = False
        
    async def start_monitoring(self):
        """啟動健康監控"""
        if self.running:
            return
            
        self.running = True
        logger.info("健康監控服務啟動")
        
        # 啟動監控任務
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._cleanup_loop())
    
    async def stop_monitoring(self):
        """停止健康監控"""
        self.running = False
        logger.info("健康監控服務停止")
    
    async def _monitoring_loop(self):
        """監控循環"""
        while self.running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"健康檢查錯誤: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _cleanup_loop(self):
        """清理循環"""
        while self.running:
            try:
                if (datetime.now() - self.last_cleanup).total_seconds() > self.cleanup_interval:
                    await self._perform_cleanup()
                    self.last_cleanup = datetime.now()
                await asyncio.sleep(60)  # 每分鐘檢查一次是否需要清理
            except Exception as e:
                logger.error(f"清理循環錯誤: {e}")
                await asyncio.sleep(60)
    
    async def _perform_health_check(self):
        """執行健康檢查"""
        try:
            # 檢查系統資源
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # 檢查 GPU 狀態
            gpu_manager = await get_gpu_manager()
            gpu_status = await gpu_manager.check_gpu_memory()
            
            # 檢查磁碟空間
            disk_usage = psutil.disk_usage('/')
            
            # 創建健康狀態報告
            health_status = HealthStatus(
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                gpu_available=gpu_status.get("available", False),
                gpu_memory_usage=gpu_status.get("memory_percent", 0),
                gpu_temperature=gpu_status.get("temperature")
            )
            
            # 檢查各種問題
            await self._check_resource_issues(health_status, cpu_percent, memory.percent, disk_usage)
            await self._check_gpu_issues(health_status, gpu_status)
            await self._check_task_issues(health_status)
            
            # 根據問題設定整體狀態
            self._determine_overall_status(health_status)
            
            # 記錄狀態
            if health_status.overall_status != "healthy":
                logger.warning(f"健康狀態: {health_status.overall_status}, 問題: {health_status.issues}")
            
            # 自動恢復
            await self._auto_recovery(health_status)
            
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
    
    async def _check_resource_issues(self, health_status: HealthStatus, cpu_percent: float, memory_percent: float, disk_usage):
        """檢查資源問題"""
        # CPU 使用率過高
        if cpu_percent > 90:
            health_status.issues.append(f"CPU 使用率過高: {cpu_percent:.1f}%")
            health_status.recommendations.append("考慮增加 CPU 資源或優化程式碼")
        
        # 記憶體使用率過高
        if memory_percent > 85:
            health_status.issues.append(f"記憶體使用率過高: {memory_percent:.1f}%")
            health_status.recommendations.append("考慮增加記憶體或優化記憶體使用")
        
        # 磁碟空間不足
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        if disk_percent > 90:
            health_status.issues.append(f"磁碟空間不足: {disk_percent:.1f}%")
            health_status.recommendations.append("清理磁碟空間或增加儲存容量")
    
    async def _check_gpu_issues(self, health_status: HealthStatus, gpu_status: Dict):
        """檢查 GPU 問題"""
        if not gpu_status.get("available", False):
            health_status.issues.append("GPU 不可用")
            health_status.recommendations.append("檢查 GPU 驅動程式和 CUDA 安裝")
            return
        
        # GPU 記憶體使用率過高
        gpu_memory_percent = gpu_status.get("memory_percent", 0)
        if gpu_memory_percent > 90:
            health_status.issues.append(f"GPU 記憶體使用率過高: {gpu_memory_percent:.1f}%")
            health_status.recommendations.append("清理 GPU 記憶體或減少併發任務")
        
        # GPU 溫度過高
        gpu_temperature = gpu_status.get("temperature")
        if gpu_temperature and gpu_temperature > 85:
            health_status.issues.append(f"GPU 溫度過高: {gpu_temperature:.1f}°C")
            health_status.recommendations.append("檢查 GPU 散熱或減少工作負載")
    
    async def _check_task_issues(self, health_status: HealthStatus):
        """檢查任務問題"""
        # 這裡需要存取任務資料庫來檢查任務狀態
        # 暫時使用模擬資料，之後需要整合真正的任務資料庫
        try:
            # 從全域任務資料庫檢查（這需要重構來支援）
            # 檢查長時間運行的任務
            # 檢查失敗的任務
            pass
        except Exception as e:
            logger.warning(f"檢查任務狀態時出錯: {e}")
    
    def _determine_overall_status(self, health_status: HealthStatus):
        """決定整體健康狀態"""
        critical_keywords = ["不可用", "不足", "過高"]
        warning_keywords = ["警告", "注意"]
        
        has_critical = any(
            any(keyword in issue for keyword in critical_keywords)
            for issue in health_status.issues
        )
        
        has_warning = any(
            any(keyword in issue for keyword in warning_keywords)
            for issue in health_status.issues
        )
        
        if has_critical:
            health_status.overall_status = "critical"
        elif has_warning or health_status.issues:
            health_status.overall_status = "warning"
        else:
            health_status.overall_status = "healthy"
    
    async def _auto_recovery(self, health_status: HealthStatus):
        """自動恢復機制"""
        try:
            # GPU 記憶體清理
            if any("GPU 記憶體" in issue for issue in health_status.issues):
                await self._cleanup_gpu_memory()
            
            # 清理過期任務
            if any("任務" in issue for issue in health_status.issues):
                await self._cleanup_stuck_tasks()
            
        except Exception as e:
            logger.error(f"自動恢復失敗: {e}")
    
    async def _cleanup_gpu_memory(self):
        """清理 GPU 記憶體"""
        try:
            gpu_manager = await get_gpu_manager()
            await gpu_manager.force_cleanup()
            logger.info("執行 GPU 記憶體清理")
        except Exception as e:
            logger.error(f"GPU 記憶體清理失敗: {e}")
    
    async def _cleanup_stuck_tasks(self):
        """清理卡住的任務"""
        try:
            # 這裡需要存取任務資料庫來清理長時間運行的任務
            # 暫時記錄日誌
            logger.info("檢查並清理卡住的任務")
        except Exception as e:
            logger.error(f"清理卡住任務失敗: {e}")
    
    async def _perform_cleanup(self):
        """執行定期清理"""
        try:
            logger.info("執行定期清理")
            
            # 清理臨時檔案
            await self._cleanup_temp_files()
            
            # 清理 GPU 記憶體
            await self._cleanup_gpu_memory()
            
            # 清理過期任務
            await self._cleanup_expired_tasks()
            
        except Exception as e:
            logger.error(f"定期清理失敗: {e}")
    
    async def _cleanup_temp_files(self):
        """清理臨時檔案"""
        try:
            import os
            import glob
            from pathlib import Path
            
            # 清理上傳目錄中的過期檔案
            uploads_dir = Path("storage/uploads")
            if uploads_dir.exists():
                # 刪除 24 小時前的檔案
                cutoff_time = datetime.now() - timedelta(hours=24)
                for file_path in uploads_dir.glob("*"):
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            file_path.unlink()
                            logger.debug(f"刪除過期檔案: {file_path}")
            
            # 清理輸出目錄中的過期檔案
            outputs_dir = Path("storage/outputs")
            if outputs_dir.exists():
                # 刪除 48 小時前的檔案
                cutoff_time = datetime.now() - timedelta(hours=48)
                for file_path in outputs_dir.glob("*"):
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            file_path.unlink()
                            logger.debug(f"刪除過期結果檔案: {file_path}")
            
        except Exception as e:
            logger.error(f"清理臨時檔案失敗: {e}")
    
    async def _cleanup_expired_tasks(self):
        """清理過期任務"""
        try:
            # 這裡需要存取任務資料庫來清理過期任務
            # 暫時記錄日誌
            logger.info("清理過期任務")
        except Exception as e:
            logger.error(f"清理過期任務失敗: {e}")
    
    async def get_health_status(self) -> HealthStatus:
        """取得目前健康狀態"""
        # 執行即時健康檢查
        await self._perform_health_check()
        
        # 返回當前狀態（簡化版本）
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        gpu_manager = await get_gpu_manager()
        gpu_status = await gpu_manager.check_gpu_memory()
        
        return HealthStatus(
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            gpu_available=gpu_status.get("available", False),
            gpu_memory_usage=gpu_status.get("memory_percent", 0),
            gpu_temperature=gpu_status.get("temperature")
        )

# 全域健康監控器實例
health_monitor = HealthMonitor()

async def get_health_monitor() -> HealthMonitor:
    """取得健康監控器實例"""
    return health_monitor

async def start_health_monitoring():
    """啟動健康監控"""
    monitor = await get_health_monitor()
    await monitor.start_monitoring()

async def stop_health_monitoring():
    """停止健康監控"""
    monitor = await get_health_monitor()
    await monitor.stop_monitoring()