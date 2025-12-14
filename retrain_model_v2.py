"""
FCN Model Retraining Script V2
==============================
- 使用最新的 FCN資料表.xlsx (包含 2025/12/12 新資料)
- 優化高 IV 股票預測 (IV > 80)
- 支援 Non-call Periods 特徵
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import HistGradientBoostingRegressor
import joblib
import warnings
import os
warnings.filterwarnings('ignore')

print("=" * 80)
print("FCN 模型重新訓練 V2")
print("=" * 80)

# ============================================================================
# 1. 載入並合併資料
# ============================================================================
print("\n" + "=" * 80)
print("1. 載入資料")
print("=" * 80)

# 載入 FCN 資料表
df_fcn = pd.read_excel('FCN資料表.xlsx')
print(f"FCN 資料表: {df_fcn.shape}")

# 檢查新資料
new_data_count = df_fcn['Pricing Date'].astype(str).str.contains('2025-12-12|2025/12/12|20251212', na=False).sum()
print(f"2025/12/12 新資料: {new_data_count} 筆")

# 顯示 Non-call 分佈
print(f"\n【Non-call Periods 分佈】")
print(df_fcn['Non-call Periods (m)'].value_counts().head(10))

# ============================================================================
# 2. 載入 IV 資料並合併
# ============================================================================
print("\n" + "=" * 80)
print("2. 載入 IV 資料")
print("=" * 80)

# 找到所有 IV 資料檔案
iv_data_path = 'iv_data'
if not os.path.exists(iv_data_path):
    iv_data_path = 'fcn-web-app/backend/data/iv_data'

iv_files = [f for f in os.listdir(iv_data_path) if f.endswith('.xlsx') and not f.startswith('~$')]
print(f"找到 {len(iv_files)} 個 IV 資料檔案")

# 載入所有 IV 資料
all_iv_data = {}
for iv_file in iv_files:
    date_key = iv_file.replace('.xlsx', '')
    df_iv = pd.read_excel(os.path.join(iv_data_path, iv_file))
    # 跳過標題行
    df_iv = df_iv.iloc[1:].reset_index(drop=True)
    df_iv = df_iv.rename(columns={'Unnamed: 0': 'BBG_Code'})
    # 清理代碼
    df_iv['BBG_Code'] = df_iv['BBG_Code'].astype(str).str.replace(' Equity', '', regex=False)
    df_iv['BBG_Code'] = df_iv['BBG_Code'].str.replace(' US', '', regex=False)
    all_iv_data[date_key] = df_iv

print(f"已載入 IV 資料日期: {list(all_iv_data.keys())}")

# ============================================================================
# 3. 資料合併與前處理
# ============================================================================
print("\n" + "=" * 80)
print("3. 資料合併與前處理")
print("=" * 80)

# 清理 FCN 資料
df = df_fcn.copy()

# 移除不需要的欄位
cols_to_drop = ['Unnamed: 17', 'BBG Code 4', 'BBG Code 5']
existing_cols_to_drop = [col for col in cols_to_drop if col in df.columns]
if existing_cols_to_drop:
    df = df.drop(existing_cols_to_drop, axis=1)

# 處理 Coupon 欄位
df['Coupon_Valid'] = (df['Coupon p.a. (%)'] != '-')
df['Coupon'] = df['Coupon p.a. (%)'].apply(lambda x: float(x) if x != '-' else np.nan)

# 只保留有效 Coupon
df = df[df['Coupon_Valid']].copy()
print(f"有效 Coupon 資料: {len(df)} 筆")

# 標的數量
df['Num_Underlyings'] = (
    df['BBG Code 1'].notna().astype(int) +
    df['BBG Code 2'].notna().astype(int) +
    df['BBG Code 3'].notna().astype(int)
)

# 轉換 Pricing Date 格式以便匹配 IV 資料
def get_date_key(date_val):
    """將日期轉換為 YYYYMMDD 格式"""
    try:
        if pd.isna(date_val):
            return None
        if isinstance(date_val, str):
            # 嘗試不同格式
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y']:
                try:
                    return pd.to_datetime(date_val, format=fmt).strftime('%Y%m%d')
                except:
                    continue
        return pd.to_datetime(date_val).strftime('%Y%m%d')
    except:
        return None

df['Date_Key'] = df['Pricing Date'].apply(get_date_key)

# 為每個標的合併 IV 資料
print("\n合併 IV 資料...")

iv_columns = ['PX_LAST', '3MO_PUT_IMP_VOL', '2M_CALL_IMP_VOL_25DELTA_DFLT',
              '2M_PUT_IMP_VOL_25DELTA_DFLT', 'HIST_PUT_IMP_VOL', 'VOL_STDDEV',
              'VOLATILITY_90D', 'VOL_PERCENTILE', 'CHG_PCT_1YR', 'CORR_COEF',
              'DIVIDEND_INDICATED_YIELD']

iv_rename = {
    '3MO_PUT_IMP_VOL': 'PUT_IMP_VOL_3M',
    '2M_CALL_IMP_VOL_25DELTA_DFLT': 'CALL_IMP_VOL_2M_25D',
    '2M_PUT_IMP_VOL_25DELTA_DFLT': 'PUT_IMP_VOL_2M_25D',
    'DIVIDEND_INDICATED_YIELD': 'DIVIDEND_YIELD'
}

def get_iv_for_stock(row, stock_col, suffix=''):
    """取得特定股票的 IV 資料"""
    date_key = row.get('Date_Key')
    stock_code = row.get(stock_col)

    if pd.isna(date_key) or pd.isna(stock_code):
        return pd.Series({f'{iv_rename.get(col, col)}{suffix}': np.nan for col in iv_columns})

    # 清理股票代碼
    stock_code = str(stock_code).replace(' Equity', '').replace(' US', '').strip()

    # 查找 IV 資料
    iv_df = all_iv_data.get(date_key)
    if iv_df is None:
        # 找最近的日期
        available_dates = sorted(all_iv_data.keys(), reverse=True)
        for d in available_dates:
            if d <= date_key:
                iv_df = all_iv_data[d]
                break
        if iv_df is None and available_dates:
            iv_df = all_iv_data[available_dates[0]]

    if iv_df is None:
        return pd.Series({f'{iv_rename.get(col, col)}{suffix}': np.nan for col in iv_columns})

    # 查找股票
    stock_row = iv_df[iv_df['BBG_Code'] == stock_code]
    if len(stock_row) == 0:
        return pd.Series({f'{iv_rename.get(col, col)}{suffix}': np.nan for col in iv_columns})

    result = {}
    for col in iv_columns:
        new_col = f'{iv_rename.get(col, col)}{suffix}'
        if col in stock_row.columns:
            val = stock_row.iloc[0][col]
            try:
                result[new_col] = float(val) if pd.notna(val) else np.nan
            except:
                result[new_col] = np.nan
        else:
            result[new_col] = np.nan

    return pd.Series(result)

# 合併 BBG Code 1 的 IV
print("  處理 BBG Code 1...")
iv_1 = df.apply(lambda row: get_iv_for_stock(row, 'BBG Code 1', ''), axis=1)
df = pd.concat([df, iv_1], axis=1)

# 合併 BBG Code 2 的 IV
print("  處理 BBG Code 2...")
iv_2 = df.apply(lambda row: get_iv_for_stock(row, 'BBG Code 2', '_2'), axis=1)
df = pd.concat([df, iv_2], axis=1)

# 合併 BBG Code 3 的 IV
print("  處理 BBG Code 3...")
iv_3 = df.apply(lambda row: get_iv_for_stock(row, 'BBG Code 3', '_3'), axis=1)
df = pd.concat([df, iv_3], axis=1)

print(f"合併後資料形狀: {df.shape}")

# ============================================================================
# 4. 特徵工程
# ============================================================================
print("\n" + "=" * 80)
print("4. 特徵工程")
print("=" * 80)

# 4.1 費用特徵
df['Fee'] = 100 - df['Cost (%)']
df['Annualized_Fee'] = (df['Fee'] / df['Tenor (m)']) * 12

# 4.2 障礙價特徵
df['KO_Strike_Distance'] = df['KO Barrier (%)'] - df['Strike (%)']
df['Strike_KI_Distance'] = df['Strike (%)'] - df['KI Barrier (%)']
df['KO_KI_Range'] = df['KO Barrier (%)'] - df['KI Barrier (%)']
df['KI_Strike_Ratio'] = df['KI Barrier (%)'] / df['Strike (%)']
df['KO_Strike_Ratio'] = df['KO Barrier (%)'] / df['Strike (%)']
df['KI_Distance_Pct'] = df['Strike (%)'] - df['KI Barrier (%)']
df['KO_Distance_Pct'] = df['KO Barrier (%)'] - df['Strike (%)']

# 4.3 時間價值特徵
df['Tenor_Sqrt'] = np.sqrt(df['Tenor (m)'])
df['Tenor_Squared'] = df['Tenor (m)'] ** 2
df['Callable_Period'] = df['Tenor (m)'] - df['Non-call Periods (m)']
df['Callable_Ratio'] = df['Callable_Period'] / df['Tenor (m)']
df['NonCall_Ratio'] = df['Non-call Periods (m)'] / df['Tenor (m)']

# 4.4 Non-call == Tenor 特徵 (不會 KO 的情況)
df['No_KO_Flag'] = (df['Non-call Periods (m)'] == df['Tenor (m)']).astype(int)

# 4.5 Basket 特徵
df['Basket_Size'] = df['Num_Underlyings']

# Worst/Best IV
df['Basket_Worst_IV'] = df[['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']].max(axis=1, skipna=True)
df['Basket_Best_IV'] = df[['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']].min(axis=1, skipna=True)
df['Basket_IV_Range'] = df['Basket_Worst_IV'] - df['Basket_Best_IV']

# 平均 IV
def safe_mean(row, cols):
    values = [row[col] for col in cols if col in row.index and pd.notna(row[col])]
    return np.mean(values) if values else np.nan

iv_3m_cols = ['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']
hv_90d_cols = ['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3']
corr_cols = ['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3']

df['Basket_Avg_IV'] = df.apply(lambda row: safe_mean(row, iv_3m_cols), axis=1)
df['Basket_Avg_HV'] = df.apply(lambda row: safe_mean(row, hv_90d_cols), axis=1)
df['Basket_Avg_Corr'] = df.apply(lambda row: safe_mean(row, corr_cols), axis=1)

# 歷史波動率
df['Basket_Worst_HV'] = df[['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3']].max(axis=1, skipna=True)
df['Basket_Best_HV'] = df[['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3']].min(axis=1, skipna=True)

# 相關性
df['Basket_Min_Corr'] = df[['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3']].min(axis=1, skipna=True)
df['Max_Correlation'] = df[['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3']].max(axis=1, skipna=True)
df['Min_Correlation'] = df['Basket_Min_Corr']

# Basket 複雜度
df['Basket_Complexity_Factor'] = df['Basket_Size'] / 3.0

# 相關性調整 IV
df['Corr_Adjusted_IV'] = df['Basket_Worst_IV'].copy()
multi_asset_mask = (df['Basket_Size'] > 1) & (df['Basket_Avg_Corr'].notna())
df.loc[multi_asset_mask, 'Corr_Adjusted_IV'] = (
    df.loc[multi_asset_mask, 'Basket_Worst_IV'] *
    (1 + 0.1 * (df.loc[multi_asset_mask, 'Basket_Size'] - 1) *
     (1 - df.loc[multi_asset_mask, 'Basket_Avg_Corr']))
)

# 4.6 IV Skew 和 Premium
df['IV_Skew_1'] = df['PUT_IMP_VOL_2M_25D'] - df['CALL_IMP_VOL_2M_25D']
df['IV_Skew_2'] = df['PUT_IMP_VOL_2M_25D_2'] - df['CALL_IMP_VOL_2M_25D_2']
df['IV_Skew_3'] = df['PUT_IMP_VOL_2M_25D_3'] - df['CALL_IMP_VOL_2M_25D_3']

skew_cols = ['IV_Skew_1', 'IV_Skew_2', 'IV_Skew_3']
df['Basket_Avg_Skew'] = df.apply(lambda row: safe_mean(row, skew_cols), axis=1)
df['Basket_Max_Skew'] = df[skew_cols].max(axis=1, skipna=True)

df['IV_Premium_1'] = (df['PUT_IMP_VOL_3M'] - df['VOLATILITY_90D']) / df['VOLATILITY_90D']
df['IV_Premium_2'] = (df['PUT_IMP_VOL_3M_2'] - df['VOLATILITY_90D_2']) / df['VOLATILITY_90D_2']
df['IV_Premium_3'] = (df['PUT_IMP_VOL_3M_3'] - df['VOLATILITY_90D_3']) / df['VOLATILITY_90D_3']

premium_cols = ['IV_Premium_1', 'IV_Premium_2', 'IV_Premium_3']
df['Basket_Avg_IV_Premium'] = df.apply(lambda row: safe_mean(row, premium_cols), axis=1)
df['Basket_Max_IV_Premium'] = df[premium_cols].max(axis=1, skipna=True)

# 4.7 標準化距離
df['Annualized_Vol_Factor'] = df['Basket_Worst_IV'] / 100 * np.sqrt(df['Tenor (m)'] / 12)
df['KI_Distance_Std'] = df['KI_Distance_Pct'] / 100 / df['Annualized_Vol_Factor']
df['KO_Distance_Std'] = df['KO_Distance_Pct'] / 100 / df['Annualized_Vol_Factor']

# 4.8 IV 比率
df['IV_HV_Ratio'] = df['Basket_Avg_IV'] / df['Basket_Avg_HV']

# 4.9 風險評分
df['KI_Risk_Score'] = (df['Basket_Worst_IV'] / df['Basket_Worst_IV'].mean()) * (df['KI Barrier (%)'] / 100)
df['Return_Potential'] = (df['KO Barrier (%)'] / 100) * (df['Tenor (m)'] / 12)

df['Basket_Risk_Score'] = (
    (df['Basket_Worst_IV'] / df['Basket_Worst_IV'].mean()) *
    (df['KI Barrier (%)'] / 100) *
    (1 + 0.2 * (df['Basket_Size'] - 1))
)
df.loc[multi_asset_mask, 'Basket_Risk_Score'] = (
    df.loc[multi_asset_mask, 'Basket_Risk_Score'] *
    (1 + 0.1 * (1 - df.loc[multi_asset_mask, 'Basket_Avg_Corr']))
)

# 4.10 Barrier Type 編碼
df['Barrier_Type_AKI'] = (df['Barrier Type'] == 'AKI').astype(int)

# 4.11 年化波動率
df['Annualized_Vol'] = df['Basket_Avg_IV'] * np.sqrt(df['Tenor (m)'] / 12)

# 4.12 IV 排序特徵 (按 PUT_IMP_VOL_3M 降冪排序)
print("\n建立 IV 排序特徵...")

def get_iv_sort_indices(row):
    iv_values = [
        (0, row['PUT_IMP_VOL_3M'] if pd.notna(row.get('PUT_IMP_VOL_3M')) else -np.inf),
        (1, row.get('PUT_IMP_VOL_3M_2', np.nan) if pd.notna(row.get('PUT_IMP_VOL_3M_2')) else -np.inf),
        (2, row.get('PUT_IMP_VOL_3M_3', np.nan) if pd.notna(row.get('PUT_IMP_VOL_3M_3')) else -np.inf),
    ]
    sorted_indices = sorted(iv_values, key=lambda x: x[1], reverse=True)
    return [x[0] for x in sorted_indices]

sort_indices = df.apply(get_iv_sort_indices, axis=1)
df['_sort_idx_0'] = sort_indices.apply(lambda x: x[0])
df['_sort_idx_1'] = sort_indices.apply(lambda x: x[1])
df['_sort_idx_2'] = sort_indices.apply(lambda x: x[2])

# IV 欄位組
iv_groups = {
    'PUT_IMP_VOL_3M': ['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3'],
    'VOLATILITY_90D': ['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3'],
    'CALL_IMP_VOL_2M_25D': ['CALL_IMP_VOL_2M_25D', 'CALL_IMP_VOL_2M_25D_2', 'CALL_IMP_VOL_2M_25D_3'],
    'PUT_IMP_VOL_2M_25D': ['PUT_IMP_VOL_2M_25D', 'PUT_IMP_VOL_2M_25D_2', 'PUT_IMP_VOL_2M_25D_3'],
    'HIST_PUT_IMP_VOL': ['HIST_PUT_IMP_VOL', 'HIST_PUT_IMP_VOL_2', 'HIST_PUT_IMP_VOL_3'],
    'VOL_STDDEV': ['VOL_STDDEV', 'VOL_STDDEV_2', 'VOL_STDDEV_3'],
    'VOL_PERCENTILE': ['VOL_PERCENTILE', 'VOL_PERCENTILE_2', 'VOL_PERCENTILE_3'],
    'CHG_PCT_1YR': ['CHG_PCT_1YR', 'CHG_PCT_1YR_2', 'CHG_PCT_1YR_3'],
    'CORR_COEF': ['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3'],
    'DIVIDEND_YIELD': ['DIVIDEND_YIELD', 'DIVIDEND_YIELD_2', 'DIVIDEND_YIELD_3'],
    'PX_LAST': ['PX_LAST', 'PX_LAST_2', 'PX_LAST_3'],
}

for group_name, cols in iv_groups.items():
    if all(col in df.columns for col in cols[:1]):
        rank_cols = [f'{group_name}_Rank_{i+1}' for i in range(3)]
        for i, rank_col in enumerate(rank_cols):
            def get_sorted_value(row, original_cols=cols, idx_col=f'_sort_idx_{i}'):
                idx = int(row[idx_col])
                if idx < len(original_cols) and original_cols[idx] in row.index:
                    return row[original_cols[idx]]
                return np.nan
            df[rank_col] = df.apply(get_sorted_value, axis=1)

# IV Skew 和 Premium 排序版本
for i in range(3):
    put_col = f'PUT_IMP_VOL_2M_25D_Rank_{i+1}'
    call_col = f'CALL_IMP_VOL_2M_25D_Rank_{i+1}'
    if put_col in df.columns and call_col in df.columns:
        df[f'IV_Skew_Rank_{i+1}'] = df[put_col] - df[call_col]

    iv_col = f'PUT_IMP_VOL_3M_Rank_{i+1}'
    hv_col = f'VOLATILITY_90D_Rank_{i+1}'
    if iv_col in df.columns and hv_col in df.columns:
        df[f'IV_Premium_Rank_{i+1}'] = (df[iv_col] - df[hv_col]) / df[hv_col]

# 排序後的風險特徵
df['KI_Distance_Std_Sorted'] = (
    (df['Strike (%)'] - df['KI Barrier (%)']) / 100 /
    (df['PUT_IMP_VOL_3M_Rank_1'] / 100 * np.sqrt(df['Tenor (m)'] / 12))
)

df['Risk_Score_Sorted'] = (
    (df['PUT_IMP_VOL_3M_Rank_1'] / df['PUT_IMP_VOL_3M_Rank_1'].mean()) *
    (df['KI Barrier (%)'] / 100) *
    (1 + 0.2 * (df['Basket_Size'] - 1))
)

# 移除輔助欄位
df = df.drop(['_sort_idx_0', '_sort_idx_1', '_sort_idx_2'], axis=1)

print(f"特徵工程後資料形狀: {df.shape}")

# ============================================================================
# 5. 準備訓練資料
# ============================================================================
print("\n" + "=" * 80)
print("5. 準備訓練資料")
print("=" * 80)

target = 'Coupon'

# 排除欄位
exclude_cols = [
    'Coupon', 'Coupon p.a. (%)', 'Coupon_Valid',
    'Pricing Date', 'Date_Key',
    'BBG Code 1', 'BBG Code 2', 'BBG Code 3',
    'Product', 'Currency', 'KO Type', 'Barrier Type',
]

# 獲取所有數值型特徵
all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
feature_cols = [col for col in all_numeric_cols if col not in exclude_cols]

print(f"總特徵數: {len(feature_cols)}")

X = df[feature_cols].copy()
y = df[target].copy()

# 移除 NaN 目標值
valid_mask = y.notna()
X = X[valid_mask]
y = y[valid_mask]

print(f"有效樣本數: {len(y)}")

# 分析高 IV 樣本
high_iv_mask = df.loc[valid_mask, 'Basket_Worst_IV'] > 80
print(f"高 IV (>80) 樣本數: {high_iv_mask.sum()}")

# 分割資料
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"訓練集: {len(X_train)}, 測試集: {len(X_test)}")

# ============================================================================
# 6. 訓練模型
# ============================================================================
print("\n" + "=" * 80)
print("6. 訓練模型")
print("=" * 80)

# HistGradient Boosting (深層版本，優化高 IV)
print("\n【HistGradient Boosting (深層 + 優化)】")

model = HistGradientBoostingRegressor(
    max_iter=500,
    max_depth=15,
    learning_rate=0.05,
    min_samples_leaf=3,
    l2_regularization=0.1,
    random_state=42
)

model.fit(X_train, y_train)
y_pred = model.predict(X_test)

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"  RMSE: {rmse:.4f}")
print(f"  MAE:  {mae:.4f}")
print(f"  R²:   {r2:.4f}")

# 高 IV 樣本的表現
high_iv_test_mask = X_test['Basket_Worst_IV'] > 80 if 'Basket_Worst_IV' in X_test.columns else pd.Series([False] * len(X_test))
if high_iv_test_mask.sum() > 0:
    high_iv_rmse = np.sqrt(mean_squared_error(y_test[high_iv_test_mask], y_pred[high_iv_test_mask]))
    high_iv_r2 = r2_score(y_test[high_iv_test_mask], y_pred[high_iv_test_mask])
    print(f"\n高 IV (>80) 表現:")
    print(f"  樣本數: {high_iv_test_mask.sum()}")
    print(f"  RMSE: {high_iv_rmse:.4f}")
    print(f"  R²:   {high_iv_r2:.4f}")

# ============================================================================
# 7. 交叉驗證
# ============================================================================
print("\n" + "=" * 80)
print("7. 交叉驗證 (5-Fold)")
print("=" * 80)

kfold = KFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(model, X, y, cv=kfold, scoring='r2', n_jobs=-1)
print(f"CV R² = {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# ============================================================================
# 8. 特徵重要性
# ============================================================================
print("\n" + "=" * 80)
print("8. 特徵重要性 Top 25")
print("=" * 80)

if hasattr(model, 'feature_importances_'):
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print(f"{'排名':<5} {'特徵名稱':<40} {'重要性':>10}")
    print("-" * 60)
    for i, row in feature_importance.head(25).iterrows():
        rank = feature_importance.index.get_loc(i) + 1
        print(f"{rank:<5} {row['feature']:<40} {row['importance']:>10.4f}")

    feature_importance.to_excel('feature_importance_v2.xlsx', index=False)

# ============================================================================
# 9. 誤差分析
# ============================================================================
print("\n" + "=" * 80)
print("9. 誤差分析")
print("=" * 80)

errors = y_test - y_pred
abs_errors = np.abs(errors)

print(f"平均誤差: {errors.mean():.4f}")
print(f"誤差標準差: {errors.std():.4f}")
print(f"\n絕對誤差分佈:")
print(f"  < 0.5%: {(abs_errors < 0.5).sum() / len(abs_errors) * 100:.1f}%")
print(f"  < 1.0%: {(abs_errors < 1.0).sum() / len(abs_errors) * 100:.1f}%")
print(f"  < 2.0%: {(abs_errors < 2.0).sum() / len(abs_errors) * 100:.1f}%")

# ============================================================================
# 10. 儲存模型
# ============================================================================
print("\n" + "=" * 80)
print("10. 儲存模型")
print("=" * 80)

# 儲存模型
model_filename = 'fcn_model_v2.pkl'
joblib.dump(model, model_filename)
print(f"模型已儲存: {model_filename}")

# 儲存特徵列表
with open('model_features_v2.txt', 'w') as f:
    for feat in feature_cols:
        f.write(f"{feat}\n")
print(f"特徵列表已儲存: model_features_v2.txt")

# 複製到 web-app
import shutil
webapp_model_dir = 'fcn-web-app/backend/models'
if os.path.exists(webapp_model_dir):
    shutil.copy(model_filename, os.path.join(webapp_model_dir, 'fcn_model_histgradient_boosting_deep.pkl'))
    shutil.copy('model_features_v2.txt', os.path.join(webapp_model_dir, 'model_features.txt'))
    print(f"已複製到 web-app: {webapp_model_dir}")

# ============================================================================
# 11. 總結
# ============================================================================
print("\n" + "=" * 80)
print("11. 訓練總結")
print("=" * 80)

print(f"""
📊 資料規模:
   - 總樣本: {len(y)}
   - 訓練集: {len(X_train)}
   - 測試集: {len(X_test)}
   - 特徵數: {len(feature_cols)}
   - 高 IV 樣本: {high_iv_mask.sum()}

🏆 模型表現:
   - R²:   {r2:.4f}
   - RMSE: {rmse:.4f}
   - MAE:  {mae:.4f}
   - CV R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}

📈 預測準確度:
   - {(abs_errors < 1.0).sum() / len(abs_errors) * 100:.1f}% 誤差 < 1%
   - {(abs_errors < 2.0).sum() / len(abs_errors) * 100:.1f}% 誤差 < 2%

✅ 新增特徵:
   - No_KO_Flag: Non-call == Tenor 的情況
   - Non-call Periods 相關特徵
""")

print("=" * 80)
print("模型訓練完成！")
print("=" * 80)
