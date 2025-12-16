# FCN 詢價平台

基於機器學習的 FCN (Fixed Coupon Note) 結構票券詢價系統。

## 功能特色

- **單一報價**: 輸入股票組合與條件，快速取得 Coupon 預估
- **AI 智慧詢價**: 從股票池自動組合最佳報價方案
- **支援 1-4 檔股票組合**
- **IV 資料管理**: 上傳/刪除 Bloomberg IV 資料

## 專案結構

```
fcn-web-app/
├── backend/                    # 後端 API (Python FastAPI)
│   ├── main.py                 # 主程式 (API 端點 + 特徵工程)
│   ├── requirements.txt        # Python 依賴套件
│   ├── models/                 # ML 模型檔案
│   │   ├── fcn_model_histgradient_boosting_deep.pkl
│   │   └── model_features.txt
│   └── data/
│       └── iv_data/            # IV 資料 (Bloomberg 匯出的 xlsx)
│           └── YYYYMMDD.xlsx
│
└── frontend/                   # 前端 (React + TypeScript + Vite)
    ├── src/
    │   ├── components/         # React 元件
    │   ├── pages/              # 頁面
    │   ├── lib/                # 工具函式
    │   └── hooks/              # React Hooks
    ├── package.json            # Node.js 依賴
    └── vite.config.ts          # Vite 設定
```

## 環境需求

### 後端
- Python 3.10+
- 套件: FastAPI, uvicorn, pandas, numpy, scikit-learn, joblib, openpyxl

### 前端
- Node.js 18+
- npm 或 yarn

## 本地開發啟動

### 1. 後端

```bash
cd backend

# 建立虛擬環境 (建議)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安裝依賴
pip install -r requirements.txt

# 啟動伺服器 (port 8000)
python main.py
```

### 2. 前端

```bash
cd frontend

# 安裝依賴
npm install

# 啟動開發伺服器 (port 8080)
npm run dev
```

### 3. 開啟瀏覽器
- 前端: http://localhost:8080
- 後端 API: http://localhost:8000
- API 文件: http://localhost:8000/docs

## 正式部署

### 後端部署
1. 使用 Gunicorn + Uvicorn workers:
   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```
2. 或使用 Docker (需另建 Dockerfile)

### 前端部署
1. 建置靜態檔案:
   ```bash
   npm run build
   ```
2. 輸出在 `dist/` 資料夾，可部署到任何靜態檔案伺服器 (Nginx, Apache, CDN)

### API 代理設定
前端開發時會透過 Vite proxy 將 `/api` 請求轉發到後端。正式部署時需要在 Nginx 或其他 reverse proxy 設定:

```nginx
location /api {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | /api/health | 健康檢查 |
| GET | /api/stocks/available | 取得可用股票清單 |
| GET | /api/market/params | 取得市場參數 (SOFR, VIX) |
| GET | /api/dates/available | 取得可用定價日期 |
| POST | /api/fcn/calculate | 計算單一 FCN 報價 |
| POST | /api/fcn/batch-calculate | 批次計算 (AI 智慧詢價) |
| POST | /api/iv-data/upload | 上傳 IV 資料檔案 |
| DELETE | /api/iv-data/{date} | 刪除指定日期的 IV 資料 |

## IV 資料格式

上傳的 xlsx 檔案必須符合以下格式:
- 檔名: `YYYYMMDD.xlsx` (例如: 20251216.xlsx)
- 來源: Bloomberg 匯出的股票 IV 資料
- 必要欄位:
  - `BBG_Code` 或 `Unnamed: 0` - 股票代碼
  - `PX_LAST` - 最新價格
  - `3MO_PUT_IMP_VOL` - 3 個月 Put IV
  - `VOLATILITY_90D` - 90 天歷史波動率
  - `2M_CALL_IMP_VOL_25DELTA_DFLT` - 2M Call IV (25 Delta)
  - `2M_PUT_IMP_VOL_25DELTA_DFLT` - 2M Put IV (25 Delta)
  - `CORR_COEF` - 相關係數
  - `DIVIDEND_INDICATED_YIELD` - 股息殖利率

## 模型參數說明

### FCN 條件參數
| 參數 | 說明 | 範圍 |
|------|------|------|
| 承作期間 (Tenor) | 票券期限 | 2-12 個月 |
| 轉換價 (Strike) | 執行價格 | 50-100% |
| 上限價 (KO Barrier) | Knock-Out 價格 | 90-150% |
| 保護價 (KI Barrier) | Knock-In 價格 | 50-95% |
| 閉鎖期 (Non-call) | 不可提前贖回期間 | 1-12 個月 |
| 成本 (Cost) | 發行成本 | 95-100% |

### 特殊情況
- **No_KO**: 當閉鎖期 = 承作期間時，表示整個期間都不會被 KO

## 技術棧

- **前端**: React 18, TypeScript, Vite, TailwindCSS, shadcn/ui
- **後端**: FastAPI, scikit-learn (HistGradientBoosting)
- **ML 模型**: V8 版本
  - 測試集 R² = 0.85
  - 特徵數量: 159
  - 支援: 1-4 檔股票組合

## 模型更新

如需重新訓練模型，請參考專案根目錄的 `retrain_model_v8_optimal.py`。

訓練完成後，將生成的模型檔案複製到 `backend/models/`:
```bash
cp fcn_model_v8_optimal.pkl backend/models/fcn_model_histgradient_boosting_deep.pkl
cp model_features_v8.txt backend/models/model_features.txt
```

## 常見問題

### Q: 後端啟動失敗
A: 確認已安裝所有依賴套件，並確認 `models/` 和 `data/iv_data/` 資料夾存在且包含必要檔案。

### Q: 前端無法連接後端
A: 確認後端已在 port 8000 啟動，且 Vite proxy 設定正確。

### Q: 預測結果不準確
A: 確認使用的 IV 資料日期與實際定價日期相符。
