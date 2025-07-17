# ☁️ Google Colab 部署指南

在 Google Colab 上快速部署 DepthFlow API 服務，享受免費 GPU 加速和公網訪問。

## 🎯 為什麼選擇 Colab？

- 🆓 **完全免費**：提供免費 GPU 加速（T4/P100/V100）
- 🌐 **公網訪問**：自動獲得公網 IP，手機可直接連接
- ⚡ **快速部署**：5-10 分鐘即可完成部署
- 🔄 **免配置**：無需設定防火牆或網路
- 💻 **零安裝**：瀏覽器即可操作

## 🚀 完整部署教學

### 步驟一：準備工作

1. **開啟 Google Colab**
   - 訪問：https://colab.research.google.com/
   - 登入您的 Google 帳號

2. **上傳 Notebook**
   - 點擊「檔案」→「上傳筆記本」
   - 選擇 `DepthFlow_Server.ipynb` 文件
   - 或者直接從 GitHub 開啟

3. **啟用 GPU 加速**（重要！）
   ```
   Runtime → Change runtime type → Hardware accelerator → GPU → Save
   ```

### 步驟二：執行部署（約 5-10 分鐘）

**🔧 儲存格 1：環境檢查**
```python
# 檢查 Python 和 GPU 環境
# 如果顯示 "CUDA 可用: False"，請確認已啟用 GPU
```
**預期輸出**：
```
Python 版本: Python 3.10.x
CUDA 可用: True
GPU 設備: Tesla T4
```

**📦 儲存格 2：安裝依賴**
```python
# 安裝所有必要套件（約 2-3 分鐘）
# 包含 FastAPI、DepthFlow、ngrok 等
```
**預期輸出**：
```
✅ 依賴安裝完成！
```

**🌐 儲存格 3：設定 ngrok**
```python
# 安裝 ngrok 隧道工具
# 可選：註冊 ngrok 帳號獲得穩定域名
```

**💡 專業提示**：註冊 ngrok 帳號可獲得：
- 穩定的域名
- 更長的會話時間
- 更好的連接穩定性

**📁 儲存格 4：創建結構**
```python
# 自動創建專案目錄
# 準備文件存儲位置
```

**📝 儲存格 5：下載代碼**
```python
# 從 GitHub 自動下載您的 API 服務
# 複製到 Colab 環境
```

**⚙️ 儲存格 6：環境配置**
```python
# 創建針對 Colab 優化的配置
# 設定 CORS、文件路徑等
```

**🚀 儲存格 7：啟動服務**
```python
# 在後台啟動 DepthFlow API
# 等待服務完全啟動
```
**預期輸出**：
```
🚀 DepthFlow API 服務啟動中...
⏳ 等待服務初始化（約 10 秒）...
```

**🌐 儲存格 8：建立公網隧道**
```python
# 🔥 關鍵步驟：獲得公網 URL
# 這裡會顯示您的 API 端點
```
**預期輸出**：
```
🎉 DepthFlow API 服務已成功部署！

📱 手機 App 設定：
API 端點: https://1a2b3c4d.ngrok.io

🌐 API 文檔: https://1a2b3c4d.ngrok.io/docs
📊 系統狀態: https://1a2b3c4d.ngrok.io/api/v1/status

✅ 服務測試成功！

🔗 Flutter App 配置：
複製此 URL 到 lib/services/api_service.dart 的 defaultBaseUrl
URL: https://1a2b3c4d.ngrok.io
```

### 步驟三：配置手機 App

1. **複製 API URL**
   - 從儲存格 8 複製 ngrok URL
   - 例如：`https://1a2b3c4d.ngrok.io`

2. **修改 Flutter App**
   ```dart
   // mobile-app/lib/services/api_service.dart
   class ApiService {
     static const String defaultBaseUrl = "https://1a2b3c4d.ngrok.io";  // 貼上您的 URL
   ```

3. **重新編譯 App**
   ```bash
   cd mobile-app
   flutter build apk
   ```

4. **安裝到手機**
   - 將生成的 APK 安裝到手機
   - 或使用 `flutter run` 直接運行

### 步驟四：測試與監控

**📊 儲存格 9：服務監控**
- 檢查服務運行狀態
- 監控 GPU 使用情況
- 可重複執行查看即時狀態

**🧪 儲存格 10：測試界面**
- 提供便利的測試連結
- 直接訪問 API 文檔
- 驗證服務功能

**💾 儲存格 11：保持會話**
- 每 5 分鐘自動輸出
- 防止 Colab 自動休眠
- 持續監控服務狀態

## 📱 手機 App 使用流程

1. **開啟 App**：啟動 Flutter App
2. **拍照或選擇**：使用相機拍照或從相簿選擇
3. **上傳處理**：App 會自動上傳到 Colab 服務
4. **等待完成**：查看處理進度（約 10-30 秒）
5. **預覽結果**：App 內播放生成的 2.5D 動畫
6. **保存分享**：下載或分享動畫

## ⚠️ 重要注意事項

### 會話管理
- **免費版限制**：12 小時最大會話時間
- **自動休眠**：90 分鐘無操作會自動休眠
- **URL 失效**：會話結束後 ngrok URL 會失效

### 效能建議
- **圖片大小**：建議不超過 1920px 解析度
- **處理時間**：GPU 加速約 10-30 秒，CPU 約 1-2 分鐘
- **同時處理**：建議一次處理一張圖片

### 成本考量
- **免費額度**：每月約 100-200 小時免費 GPU 時間
- **Colab Pro**：$9.99/月，更穩定的 GPU 和更長會話時間

## 🔧 故障排除

### 常見問題

#### 1. GPU 不可用
**症狀**：顯示「CUDA 可用: False」
**解決**：
```
Runtime → Change runtime type → Hardware accelerator → GPU → Save
然後重新執行儲存格 1
```

#### 2. 依賴安裝失敗
**症狀**：pip install 出現錯誤
**解決**：
```
Runtime → Restart runtime
然後重新執行儲存格 2
```

#### 3. 服務啟動失敗
**症狀**：儲存格 7 執行後沒有輸出
**解決**：
```
等待更長時間（約 30 秒）
或重新執行儲存格 7
```

#### 4. ngrok 隧道失敗
**症狀**：儲存格 8 顯示連接錯誤
**解決**：
```
重新執行儲存格 8
或註冊 ngrok 帳號並設定 authtoken
```

#### 5. 手機 App 無法連接
**症狀**：App 顯示網路錯誤
**檢查**：
- [ ] 複製的 URL 是否正確
- [ ] URL 是否包含 `https://`
- [ ] Colab 會話是否仍在運行
- [ ] 手機網路是否正常

### 錯誤代碼說明

| 錯誤碼 | 說明 | 解決方案 |
|--------|------|----------|
| 500 | 服務內部錯誤 | 檢查 Colab 日誌，重啟服務 |
| 422 | 請求格式錯誤 | 檢查圖片格式和大小 |
| 413 | 文件過大 | 壓縮圖片到 20MB 以下 |
| 503 | 服務不可用 | 等待服務啟動完成 |

## 💡 最佳實踐

### 部署前準備
1. **測試 GitHub 連接**：確保 depthflow-api 倉庫可正常訪問
2. **準備測試圖片**：選擇幾張品質好的照片進行測試
3. **手機準備**：確保手機已安裝 Flutter App

### 使用期間
1. **保持瀏覽器開啟**：避免 Colab 會話意外結束
2. **定期檢查狀態**：每隔一段時間執行監控儲存格
3. **備份重要結果**：及時下載生成的動畫

### 長期使用
1. **考慮 Colab Pro**：如需穩定的長期服務
2. **建立 ngrok 帳號**：獲得穩定域名
3. **監控使用量**：注意免費額度限制

## 🎓 進階配置

### 自定義 ngrok 域名
```python
# 在儲存格 3 中設定 authtoken
!ngrok authtoken YOUR_AUTH_TOKEN

# 在儲存格 8 中使用固定域名
public_tunnel = ngrok.connect(8080, subdomain="your-custom-name")
```

### 優化處理參數
```python
# 在儲存格 6 中調整 .env 設定
DEPTHFLOW_MAX_RESOLUTION=1080  # 降低解析度提升速度
DEPTHFLOW_DEFAULT_DURATION=2   # 縮短動畫時長
```

### 添加基本認證
```python
# 在 .env 中啟用 API 金鑰
API_KEY_ENABLED=true
API_KEY=your-secret-key
```

## 📞 取得協助

如果您在部署過程中遇到問題：

1. **檢查此指南**：先查看故障排除章節
2. **查看 Colab 日誌**：檢查完整的錯誤訊息
3. **提供詳細資訊**：
   - Colab 環境資訊（GPU 型號等）
   - 完整的錯誤訊息
   - 執行到哪個步驟出現問題
4. **GitHub Issues**：在專案倉庫提出問題

---

🌟 **現在您已經掌握了完整的 Colab 部署流程，開始享受免費的 GPU 加速 2.5D 動畫生成服務吧！**