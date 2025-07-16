# DepthFlow REST API

將靜態圖片轉換為 2.5D 視差動畫的 REST API 服務，基於 [DepthFlow](https://github.com/BrokenSource/DepthFlow) 開源專案。

## 功能特點

- 🖼️ 支援 JPEG/PNG 圖片上傳
- 🎬 生成 MP4/WebM/GIF 格式的 2.5D 動畫
- ⚡ 非同步任務處理，支援大量並發請求
- 📊 任務進度追蹤和狀態查詢
- 🔄 可自訂處理參數（深度強度、動畫時長等）
- 🐳 Docker 容器化部署
- 📝 自動生成 API 文檔

## 快速開始

### 環境需求

- Python 3.11+ (建議 3.12)
- Redis 6.0+
- GPU（建議，用於加速處理）
- FFmpeg（用於影片處理）

### 本地安裝

1. 克隆專案
```bash
git clone <your-repo-url>
cd depthflow-api
```

2. 建立虛擬環境
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows
```

3. 安裝依賴
```bash
pip install -r requirements.txt
```

4. 設定環境變數
```bash
cp .env.example .env
# 編輯 .env 檔案，設定必要的參數
```

5. 啟動 Redis
```bash
redis-server
```

6. 執行服務
```bash
python -m app.main
```

### Docker 部署

使用 Docker Compose 一鍵部署：

```bash
cd docker
docker-compose up -d
```

服務將在以下端口啟動：
- API 服務：http://localhost:8080
- API 文檔：http://localhost:8080/docs
- Flower 監控：http://localhost:5555（可選）

## API 使用說明

### 1. 上傳圖片並處理

```bash
curl -X POST "http://localhost:8080/api/v1/process" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/image.jpg" \
  -F 'request={
    "parameters": {
      "depth_strength": 1.5,
      "animation_duration": 3.0,
      "fps": 30,
      "output_format": "mp4"
    }
  }'
```

回應範例：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2024-01-16T10:30:00Z",
  "updated_at": "2024-01-16T10:30:00Z"
}
```

### 2. 查詢任務狀態

```bash
curl -X GET "http://localhost:8080/api/v1/task/{task_id}"
```

回應範例：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "message": "處理完成",
  "result_url": "/api/v1/result/550e8400-e29b-41d4-a716-446655440000"
}
```

### 3. 下載處理結果

```bash
curl -X GET "http://localhost:8080/api/v1/result/{task_id}" \
  --output result.mp4
```

## 處理參數說明

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| depth_strength | float | 1.0 | 深度強度 (0.1-5.0) |
| animation_duration | float | 3.0 | 動畫時長（秒）(1.0-10.0) |
| fps | int | 30 | 影格率 (15-60) |
| output_format | string | mp4 | 輸出格式 (mp4/webm/gif) |
| resolution | int | null | 最大解析度 (480-2048) |
| loop | bool | true | 是否循環播放 |
| depth_model | string | default | 深度估計模型 |
| camera_movement | string | orbit | 相機運動模式 (orbit/zoom/dolly/static) |

### 相機運動模式說明
- **orbit**: 環繞運動，相機圍繞場景中心旋轉
- **zoom**: 縮放運動，相機前後移動
- **dolly**: 推軌運動，相機平行移動
- **static**: 靜態，無相機運動

## 專案結構

```
depthflow-api/
├── app/
│   ├── api/          # API 路由和端點
│   ├── models/       # 資料模型
│   ├── services/     # 商業邏輯服務
│   ├── tasks/        # 非同步任務
│   └── utils/        # 工具函數
├── storage/          # 檔案儲存
├── docker/           # Docker 配置
├── tests/            # 測試檔案
└── requirements.txt  # Python 依賴
```

## 進階配置

### GPU 支援

如果您的伺服器有 NVIDIA GPU，可以在 `docker-compose.yml` 中啟用 GPU 支援：

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

### 擴展性

- 使用 Kubernetes 進行水平擴展
- 配置多個 Celery Worker 處理更多並發任務
- 使用 S3 或其他物件儲存服務儲存結果檔案

## 故障排除

### DepthFlow 未安裝

如果出現 DepthFlow 相關錯誤，請確保已正確安裝：

```bash
pip install depthflow
```

### GPU 不可用

檢查 CUDA 和 GPU 驅動是否正確安裝：

```bash
nvidia-smi
```

### Redis 連接失敗

確保 Redis 服務正在執行：

```bash
redis-cli ping
```

## 授權

本專案基於 MIT 授權條款開源。

## 貢獻指南

歡迎提交 Pull Request 或開啟 Issue！

## 相關連結

- [DepthFlow 官方專案](https://github.com/BrokenSource/DepthFlow)
- [FastAPI 文檔](https://fastapi.tiangolo.com/)
- [Celery 文檔](https://docs.celeryproject.org/)