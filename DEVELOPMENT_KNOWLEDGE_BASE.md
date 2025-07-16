# Development Knowledge Base - DepthFlow API

🧠 **DepthFlow API Development Experience** - Technical challenges and solutions

---

## 📋 Contents
1. [Platform/Technology Specific Experiences](#platform-experiences)
2. [Technical Challenges & Solutions](#technical-challenges)
3. [Performance Optimization](#performance-optimization)
4. [Error Handling & Debugging](#error-handling)
5. [Integration Experiences](#integration-experiences)
6. [Best Practices Discovered](#best-practices)
7. [Future Development Guidelines](#future-guidelines)

---

## Platform/Technology Specific Experiences

### 🎯 Core Challenges

#### Challenge: DepthFlow Python API 整合
- **Context**: DepthFlow 提供了 Python API 但需要額外依賴（如 PyTorch）
- **Issue**: 初次導入時發現依賴問題 (SimpleTorch.CUDA124 錯誤)
- **Solution**: 實作了雙重策略 - 優先嘗試 Python API，失敗時降級到 CLI 調用
- **Code Example**:
```python
try:
    from depthflow.scene import DepthScene
    scene = DepthScene(backend="headless")
    scene.input(image=[input_path])
    scene.config.animation.add(Animation.Orbital(intensity=1.0))
    scene.main(output=output_path, time=3, fps=30)
except ImportError:
    # 降級到 CLI
    subprocess.run(["depthflow", "--image", input_path, ...])
```

#### Challenge: GPU 記憶體管理
- **Context**: 高解析度圖片處理可能耗盡 GPU 記憶體
- **Issue**: 多個並發任務可能導致 OOM
- **Solution**: 實作任務隊列限制並發 GPU 任務數量

### 🔍 Key Technical Discoveries

#### Discovery: DepthFlow 架構理解
- **Discovery**: DepthFlow 基於 DepthScene 類別，支援多種動畫預設（Orbital、Zoom、Dolly）
- **Impact**: 可以提供多樣化的相機運動效果給用戶選擇
- **Application**: 在 API 中暴露這些選項作為 camera_movement 參數

#### Discovery: DepthFlow 依賴管理
- **Discovery**: DepthFlow 需要 PyTorch 和其他 GPU 相關依賴，但 CLI 模式可以獨立運行
- **Impact**: 提供了更好的降級策略
- **Application**: Python API 失敗時可以安全降級到 CLI

#### Discovery: FastAPI BackgroundTasks vs Celery
- **Discovery**: FastAPI 的 BackgroundTasks 適合輕量級任務，但不適合長時間運行的任務
- **Impact**: 需要整合 Celery 處理實際的圖片處理任務
- **Application**: 使用 BackgroundTasks 進行快速回應，Celery 處理實際工作

#### Discovery: 檔案儲存策略
- **Discovery**: 本地檔案系統在容器化環境中需要掛載 volume
- **Impact**: 需要考慮分散式部署時的檔案共享問題
- **Application**: 未來應考慮使用 S3 或其他物件儲存

## Technical Challenges & Solutions

### Problem: 非同步任務狀態同步
**Context**: 使用記憶體儲存任務狀態在多進程環境下無法共享
**Symptoms**: Worker 進程無法更新主進程中的任務狀態
**Investigation**: 發現 tasks_db 字典在不同進程間不共享
**Root Cause**: Python 進程間記憶體隔離
**Solution**: 應使用 Redis 或資料庫儲存任務狀態
**Prevention**: 從一開始就設計為分散式架構

### Problem: 圖片格式相容性
**Context**: 用戶可能上傳各種格式的圖片
**Symptoms**: 某些圖片格式導致處理失敗
**Investigation**: PIL/Pillow 對某些格式支援有限
**Root Cause**: 圖片格式多樣性
**Solution**: 預處理階段統一轉換為 RGB JPEG
**Prevention**: 在上傳時進行格式驗證和轉換

## Performance Optimization

### GPU 處理優化
- 實作批次處理以提高 GPU 利用率
- 使用較低的預設解析度進行快速預覽
- 實作智慧排程，根據 GPU 記憶體動態調整任務

### API 回應時間優化
- 使用非同步處理避免阻塞
- 實作任務結果快取
- 使用 Redis 進行任務狀態快取

## Error Handling & Debugging

### 常見錯誤處理
1. **檔案上傳失敗**: 實作重試機制和詳細錯誤訊息
2. **GPU OOM**: 自動降級到 CPU 處理或降低解析度
3. **DepthFlow 崩潰**: 捕獲並記錄詳細錯誤，提供備用處理方案

### 除錯策略
- 使用結構化日誌記錄所有關鍵步驟
- 實作健康檢查端點監控服務狀態
- 保留處理失敗的檔案供除錯

## Integration Experiences

### DepthFlow 整合
- CLI 介面相對穩定，但效能較差
- Python API 需要更多文檔支援
- 考慮直接使用底層的深度估計模型

### Docker 容器化
- GPU 支援需要 nvidia-docker
- 檔案權限問題需要特別注意
- 多階段建構可減少映像大小

## Best Practices Discovered

1. **任務管理**: 使用唯一 UUID 追蹤任務，便於除錯和監控
2. **錯誤處理**: 提供詳細的錯誤訊息和錯誤代碼
3. **API 設計**: RESTful 原則配合非同步處理模式
4. **檔案管理**: 定期清理過期檔案避免磁碟空間不足

## Future Development Guidelines

### 建議的改進方向

1. **持久化儲存**
   - 整合 PostgreSQL 儲存任務元資料
   - 使用 S3 儲存處理結果

2. **效能優化**
   - 實作真正的 Celery 整合
   - 加入任務優先級隊列
   - 實作智慧的 GPU 資源調度

3. **功能擴展**
   - 支援批次處理多張圖片
   - 加入更多自訂參數（濾鏡、特效等）
   - 實作即時預覽功能

4. **監控和維運**
   - 整合 Prometheus 指標
   - 實作詳細的效能追蹤
   - 加入自動擴展支援

### 技術債務
- 任務狀態目前儲存在記憶體中，需要遷移到持久化儲存
- 錯誤處理可以更細緻
- 需要加入更多的單元測試和整合測試

### 部署建議
- 使用 Kubernetes 進行生產環境部署
- 配置自動擴展策略
- 實作藍綠部署減少服務中斷

---

*最後更新: 2025-01-16*