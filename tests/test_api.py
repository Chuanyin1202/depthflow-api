import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """測試健康檢查端點"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_root_endpoint():
    """測試根端點"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_get_presets():
    """測試取得預設配置"""
    response = client.get("/api/v1/presets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # 檢查預設配置結構
    for preset in data:
        assert "name" in preset
        assert "parameters" in preset
        assert "depth_strength" in preset["parameters"]


def test_get_system_status():
    """測試系統狀態端點"""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "queue_length" in data
    assert "active_tasks" in data


def test_task_not_found():
    """測試查詢不存在的任務"""
    response = client.get("/api/v1/task/non-existent-task-id")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "task_not_found"


def test_upload_without_file():
    """測試沒有檔案的上傳請求"""
    response = client.post("/api/v1/process")
    assert response.status_code == 422  # Unprocessable Entity


def test_upload_invalid_file_format():
    """測試無效檔案格式"""
    # 創建一個假的文字檔案
    files = {"file": ("test.txt", b"This is not an image", "text/plain")}
    response = client.post("/api/v1/process", files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "invalid_file_format"


@pytest.mark.asyncio
async def test_file_validation():
    """測試檔案驗證邏輯"""
    from app.api.dependencies import validate_file_extension
    
    assert validate_file_extension("image.jpg") == True
    assert validate_file_extension("image.JPEG") == True
    assert validate_file_extension("image.png") == True
    assert validate_file_extension("image.gif") == False
    assert validate_file_extension("document.pdf") == False
    assert validate_file_extension(None) == False