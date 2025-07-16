from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.config import settings
from app.api import routes
from app.models.schemas import ErrorResponse, HealthResponse

# 設定日誌
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    # 啟動時執行
    logger.info(f"啟動 {settings.app_name} v{settings.app_version}")
    settings.ensure_directories()
    
    yield
    
    # 關閉時執行
    logger.info("正在關閉應用程式...")


# 建立 FastAPI 實例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DepthFlow REST API - 將靜態圖片轉換為 2.5D 動畫",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# 全域異常處理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全域異常處理器"""
    logger.error(f"未處理的異常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message="內部伺服器錯誤",
            detail={"error": str(exc)} if settings.debug else None
        ).model_dump()
    )


# 根路徑
@app.get("/", response_model=HealthResponse)
async def root():
    """根路徑 - 健康檢查"""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow()
    )


# 健康檢查端點
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康檢查端點"""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow()
    )


# 包含 API 路由
app.include_router(
    routes.router,
    prefix=settings.api_prefix,
    tags=["DepthFlow API"]
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )