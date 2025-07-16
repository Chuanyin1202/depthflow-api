"""
監控和錯誤追蹤服務
收集系統性能指標、錯誤統計和事件日誌
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
from dataclasses import dataclass, field
from functools import wraps
import traceback

logger = logging.getLogger(__name__)

@dataclass
class MetricsData:
    """指標數據"""
    timestamp: datetime
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class ErrorEvent:
    """錯誤事件"""
    timestamp: datetime
    error_type: str
    error_message: str
    task_id: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

class MonitoringService:
    """監控服務"""
    
    def __init__(self, max_metrics_history: int = 1000, max_error_history: int = 500):
        self.max_metrics_history = max_metrics_history
        self.max_error_history = max_error_history
        
        # 指標儲存
        self.metrics_history: deque = deque(maxlen=max_metrics_history)
        self.error_history: deque = deque(maxlen=max_error_history)
        
        # 統計計數器
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        
        # 性能追蹤
        self.performance_timers: Dict[str, float] = {}
        
        # 錯誤統計
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_rates: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # 任務統計
        self.task_stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "retried_tasks": 0,
            "average_processing_time": 0.0
        }
        
        # 處理時間記錄
        self.processing_times: deque = deque(maxlen=100)
        
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """記錄指標"""
        if tags is None:
            tags = {}
            
        metric = MetricsData(
            timestamp=datetime.now(),
            metric_name=metric_name,
            value=value,
            tags=tags
        )
        
        self.metrics_history.append(metric)
        
        # 更新計數器或測量儀
        if metric_name.endswith('_count'):
            self.counters[metric_name] += value
        else:
            self.gauges[metric_name] = value
        
        logger.debug(f"記錄指標: {metric_name} = {value}")
    
    def record_error(self, error: Exception, task_id: str = None, context: Dict[str, Any] = None):
        """記錄錯誤"""
        if context is None:
            context = {}
            
        error_event = ErrorEvent(
            timestamp=datetime.now(),
            error_type=type(error).__name__,
            error_message=str(error),
            task_id=task_id,
            stack_trace=traceback.format_exc(),
            context=context
        )
        
        self.error_history.append(error_event)
        
        # 更新錯誤統計
        self.error_counts[error_event.error_type] += 1
        self.error_rates[error_event.error_type].append(datetime.now())
        
        logger.error(f"記錄錯誤: {error_event.error_type} - {error_event.error_message}")
        
        # 如果是任務相關錯誤，更新任務統計
        if task_id:
            self.task_stats["failed_tasks"] += 1
    
    def start_timer(self, timer_name: str):
        """開始計時器"""
        self.performance_timers[timer_name] = time.time()
    
    def stop_timer(self, timer_name: str) -> float:
        """停止計時器並返回經過時間"""
        if timer_name not in self.performance_timers:
            logger.warning(f"計時器 {timer_name} 未找到")
            return 0.0
        
        elapsed = time.time() - self.performance_timers[timer_name]
        del self.performance_timers[timer_name]
        
        # 記錄性能指標
        self.record_metric(f"{timer_name}_duration", elapsed)
        
        return elapsed
    
    def record_task_completed(self, task_id: str, processing_time: float):
        """記錄任務完成"""
        self.task_stats["completed_tasks"] += 1
        self.processing_times.append(processing_time)
        
        # 計算平均處理時間
        if self.processing_times:
            self.task_stats["average_processing_time"] = sum(self.processing_times) / len(self.processing_times)
        
        # 記錄指標
        self.record_metric("task_processing_time", processing_time, {"task_id": task_id})
        self.record_metric("task_completed_count", 1)
        
        logger.info(f"任務完成: {task_id}, 處理時間: {processing_time:.2f}秒")
    
    def record_task_retry(self, task_id: str, retry_count: int):
        """記錄任務重試"""
        self.task_stats["retried_tasks"] += 1
        
        # 記錄指標
        self.record_metric("task_retry_count", 1, {"task_id": task_id, "retry_count": str(retry_count)})
        
        logger.info(f"任務重試: {task_id}, 重試次數: {retry_count}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """取得指標摘要"""
        now = datetime.now()
        
        # 計算錯誤率（過去 5 分鐘）
        error_rates_5min = {}
        for error_type, timestamps in self.error_rates.items():
            recent_errors = [ts for ts in timestamps if (now - ts).total_seconds() < 300]
            error_rates_5min[error_type] = len(recent_errors)
        
        # 取得最新的系統指標
        recent_metrics = {}
        for metric in list(self.metrics_history)[-50:]:  # 最近 50 個指標
            if metric.metric_name not in recent_metrics or metric.timestamp > recent_metrics[metric.metric_name]["timestamp"]:
                recent_metrics[metric.metric_name] = {
                    "value": metric.value,
                    "timestamp": metric.timestamp
                }
        
        return {
            "timestamp": now.isoformat(),
            "task_stats": self.task_stats,
            "error_counts": dict(self.error_counts),
            "error_rates_5min": error_rates_5min,
            "recent_metrics": {k: v["value"] for k, v in recent_metrics.items()},
            "active_timers": list(self.performance_timers.keys()),
            "system_health": self._calculate_system_health()
        }
    
    def _calculate_system_health(self) -> str:
        """計算系統健康狀態"""
        # 簡單的健康評估邏輯
        total_tasks = self.task_stats["total_tasks"]
        failed_tasks = self.task_stats["failed_tasks"]
        
        if total_tasks == 0:
            return "unknown"
        
        failure_rate = failed_tasks / total_tasks
        
        if failure_rate > 0.5:
            return "critical"
        elif failure_rate > 0.2:
            return "warning"
        else:
            return "healthy"
    
    def get_error_report(self, hours: int = 24) -> Dict[str, Any]:
        """取得錯誤報告"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_errors = [
            error for error in self.error_history
            if error.timestamp >= cutoff_time
        ]
        
        # 按錯誤類型分組
        errors_by_type = defaultdict(list)
        for error in recent_errors:
            errors_by_type[error.error_type].append(error)
        
        # 生成報告
        report = {
            "time_range": f"過去 {hours} 小時",
            "total_errors": len(recent_errors),
            "error_types": {},
            "recent_errors": []
        }
        
        for error_type, errors in errors_by_type.items():
            report["error_types"][error_type] = {
                "count": len(errors),
                "percentage": (len(errors) / len(recent_errors)) * 100 if recent_errors else 0,
                "latest_error": errors[-1].error_message if errors else None
            }
        
        # 最近的錯誤
        report["recent_errors"] = [
            {
                "timestamp": error.timestamp.isoformat(),
                "type": error.error_type,
                "message": error.error_message,
                "task_id": error.task_id
            }
            for error in sorted(recent_errors, key=lambda x: x.timestamp, reverse=True)[:10]
        ]
        
        return report
    
    def clear_old_data(self, days: int = 7):
        """清理舊數據"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # 清理舊的指標數據
        self.metrics_history = deque(
            [m for m in self.metrics_history if m.timestamp >= cutoff_time],
            maxlen=self.max_metrics_history
        )
        
        # 清理舊的錯誤數據
        self.error_history = deque(
            [e for e in self.error_history if e.timestamp >= cutoff_time],
            maxlen=self.max_error_history
        )
        
        # 清理錯誤率數據
        for error_type, timestamps in self.error_rates.items():
            self.error_rates[error_type] = deque(
                [ts for ts in timestamps if (datetime.now() - ts).total_seconds() < 3600],
                maxlen=100
            )
        
        logger.info(f"清理 {days} 天前的監控數據")

def performance_monitor(operation_name: str):
    """性能監控裝飾器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitoring_service.start_timer(f"{operation_name}_operation")
            try:
                result = await func(*args, **kwargs)
                elapsed = monitoring_service.stop_timer(f"{operation_name}_operation")
                monitoring_service.record_metric(f"{operation_name}_success_count", 1)
                return result
            except Exception as e:
                monitoring_service.stop_timer(f"{operation_name}_operation")
                monitoring_service.record_error(e, context={"operation": operation_name})
                monitoring_service.record_metric(f"{operation_name}_error_count", 1)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitoring_service.start_timer(f"{operation_name}_operation")
            try:
                result = func(*args, **kwargs)
                elapsed = monitoring_service.stop_timer(f"{operation_name}_operation")
                monitoring_service.record_metric(f"{operation_name}_success_count", 1)
                return result
            except Exception as e:
                monitoring_service.stop_timer(f"{operation_name}_operation")
                monitoring_service.record_error(e, context={"operation": operation_name})
                monitoring_service.record_metric(f"{operation_name}_error_count", 1)
                raise
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    
    return decorator

# 全域監控服務實例
monitoring_service = MonitoringService()

def get_monitoring_service() -> MonitoringService:
    """取得監控服務實例"""
    return monitoring_service