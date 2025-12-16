"""
FCN 報價預測 API
================
基於 FastAPI 的後端服務，整合我們訓練的機器學習模型
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
import numpy as np
import joblib
import os
import re
import shutil
from datetime import datetime

# 初始化 FastAPI
app = FastAPI(
    title="FCN 報價預測 API",
    description="使用機器學習模型預測 FCN (Fixed Coupon Note) 年化收益率",
    version="1.0.0"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發環境允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 全域變數和模型載入
# ============================================================================

MODEL_PATH = "models/fcn_model_histgradient_boosting_deep.pkl"
FEATURES_PATH = "models/model_features.txt"
IV_DATA_PATH = "data/iv_data"

model = None
feature_cols = []
iv_cache = {}
market_indices_cache = {}


def load_model():
    """載入模型和特徵列表"""
    global model, feature_cols

    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        print(f"✅ 模型載入成功: {MODEL_PATH}")
    else:
        print(f"❌ 找不到模型檔案: {MODEL_PATH}")
        model = None

    if os.path.exists(FEATURES_PATH):
        with open(FEATURES_PATH, 'r') as f:
            feature_cols = [line.strip() for line in f.readlines()]
        print(f"✅ 特徵列表載入成功: {len(feature_cols)} 個特徵")
    else:
        print(f"❌ 找不到特徵列表: {FEATURES_PATH}")
        feature_cols = []


def load_iv_data(date_key: str) -> pd.DataFrame:
    """載入指定日期的IV資料"""
    global iv_cache, market_indices_cache

    if date_key in iv_cache:
        return iv_cache[date_key]

    iv_file = os.path.join(IV_DATA_PATH, f'{date_key}.xlsx')

    if not os.path.exists(iv_file):
        raise FileNotFoundError(f"找不到IV資料檔案: {iv_file}")

    df_iv = pd.read_excel(iv_file)

    # 跳過標題行 (中文標題)
    df_iv = df_iv.iloc[1:].reset_index(drop=True)

    # 重命名列 - 根據實際 Bloomberg 數據列名
    column_mapping = {
        'Unnamed: 0': 'BBG_Code',
        'PX_LAST': 'PX_LAST',
        '3MO_PUT_IMP_VOL': 'PUT_IMP_VOL_3M',
        '2M_CALL_IMP_VOL_25DELTA_DFLT': 'CALL_IMP_VOL_2M_25D',
        '2M_PUT_IMP_VOL_25DELTA_DFLT': 'PUT_IMP_VOL_2M_25D',
        'HIST_PUT_IMP_VOL': 'HIST_PUT_IMP_VOL',
        'VOL_STDDEV': 'VOL_STDDEV',
        'VOLATILITY_90D': 'VOLATILITY_90D',
        'VOL_PERCENTILE': 'VOL_PERCENTILE',
        'CHG_PCT_1YR': 'CHG_PCT_1YR',
        'CORR_COEF': 'CORR_COEF',
        'DIVIDEND_INDICATED_YIELD': 'DIVIDEND_YIELD'
    }
    df_iv = df_iv.rename(columns=column_mapping)

    # 清理 BBG_Code - 移除 " Equity" 後綴
    if 'BBG_Code' in df_iv.columns:
        df_iv['BBG_Code'] = df_iv['BBG_Code'].astype(str).str.replace(' Equity', '', regex=False)
        df_iv['BBG_Code'] = df_iv['BBG_Code'].str.replace(' US', '', regex=False)

    # 轉換數值列
    numeric_cols = ['PX_LAST', 'PUT_IMP_VOL_3M', 'CALL_IMP_VOL_2M_25D',
                    'PUT_IMP_VOL_2M_25D', 'HIST_PUT_IMP_VOL', 'VOL_STDDEV',
                    'VOLATILITY_90D', 'VOL_PERCENTILE', 'CHG_PCT_1YR',
                    'CORR_COEF', 'DIVIDEND_YIELD']
    for col in numeric_cols:
        if col in df_iv.columns:
            df_iv[col] = pd.to_numeric(df_iv[col], errors='coerce')

    # 提取市場指數 (SOFR, VIX 等)
    market_indices = {'SOFR_RATE': 5.0, 'VIX_INDEX': 15.0}  # 預設值
    for _, row in df_iv.iterrows():
        code = str(row['BBG_Code'])
        price = safe_float(row['PX_LAST'])
        if price is not None:
            if 'SOFRRATE' in code or 'SOFR' in code:
                market_indices['SOFR_RATE'] = price
            elif 'VIX' in code:
                market_indices['VIX_INDEX'] = price
    market_indices_cache[date_key] = market_indices

    iv_cache[date_key] = df_iv
    return df_iv


def get_market_indices(date_key: str) -> dict:
    """取得指定日期的市場指數"""
    if date_key not in market_indices_cache:
        load_iv_data(date_key)
    return market_indices_cache.get(date_key, {'SOFR_RATE': 5.0, 'VIX_INDEX': 15.0})


def get_available_dates() -> List[str]:
    """取得可用的IV資料日期"""
    if not os.path.exists(IV_DATA_PATH):
        return []

    dates = []
    for f in os.listdir(IV_DATA_PATH):
        if f.endswith('.xlsx'):
            dates.append(f.replace('.xlsx', ''))
    return sorted(dates, reverse=True)


def safe_float(value) -> float | None:
    """安全轉換為 float，處理 NaN 和無效值"""
    if pd.isna(value):
        return None
    try:
        f = float(value)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def get_available_stocks(date_key: str) -> List[dict]:
    """取得指定日期可用的股票清單"""
    try:
        df_iv = load_iv_data(date_key)
        stocks = []
        for _, row in df_iv.iterrows():
            code = row['BBG_Code']
            # 過濾掉無效的股票代碼
            if not code or code == 'nan' or 'Index' in str(code):
                continue
            # 過濾掉沒有價格的記錄
            price = safe_float(row['PX_LAST'])
            if price is None:
                continue
            stocks.append({
                'code': code,
                'price': price,
                'vol90d': safe_float(row['VOLATILITY_90D']),
                'iv': safe_float(row['PUT_IMP_VOL_3M'])
            })
        return stocks
    except Exception as e:
        print(f"Error loading stocks: {e}")
        return []


# ============================================================================
# Pydantic 模型
# ============================================================================

class FCNRequest(BaseModel):
    stocks: List[str] = Field(..., min_items=1, max_items=4, description="股票代碼列表(最多4檔)")
    period: int = Field(..., ge=2, le=12, description="承作期間(月)")
    strikePrice: float = Field(..., ge=50, le=100, description="轉換價(%)")
    knockOutPrice: float = Field(..., ge=90, le=150, description="上限價(%)")
    knockInPrice: float = Field(..., ge=50, le=95, description="保護價(%)")
    kiType: str = Field(default="EKI", description="KI類型(AKI/EKI)")
    customFeeRate: float = Field(default=99.0, ge=95, le=100, description="成本(%)")
    pricingDate: Optional[str] = Field(default=None, description="定價日期(YYYYMMDD)")
    nonCallPeriods: Optional[int] = Field(default=1, ge=1, le=12, description="閉鎖期(月)")


class BatchFCNRequest(BaseModel):
    """批次報價請求 - 用於 AI 智慧詢價"""
    stockPool: List[str] = Field(..., min_items=1, max_items=20, description="股票池(最多20檔)")
    basketSizes: List[int] = Field(..., min_items=1, description="組合大小(1-4)")
    period: int = Field(..., ge=2, le=12, description="承作期間(月)")
    strikePrice: float = Field(..., ge=50, le=100, description="轉換價(%)")
    knockOutPrice: float = Field(..., ge=90, le=150, description="上限價(%)")
    knockInPrice: float = Field(..., ge=50, le=95, description="保護價(%)")
    kiType: str = Field(default="EKI", description="KI類型(AKI/EKI)")
    customFeeRate: float = Field(default=99.0, ge=95, le=100, description="成本(%)")
    nonCallPeriods: Optional[int] = Field(default=1, ge=1, le=12, description="閉鎖期(月)")
    pricingDate: Optional[str] = Field(default=None, description="定價日期(YYYYMMDD)")


class FCNResponse(BaseModel):
    annualized_yield: float
    calibrated_yield: Optional[float] = None
    model_used: str
    has_calibration: bool
    input_params: dict
    market_params: dict
    stock_info: dict


class StockDetailsRequest(BaseModel):
    symbols: List[str]


# ============================================================================
# 特徵工程函數
# ============================================================================

def compute_features(input_data: dict, iv_data_list: list) -> pd.DataFrame:
    """計算所有特徵"""
    features = {}

    # 基本FCN條件特徵
    features['Strike (%)'] = input_data['strike']
    features['KO Barrier (%)'] = input_data['ko_barrier']
    features['KI Barrier (%)'] = input_data['ki_barrier']
    features['Tenor (m)'] = input_data['tenor']
    features['Non-call Periods (m)'] = input_data.get('non_call_periods', 1)
    features['Cost (%)'] = input_data['cost']
    features['Barrier_Type_AKI'] = 1 if input_data['barrier_type'] == 'AKI' else 0

    # No KO Flag (當 Non-call == Tenor 時，不會觸發 KO)
    features['No_KO_Flag'] = 1 if features['Non-call Periods (m)'] == input_data['tenor'] else 0

    # No_KO 交互特徵 (V4 新增)
    no_ko = features['No_KO_Flag']
    features['No_KO_Tenor_Interaction'] = no_ko * input_data['tenor']
    features['No_KO_KI_Interaction'] = no_ko * input_data['ki_barrier']
    features['No_KO_Strike_Interaction'] = no_ko * input_data['strike']

    # 費用特徵
    features['Fee'] = 100 - input_data['cost']
    features['Annualized_Fee'] = features['Fee'] / input_data['tenor'] * 12

    # 時間特徵
    features['Tenor_Sqrt'] = np.sqrt(input_data['tenor'])
    features['Tenor_Squared'] = input_data['tenor'] ** 2
    features['Callable_Period'] = input_data['tenor'] - features['Non-call Periods (m)']
    features['Callable_Ratio'] = features['Callable_Period'] / input_data['tenor']
    features['NonCall_Ratio'] = features['Non-call Periods (m)'] / input_data['tenor']

    # 障礙價特徵
    features['KO_Strike_Distance'] = input_data['ko_barrier'] - input_data['strike']
    features['Strike_KI_Distance'] = input_data['strike'] - input_data['ki_barrier']
    features['KO_KI_Range'] = input_data['ko_barrier'] - input_data['ki_barrier']
    features['KI_Strike_Ratio'] = input_data['ki_barrier'] / input_data['strike']
    features['KO_Strike_Ratio'] = input_data['ko_barrier'] / input_data['strike']
    features['KI_Distance_Pct'] = input_data['strike'] - input_data['ki_barrier']
    features['KO_Distance_Pct'] = input_data['ko_barrier'] - input_data['strike']

    # Basket特徵
    basket_size = len([d for d in iv_data_list if d is not None])
    features['Basket_Size'] = basket_size
    features['Num_Underlyings'] = basket_size
    features['Basket_Complexity_Factor'] = basket_size / 3.0

    # 原始 IV 欄位列表
    iv_cols = ['PX_LAST', 'PUT_IMP_VOL_3M', 'CALL_IMP_VOL_2M_25D', 'PUT_IMP_VOL_2M_25D',
               'HIST_PUT_IMP_VOL', 'VOL_STDDEV', 'VOLATILITY_90D', 'VOL_PERCENTILE',
               'CHG_PCT_1YR', 'CORR_COEF', 'DIVIDEND_YIELD']

    # V8: 先生成原始 IV 欄位 (PUT_IMP_VOL_3M, PUT_IMP_VOL_3M_2, etc.)
    max_stocks = 4
    for i in range(max_stocks):
        suffix = '' if i == 0 else f'_{i+1}'
        for col in iv_cols:
            col_name = f'{col}{suffix}'
            if i < len(iv_data_list) and iv_data_list[i] is not None:
                features[col_name] = iv_data_list[i].get(col, np.nan)
            else:
                features[col_name] = np.nan

    # V8: 按 PUT_IMP_VOL_3M 降冪排序生成 _Rank_ 欄位
    # 收集每個股票的 IV 值和索引
    iv_pairs = []
    for i in range(max_stocks):
        suffix = '' if i == 0 else f'_{i+1}'
        iv_val = features.get(f'PUT_IMP_VOL_3M{suffix}', np.nan)
        if pd.notna(iv_val):
            iv_pairs.append((i, iv_val))
        else:
            iv_pairs.append((i, -np.inf))

    # 按 IV 降冪排序
    sorted_pairs = sorted(iv_pairs, key=lambda x: x[1], reverse=True)
    sorted_indices = [p[0] for p in sorted_pairs]

    # 生成排序後的特徵 (_Rank_1, _Rank_2, etc.)
    for col in iv_cols:
        for rank in range(max_stocks):
            rank_col = f'{col}_Rank_{rank+1}'
            orig_idx = sorted_indices[rank]
            orig_suffix = '' if orig_idx == 0 else f'_{orig_idx+1}'
            features[rank_col] = features.get(f'{col}{orig_suffix}', np.nan)

    # IV Skew 和 Premium - 原始版本 (IV_Skew_1, IV_Skew_2, etc.)
    for i in range(max_stocks):
        suffix = '' if i == 0 else f'_{i+1}'
        put_iv = features.get(f'PUT_IMP_VOL_2M_25D{suffix}', np.nan)
        call_iv = features.get(f'CALL_IMP_VOL_2M_25D{suffix}', np.nan)
        hist_iv = features.get(f'VOLATILITY_90D{suffix}', np.nan)
        iv_3m = features.get(f'PUT_IMP_VOL_3M{suffix}', np.nan)

        if pd.notna(put_iv) and pd.notna(call_iv):
            features[f'IV_Skew_{i+1}'] = put_iv - call_iv
        else:
            features[f'IV_Skew_{i+1}'] = np.nan

        if pd.notna(iv_3m) and pd.notna(hist_iv) and hist_iv != 0:
            features[f'IV_Premium_{i+1}'] = (iv_3m - hist_iv) / hist_iv
        else:
            features[f'IV_Premium_{i+1}'] = np.nan

    # IV Skew 和 Premium - 排序版本 (IV_Skew_Rank_1, etc.)
    for rank in range(max_stocks):
        orig_idx = sorted_indices[rank]
        features[f'IV_Skew_Rank_{rank+1}'] = features.get(f'IV_Skew_{orig_idx+1}', np.nan)
        features[f'IV_Premium_Rank_{rank+1}'] = features.get(f'IV_Premium_{orig_idx+1}', np.nan)

    # Basket聚合特徵
    iv_values = [d.get('PUT_IMP_VOL_3M') for d in iv_data_list if d and pd.notna(d.get('PUT_IMP_VOL_3M'))]
    hv_values = [d.get('VOLATILITY_90D') for d in iv_data_list if d and pd.notna(d.get('VOLATILITY_90D'))]
    corr_values = [d.get('CORR_COEF') for d in iv_data_list if d and pd.notna(d.get('CORR_COEF'))]

    # V8: IV 聚合特徵 (使用 Basket_Worst_IV/Best_IV 命名)
    features['Basket_Worst_IV'] = max(iv_values) if iv_values else np.nan
    features['Basket_Best_IV'] = min(iv_values) if iv_values else np.nan
    features['Basket_IV_Range'] = (max(iv_values) - min(iv_values)) if len(iv_values) >= 2 else 0
    features['Basket_Avg_IV'] = np.mean(iv_values) if iv_values else np.nan

    # HV 聚合特徵
    features['Basket_Worst_HV'] = max(hv_values) if hv_values else np.nan
    features['Basket_Best_HV'] = min(hv_values) if hv_values else np.nan
    features['Basket_Avg_HV'] = np.mean(hv_values) if hv_values else np.nan

    # 相關係數聚合特徵
    features['Basket_Avg_Corr'] = np.mean(corr_values) if corr_values else np.nan
    features['Basket_Min_Corr'] = min(corr_values) if corr_values else np.nan
    features['Max_Correlation'] = max(corr_values) if corr_values else np.nan
    features['Min_Correlation'] = min(corr_values) if corr_values else np.nan

    skew_values = [features.get(f'IV_Skew_{i+1}') for i in range(basket_size)
                   if pd.notna(features.get(f'IV_Skew_{i+1}'))]
    premium_values = [features.get(f'IV_Premium_{i+1}') for i in range(basket_size)
                      if pd.notna(features.get(f'IV_Premium_{i+1}'))]

    features['Basket_Avg_Skew'] = np.mean(skew_values) if skew_values else np.nan
    features['Basket_Max_Skew'] = max(skew_values) if skew_values else np.nan
    features['Basket_Avg_IV_Premium'] = np.mean(premium_values) if premium_values else np.nan
    features['Basket_Max_IV_Premium'] = max(premium_values) if premium_values else np.nan

    if iv_values and hv_values:
        features['IV_HV_Ratio'] = np.mean(iv_values) / np.mean(hv_values)
    else:
        features['IV_HV_Ratio'] = np.nan

    # 風險評分特徵 - V8 使用 Basket_Worst_IV
    rank_1_iv = features.get('PUT_IMP_VOL_3M_Rank_1', np.nan)
    worst_iv = features.get('Basket_Worst_IV', np.nan)

    if pd.notna(worst_iv):
        # V8: 使用 worst_iv 計算 Annualized_Vol_Factor
        features['Annualized_Vol_Factor'] = worst_iv / 100 * np.sqrt(input_data['tenor'] / 12)

        if features['Annualized_Vol_Factor'] > 0:
            features['KI_Distance_Std'] = features['KI_Distance_Pct'] / 100 / features['Annualized_Vol_Factor']
            features['KO_Distance_Std'] = features['KO_Distance_Pct'] / 100 / features['Annualized_Vol_Factor']
            features['KI_Distance_Std_Sorted'] = features['KI_Distance_Std']
        else:
            features['KI_Distance_Std'] = np.nan
            features['KO_Distance_Std'] = np.nan
            features['KI_Distance_Std_Sorted'] = np.nan

        features['Annualized_Vol'] = features['Basket_Avg_IV'] * np.sqrt(input_data['tenor'] / 12) if pd.notna(features['Basket_Avg_IV']) else np.nan

        if pd.notna(features['Basket_Avg_Corr']) and basket_size > 1:
            features['Corr_Adjusted_IV'] = worst_iv * (1 + 0.1 * (basket_size - 1) * (1 - features['Basket_Avg_Corr']))
        else:
            features['Corr_Adjusted_IV'] = worst_iv

        # V8: 用 worst_iv 的平均值 (約 43.5) 作為基準
        mean_worst_iv = 43.5
        features['KI_Risk_Score'] = (worst_iv / mean_worst_iv) * (input_data['ki_barrier'] / 100)
        features['Basket_Risk_Score'] = features['KI_Risk_Score'] * (1 + 0.2 * (basket_size - 1))

        if pd.notna(features['Basket_Avg_Corr']) and basket_size > 1:
            features['Basket_Risk_Score'] *= (1 + 0.1 * (1 - features['Basket_Avg_Corr']))

        # V8: 用 rank_1_iv 計算 Risk_Score_Sorted (如果可用)
        if pd.notna(rank_1_iv):
            mean_rank1_iv = 52.4
            features['Risk_Score_Sorted'] = (rank_1_iv / mean_rank1_iv) * (input_data['ki_barrier'] / 100) * (1 + 0.2 * (basket_size - 1))
        else:
            features['Risk_Score_Sorted'] = features['KI_Risk_Score'] * (1 + 0.2 * (basket_size - 1))
    else:
        for key in ['Annualized_Vol_Factor', 'KI_Distance_Std', 'KO_Distance_Std',
                    'KI_Distance_Std_Sorted', 'Annualized_Vol', 'Corr_Adjusted_IV',
                    'KI_Risk_Score', 'Basket_Risk_Score', 'Risk_Score_Sorted']:
            features[key] = np.nan

    features['Return_Potential'] = (input_data['ko_barrier'] / 100) * (input_data['tenor'] / 12)

    # No_KO 交互特徵
    features['No_KO_Basket_Interaction'] = features['No_KO_Flag'] * basket_size

    return pd.DataFrame([features])


# ============================================================================
# API 端點
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """應用啟動時載入模型"""
    load_model()


@app.get("/api/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "model_available": model is not None,
        "feature_count": len(feature_cols),
        "available_dates": get_available_dates()[:5]
    }


@app.get("/api/stocks/available")
async def get_stocks():
    """取得可用股票清單"""
    dates = get_available_dates()
    if not dates:
        raise HTTPException(status_code=404, detail="沒有可用的IV資料")

    latest_date = dates[0]
    stocks = get_available_stocks(latest_date)
    return stocks


@app.get("/api/market/params")
async def get_market_params():
    """取得市場參數 (SOFR, VIX)"""
    dates = get_available_dates()
    if not dates:
        raise HTTPException(status_code=404, detail="沒有可用的IV資料")

    latest_date = dates[0]
    market_data = get_market_indices(latest_date)
    return market_data


@app.post("/api/stocks/details")
async def get_stock_details(request: StockDetailsRequest):
    """取得股票詳細資訊"""
    dates = get_available_dates()
    if not dates:
        raise HTTPException(status_code=404, detail="沒有可用的IV資料")

    latest_date = dates[0]
    df_iv = load_iv_data(latest_date)

    results = []
    for symbol in request.symbols:
        stock_data = df_iv[df_iv['BBG_Code'] == symbol]
        if len(stock_data) > 0:
            row = stock_data.iloc[0]
            results.append({
                'symbol': symbol,
                'currentPrice': safe_float(row['PX_LAST']),
                'vol_90d': safe_float(row['VOLATILITY_90D']),
                'iv': safe_float(row['PUT_IMP_VOL_3M'])
            })

    return results


@app.post("/api/fcn/calculate", response_model=FCNResponse)
async def calculate_fcn(request: FCNRequest):
    """計算FCN收益率"""
    if model is None:
        raise HTTPException(status_code=500, detail="模型未載入")

    # 取得定價日期
    dates = get_available_dates()
    if not dates:
        raise HTTPException(status_code=404, detail="沒有可用的IV資料")

    pricing_date = request.pricingDate if request.pricingDate else dates[0]

    # 驗證輸入
    if request.knockInPrice >= request.strikePrice:
        raise HTTPException(status_code=400, detail="保護價必須低於轉換價")
    if request.knockOutPrice <= request.strikePrice:
        raise HTTPException(status_code=400, detail="上限價必須高於轉換價")

    try:
        # 載入IV資料
        df_iv = load_iv_data(pricing_date)

        # 取得各標的的IV資料
        iv_data_list = []
        stock_info = {}

        for bbg in request.stocks:
            stock_data = df_iv[df_iv['BBG_Code'] == bbg]
            if len(stock_data) > 0:
                row = stock_data.iloc[0].to_dict()
                iv_data_list.append(row)
                stock_info[bbg] = {
                    'price': safe_float(row['PX_LAST']),
                    'put_iv_3m': safe_float(row['PUT_IMP_VOL_3M']),
                    'vol_90d': safe_float(row['VOLATILITY_90D'])
                }
            else:
                raise HTTPException(status_code=400, detail=f"找不到股票 {bbg} 的IV資料")

        # 按PUT_IMP_VOL_3M降冪排序
        iv_data_list.sort(key=lambda x: x.get('PUT_IMP_VOL_3M', 0) or 0, reverse=True)

        # 填補到4個 (支援最多4檔股票)
        while len(iv_data_list) < 4:
            iv_data_list.append(None)

        # 準備輸入資料
        non_call = request.nonCallPeriods if request.nonCallPeriods else 1
        # 確保 non_call 不超過 tenor
        non_call = min(non_call, request.period)

        input_data = {
            'strike': request.strikePrice,
            'ko_barrier': request.knockOutPrice,
            'ki_barrier': request.knockInPrice,
            'tenor': request.period,
            'cost': request.customFeeRate,
            'barrier_type': request.kiType,
            'non_call_periods': non_call
        }

        # 計算特徵
        features_df = compute_features(input_data, iv_data_list)

        # 確保特徵順序正確
        X = features_df.reindex(columns=feature_cols)

        # 預測
        predicted_coupon = safe_float(model.predict(X)[0])
        if predicted_coupon is None:
            predicted_coupon = 0.0

        return FCNResponse(
            annualized_yield=predicted_coupon,
            calibrated_yield=predicted_coupon,
            model_used="HistGradient Boosting (R²=0.92)",
            has_calibration=True,
            input_params={
                'tenure_months': request.period,
                'strike_pct': request.strikePrice,
                'ko_barrier_pct': request.knockOutPrice,
                'ki_barrier_pct': request.knockInPrice,
                'ki_type': request.kiType,
                'cost_pct': request.customFeeRate,
                'non_call_periods': non_call,
                'no_ko': non_call == request.period
            },
            market_params={
                'pricing_date': pricing_date,
                **get_market_indices(pricing_date)
            },
            stock_info=stock_info
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"計算錯誤: {str(e)}")


@app.get("/api/dates/available")
async def get_dates():
    """取得可用的定價日期"""
    return get_available_dates()


# ============================================================================
# IV 資料上傳 API
# ============================================================================

@app.post("/api/iv-data/upload")
async def upload_iv_data(file: UploadFile = File(...)):
    """
    上傳 IV 資料檔案 (xlsx 格式)
    檔案名稱必須是日期格式，例如 20251212.xlsx
    """
    global iv_cache, market_indices_cache

    # 驗證檔案類型
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="只接受 .xlsx 格式的檔案")

    # 驗證檔案名稱格式 (YYYYMMDD.xlsx)
    filename_without_ext = file.filename.replace('.xlsx', '')
    if not re.match(r'^\d{8}$', filename_without_ext):
        raise HTTPException(
            status_code=400,
            detail="檔案名稱必須是日期格式 (YYYYMMDD.xlsx)，例如 20251212.xlsx"
        )

    # 驗證日期有效性
    try:
        datetime.strptime(filename_without_ext, '%Y%m%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的日期格式")

    # 確保目錄存在
    os.makedirs(IV_DATA_PATH, exist_ok=True)

    # 儲存檔案
    file_path = os.path.join(IV_DATA_PATH, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"儲存檔案失敗: {str(e)}")

    # 清除快取以載入新資料
    if filename_without_ext in iv_cache:
        del iv_cache[filename_without_ext]
    if filename_without_ext in market_indices_cache:
        del market_indices_cache[filename_without_ext]

    # 驗證檔案可以正確載入
    try:
        df_iv = load_iv_data(filename_without_ext)
        stocks = get_available_stocks(filename_without_ext)
        stock_count = len(stocks)
    except Exception as e:
        # 如果載入失敗，刪除檔案
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"檔案格式錯誤: {str(e)}")

    return {
        "message": "上傳成功",
        "filename": file.filename,
        "date": filename_without_ext,
        "stock_count": stock_count,
        "available_dates": get_available_dates()
    }


@app.delete("/api/iv-data/{date}")
async def delete_iv_data(date: str):
    """刪除指定日期的 IV 資料"""
    global iv_cache, market_indices_cache

    # 驗證日期格式
    if not re.match(r'^\d{8}$', date):
        raise HTTPException(status_code=400, detail="無效的日期格式")

    file_path = os.path.join(IV_DATA_PATH, f"{date}.xlsx")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="找不到該日期的資料")

    try:
        os.remove(file_path)
        # 清除快取
        if date in iv_cache:
            del iv_cache[date]
        if date in market_indices_cache:
            del market_indices_cache[date]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除失敗: {str(e)}")

    return {
        "message": "刪除成功",
        "date": date,
        "available_dates": get_available_dates()
    }


# ============================================================================
# 批次報價 API (AI 智慧詢價)
# ============================================================================

from itertools import combinations as iter_combinations

@app.post("/api/fcn/batch-calculate")
async def batch_calculate_fcn(request: BatchFCNRequest):
    """
    批次計算 FCN 收益率 - 用於 AI 智慧詢價
    根據股票池和組合大小，產生所有排列組合的報價
    """
    if model is None:
        raise HTTPException(status_code=500, detail="模型未載入")

    # 取得定價日期
    dates = get_available_dates()
    if not dates:
        raise HTTPException(status_code=404, detail="沒有可用的IV資料")

    pricing_date = request.pricingDate if request.pricingDate else dates[0]

    # 驗證輸入
    if request.knockInPrice >= request.strikePrice:
        raise HTTPException(status_code=400, detail="保護價必須低於轉換價")
    if request.knockOutPrice <= request.strikePrice:
        raise HTTPException(status_code=400, detail="上限價必須高於轉換價")

    # 驗證 basketSizes
    valid_sizes = [s for s in request.basketSizes if 1 <= s <= 4]
    if not valid_sizes:
        raise HTTPException(status_code=400, detail="組合大小必須在1-4之間")

    try:
        # 載入IV資料
        df_iv = load_iv_data(pricing_date)

        # 取得所有股票的IV資料
        stock_iv_data = {}
        stock_info = {}

        for bbg in request.stockPool:
            stock_data = df_iv[df_iv['BBG_Code'] == bbg]
            if len(stock_data) > 0:
                row = stock_data.iloc[0].to_dict()
                stock_iv_data[bbg] = row
                stock_info[bbg] = {
                    'price': safe_float(row['PX_LAST']),
                    'put_iv_3m': safe_float(row['PUT_IMP_VOL_3M']),
                    'vol_90d': safe_float(row['VOLATILITY_90D'])
                }

        # 只使用有IV資料的股票
        valid_stocks = list(stock_iv_data.keys())
        if len(valid_stocks) == 0:
            raise HTTPException(status_code=400, detail="股票池中沒有可用的IV資料")

        # 準備基礎輸入資料
        non_call = request.nonCallPeriods if request.nonCallPeriods else 1
        non_call = min(non_call, request.period)

        base_input = {
            'strike': request.strikePrice,
            'ko_barrier': request.knockOutPrice,
            'ki_barrier': request.knockInPrice,
            'tenor': request.period,
            'cost': request.customFeeRate,
            'barrier_type': request.kiType,
            'non_call_periods': non_call
        }

        # 產生所有組合並計算
        quotes = []
        quote_id = 0

        for basket_size in valid_sizes:
            if basket_size > len(valid_stocks):
                continue

            # 產生所有 C(n, k) 組合
            for combo in iter_combinations(valid_stocks, basket_size):
                combo_list = list(combo)

                # 取得這個組合的 IV 資料
                iv_data_list = [stock_iv_data[s] for s in combo_list]

                # 按 PUT_IMP_VOL_3M 降冪排序
                iv_data_list.sort(key=lambda x: x.get('PUT_IMP_VOL_3M', 0) or 0, reverse=True)

                # 填補到4個
                while len(iv_data_list) < 4:
                    iv_data_list.append(None)

                # 計算特徵
                features_df = compute_features(base_input, iv_data_list)

                # 確保特徵順序正確
                X = features_df.reindex(columns=feature_cols)

                # 預測
                predicted_coupon = safe_float(model.predict(X)[0])
                if predicted_coupon is None:
                    predicted_coupon = 0.0

                # 計算距KI距離 (使用最高IV股票)
                max_iv = max([stock_info[s]['put_iv_3m'] or 0 for s in combo_list])
                distance_to_ki = request.strikePrice - request.knockInPrice

                # 決定風險等級
                if request.knockInPrice < 60 and request.strikePrice > 85:
                    risk_level = "low"
                elif request.knockInPrice > 70 or request.strikePrice < 70:
                    risk_level = "high"
                else:
                    risk_level = "medium"

                quotes.append({
                    'id': f"quote-{quote_id}",
                    'stocks': combo_list,
                    'basketSize': basket_size,
                    'couponRate': round(predicted_coupon, 2),
                    'distanceToKI': round(distance_to_ki, 1),
                    'maxIV': round(max_iv, 1) if max_iv else None,
                    'riskLevel': risk_level,
                    'stockInfo': {s: stock_info[s] for s in combo_list}
                })
                quote_id += 1

        # 按 couponRate 降冪排序
        quotes.sort(key=lambda x: x['couponRate'], reverse=True)

        # 計算 yieldBoost (相對於單一標的的增益)
        avg_coupon_by_size = {}
        for size in valid_sizes:
            size_quotes = [q for q in quotes if q['basketSize'] == size]
            if size_quotes:
                avg_coupon_by_size[size] = sum(q['couponRate'] for q in size_quotes) / len(size_quotes)

        min_size = min(valid_sizes)
        for quote in quotes:
            if quote['basketSize'] > min_size and min_size in avg_coupon_by_size:
                quote['yieldBoost'] = round(
                    avg_coupon_by_size.get(quote['basketSize'], 0) - avg_coupon_by_size[min_size],
                    2
                )
            else:
                quote['yieldBoost'] = None

        return {
            'quotes': quotes,
            'totalCount': len(quotes),
            'pricingDate': pricing_date,
            'params': {
                'period': request.period,
                'strikePrice': request.strikePrice,
                'knockOutPrice': request.knockOutPrice,
                'knockInPrice': request.knockInPrice,
                'kiType': request.kiType,
                'nonCallPeriods': non_call,
                'noKO': non_call == request.period
            },
            'marketParams': get_market_indices(pricing_date)
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"批次計算錯誤: {str(e)}")


# ============================================================================
# 啟動伺服器
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
