"""
FCN 模型重新訓練 V8 - 最佳化策略
=====================================
結合原本 R²=0.92 的設定 + 4 檔股票支援

關鍵改進:
1. 使用更激進的模型參數 (max_depth=15, min_samples_leaf=3)
2. 保留原始 IV 欄位作為特徵
3. 主要訓練原始資料，少量加入 12/16 4 檔樣本
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import json
import warnings
import os
warnings.filterwarnings('ignore')

print("=" * 80)
print("FCN 模型重新訓練 V8 - 最佳化策略")
print("=" * 80)

# ============================================================================
# 1. 載入資料
# ============================================================================
print("\n" + "=" * 80)
print("1. 載入資料")
print("=" * 80)

df_raw = pd.read_excel('FCN資料表.xlsx')
print(f"原始資料形狀: {df_raw.shape}")

# 轉換日期
df_raw['Date_Str'] = pd.to_datetime(df_raw['Pricing Date']).dt.strftime('%Y-%m-%d')

# 標記發行商和期間
df_raw['Issuer'] = df_raw['Date_Str'].apply(lambda x: 'Barclays' if x == '2025-12-12' else 'UBS')

# 計算 Basket Size (支援 4 檔)
df_raw['Basket_Size'] = df_raw[['BBG Code 1', 'BBG Code 2', 'BBG Code 3', 'BBG Code 4']].notna().sum(axis=1)

# 處理 Coupon
df_raw['Coupon'] = pd.to_numeric(df_raw['Coupon p.a. (%)'], errors='coerce')
barclays_mask = df_raw['Issuer'] == 'Barclays'
df_raw.loc[barclays_mask, 'Coupon'] = df_raw.loc[barclays_mask, 'Coupon'] * 100

# 過濾有效資料
df_raw = df_raw[df_raw['Coupon'].notna() & (df_raw['Coupon'] > 0)]

# No_KO Flag
df_raw['No_KO_Flag'] = (df_raw['Non-call Periods (m)'] == df_raw['Tenor (m)']).astype(int)

# 標記期間
df_raw['Period'] = df_raw['Date_Str'].apply(lambda x:
    'Original' if x < '2025-12-01' else
    'Dec12_Barclays' if x == '2025-12-12' else
    'Dec16_UBS')

print("\n【資料分類統計】")
summary = df_raw.groupby('Period').agg({
    'Coupon': ['count', 'mean'],
    'No_KO_Flag': 'sum',
    'Basket_Size': lambda x: (x == 4).sum()
}).round(2)
print(summary)

# 只用 UBS 資料 (原始 + 12/16)
df_ubs = df_raw[df_raw['Issuer'] == 'UBS'].copy()
df_barclays = df_raw[df_raw['Issuer'] == 'Barclays'].copy()

print(f"\nUBS 資料: {len(df_ubs)} 筆")
print(f"巴克萊資料: {len(df_barclays)} 筆 (只用於 No_KO 調整)")

# ============================================================================
# 2. 載入 IV 資料
# ============================================================================
print("\n" + "=" * 80)
print("2. 載入 IV 資料")
print("=" * 80)

iv_data_path = 'iv_data'

all_iv_data = {}
for f in os.listdir(iv_data_path):
    if f.endswith('.xlsx') and not f.startswith('~$'):
        date_key = f.replace('.xlsx', '')
        df_iv = pd.read_excel(os.path.join(iv_data_path, f))
        df_iv = df_iv.iloc[1:].reset_index(drop=True)
        df_iv = df_iv.rename(columns={'Unnamed: 0': 'BBG_Code'})
        df_iv['BBG_Code'] = df_iv['BBG_Code'].astype(str).str.replace(' Equity', '').str.replace(' US', '')
        all_iv_data[date_key] = df_iv

print(f"已載入 IV 資料日期: {sorted(all_iv_data.keys())}")

# IV 欄位映射
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

def get_date_key(date_str):
    """將日期字串轉換為 YYYYMMDD 格式"""
    try:
        return date_str.replace('-', '')
    except:
        return None

df_ubs['Date_Key'] = df_ubs['Date_Str'].apply(get_date_key)

def get_iv_for_stock(row, stock_col, suffix=''):
    """取得特定股票的 IV 資料"""
    date_key = row.get('Date_Key')
    stock_code = row.get(stock_col)

    if pd.isna(date_key) or pd.isna(stock_code):
        return pd.Series({f'{iv_rename.get(col, col)}{suffix}': np.nan for col in iv_columns})

    stock_code = str(stock_code).replace(' Equity', '').replace(' US', '').strip()

    iv_df = all_iv_data.get(date_key)
    if iv_df is None:
        available_dates = sorted(all_iv_data.keys(), reverse=True)
        for d in available_dates:
            if d <= date_key:
                iv_df = all_iv_data[d]
                break
        if iv_df is None and available_dates:
            iv_df = all_iv_data[available_dates[0]]

    if iv_df is None:
        return pd.Series({f'{iv_rename.get(col, col)}{suffix}': np.nan for col in iv_columns})

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

# 合併 IV 資料 (4 檔股票)
print("\n合併 IV 資料...")
for i, suffix in [(1, ''), (2, '_2'), (3, '_3'), (4, '_4')]:
    print(f"  處理 BBG Code {i}...")
    iv_data = df_ubs.apply(lambda row: get_iv_for_stock(row, f'BBG Code {i}', suffix), axis=1)
    df_ubs = pd.concat([df_ubs.reset_index(drop=True), iv_data], axis=1)

print(f"合併後資料形狀: {df_ubs.shape}")

# ============================================================================
# 3. 特徵工程 (與 V2 相同)
# ============================================================================
print("\n" + "=" * 80)
print("3. 特徵工程")
print("=" * 80)

df = df_ubs.copy()

# 標的數量
df['Num_Underlyings'] = df['Basket_Size']

# 費用特徵
df['Fee'] = 100 - df['Cost (%)']
df['Annualized_Fee'] = (df['Fee'] / df['Tenor (m)']) * 12

# 障礙價特徵
df['KO_Strike_Distance'] = df['KO Barrier (%)'] - df['Strike (%)']
df['Strike_KI_Distance'] = df['Strike (%)'] - df['KI Barrier (%)']
df['KO_KI_Range'] = df['KO Barrier (%)'] - df['KI Barrier (%)']
df['KI_Strike_Ratio'] = df['KI Barrier (%)'] / df['Strike (%)']
df['KO_Strike_Ratio'] = df['KO Barrier (%)'] / df['Strike (%)']
df['KI_Distance_Pct'] = df['Strike (%)'] - df['KI Barrier (%)']
df['KO_Distance_Pct'] = df['KO Barrier (%)'] - df['Strike (%)']

# 時間價值特徵
df['Tenor_Sqrt'] = np.sqrt(df['Tenor (m)'])
df['Tenor_Squared'] = df['Tenor (m)'] ** 2
df['Callable_Period'] = df['Tenor (m)'] - df['Non-call Periods (m)']
df['Callable_Ratio'] = df['Callable_Period'] / df['Tenor (m)']
df['NonCall_Ratio'] = df['Non-call Periods (m)'] / df['Tenor (m)']

# Basket 特徵 (4 檔支援)
iv_3m_cols = ['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3', 'PUT_IMP_VOL_3M_4']
hv_90d_cols = ['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3', 'VOLATILITY_90D_4']
corr_cols = ['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3', 'CORR_COEF_4']

def safe_agg(row, cols, func):
    values = [row[col] for col in cols if col in row.index and pd.notna(row[col])]
    if not values:
        return np.nan
    if func == 'max':
        return max(values)
    elif func == 'min':
        return min(values)
    elif func == 'mean':
        return np.mean(values)
    elif func == 'range':
        return max(values) - min(values) if len(values) > 1 else 0

df['Basket_Worst_IV'] = df.apply(lambda row: safe_agg(row, iv_3m_cols, 'max'), axis=1)
df['Basket_Best_IV'] = df.apply(lambda row: safe_agg(row, iv_3m_cols, 'min'), axis=1)
df['Basket_IV_Range'] = df['Basket_Worst_IV'] - df['Basket_Best_IV']
df['Basket_Avg_IV'] = df.apply(lambda row: safe_agg(row, iv_3m_cols, 'mean'), axis=1)
df['Basket_Avg_HV'] = df.apply(lambda row: safe_agg(row, hv_90d_cols, 'mean'), axis=1)
df['Basket_Avg_Corr'] = df.apply(lambda row: safe_agg(row, corr_cols, 'mean'), axis=1)

df['Basket_Worst_HV'] = df.apply(lambda row: safe_agg(row, hv_90d_cols, 'max'), axis=1)
df['Basket_Best_HV'] = df.apply(lambda row: safe_agg(row, hv_90d_cols, 'min'), axis=1)
df['Basket_Min_Corr'] = df.apply(lambda row: safe_agg(row, corr_cols, 'min'), axis=1)
df['Max_Correlation'] = df.apply(lambda row: safe_agg(row, corr_cols, 'max'), axis=1)
df['Min_Correlation'] = df['Basket_Min_Corr']

df['Basket_Complexity_Factor'] = df['Basket_Size'] / 3.0

# 相關性調整 IV
df['Corr_Adjusted_IV'] = df['Basket_Worst_IV'].copy()
multi_asset_mask = (df['Basket_Size'] > 1) & (df['Basket_Avg_Corr'].notna())
df.loc[multi_asset_mask, 'Corr_Adjusted_IV'] = (
    df.loc[multi_asset_mask, 'Basket_Worst_IV'] *
    (1 + 0.1 * (df.loc[multi_asset_mask, 'Basket_Size'] - 1) *
     (1 - df.loc[multi_asset_mask, 'Basket_Avg_Corr']))
)

# IV Skew 和 Premium
for i, suffix in [(1, ''), (2, '_2'), (3, '_3'), (4, '_4')]:
    put_col = f'PUT_IMP_VOL_2M_25D{suffix}'
    call_col = f'CALL_IMP_VOL_2M_25D{suffix}'
    if put_col in df.columns and call_col in df.columns:
        df[f'IV_Skew_{i}'] = df[put_col] - df[call_col]

    iv_col = f'PUT_IMP_VOL_3M{suffix}'
    hv_col = f'VOLATILITY_90D{suffix}'
    if iv_col in df.columns and hv_col in df.columns:
        df[f'IV_Premium_{i}'] = (df[iv_col] - df[hv_col]) / df[hv_col].replace(0, np.nan)

skew_cols = [f'IV_Skew_{i}' for i in range(1, 5) if f'IV_Skew_{i}' in df.columns]
df['Basket_Avg_Skew'] = df.apply(lambda row: safe_agg(row, skew_cols, 'mean'), axis=1)
df['Basket_Max_Skew'] = df.apply(lambda row: safe_agg(row, skew_cols, 'max'), axis=1)

premium_cols = [f'IV_Premium_{i}' for i in range(1, 5) if f'IV_Premium_{i}' in df.columns]
df['Basket_Avg_IV_Premium'] = df.apply(lambda row: safe_agg(row, premium_cols, 'mean'), axis=1)
df['Basket_Max_IV_Premium'] = df.apply(lambda row: safe_agg(row, premium_cols, 'max'), axis=1)

# 標準化距離
df['Annualized_Vol_Factor'] = df['Basket_Worst_IV'] / 100 * np.sqrt(df['Tenor (m)'] / 12)
df['KI_Distance_Std'] = df['KI_Distance_Pct'] / 100 / df['Annualized_Vol_Factor'].replace(0, np.nan)
df['KO_Distance_Std'] = df['KO_Distance_Pct'] / 100 / df['Annualized_Vol_Factor'].replace(0, np.nan)

# IV 比率
df['IV_HV_Ratio'] = df['Basket_Avg_IV'] / df['Basket_Avg_HV'].replace(0, np.nan)

# 風險評分
mean_worst_iv = df['Basket_Worst_IV'].mean()
df['KI_Risk_Score'] = (df['Basket_Worst_IV'] / mean_worst_iv) * (df['KI Barrier (%)'] / 100)
df['Return_Potential'] = (df['KO Barrier (%)'] / 100) * (df['Tenor (m)'] / 12)

df['Basket_Risk_Score'] = (
    (df['Basket_Worst_IV'] / mean_worst_iv) *
    (df['KI Barrier (%)'] / 100) *
    (1 + 0.2 * (df['Basket_Size'] - 1))
)
df.loc[multi_asset_mask, 'Basket_Risk_Score'] = (
    df.loc[multi_asset_mask, 'Basket_Risk_Score'] *
    (1 + 0.1 * (1 - df.loc[multi_asset_mask, 'Basket_Avg_Corr']))
)

# Barrier Type 編碼
df['Barrier_Type_AKI'] = (df['Barrier Type'] == 'AKI').astype(int)

# 年化波動率
df['Annualized_Vol'] = df['Basket_Avg_IV'] * np.sqrt(df['Tenor (m)'] / 12)

# IV 排序特徵 (按 PUT_IMP_VOL_3M 降冪排序) - 支援 4 檔
print("\n建立 IV 排序特徵...")

def get_iv_sort_indices(row):
    iv_values = []
    for i, suffix in [(0, ''), (1, '_2'), (2, '_3'), (3, '_4')]:
        col = f'PUT_IMP_VOL_3M{suffix}'
        val = row.get(col, np.nan)
        if pd.notna(val):
            iv_values.append((i, val))
        else:
            iv_values.append((i, -np.inf))
    sorted_indices = sorted(iv_values, key=lambda x: x[1], reverse=True)
    return [x[0] for x in sorted_indices]

sort_indices = df.apply(get_iv_sort_indices, axis=1)
for i in range(4):
    df[f'_sort_idx_{i}'] = sort_indices.apply(lambda x: x[i])

# IV 欄位組 (4 檔)
iv_groups = {
    'PUT_IMP_VOL_3M': ['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3', 'PUT_IMP_VOL_3M_4'],
    'VOLATILITY_90D': ['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3', 'VOLATILITY_90D_4'],
    'CALL_IMP_VOL_2M_25D': ['CALL_IMP_VOL_2M_25D', 'CALL_IMP_VOL_2M_25D_2', 'CALL_IMP_VOL_2M_25D_3', 'CALL_IMP_VOL_2M_25D_4'],
    'PUT_IMP_VOL_2M_25D': ['PUT_IMP_VOL_2M_25D', 'PUT_IMP_VOL_2M_25D_2', 'PUT_IMP_VOL_2M_25D_3', 'PUT_IMP_VOL_2M_25D_4'],
    'HIST_PUT_IMP_VOL': ['HIST_PUT_IMP_VOL', 'HIST_PUT_IMP_VOL_2', 'HIST_PUT_IMP_VOL_3', 'HIST_PUT_IMP_VOL_4'],
    'VOL_STDDEV': ['VOL_STDDEV', 'VOL_STDDEV_2', 'VOL_STDDEV_3', 'VOL_STDDEV_4'],
    'VOL_PERCENTILE': ['VOL_PERCENTILE', 'VOL_PERCENTILE_2', 'VOL_PERCENTILE_3', 'VOL_PERCENTILE_4'],
    'CHG_PCT_1YR': ['CHG_PCT_1YR', 'CHG_PCT_1YR_2', 'CHG_PCT_1YR_3', 'CHG_PCT_1YR_4'],
    'CORR_COEF': ['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3', 'CORR_COEF_4'],
    'DIVIDEND_YIELD': ['DIVIDEND_YIELD', 'DIVIDEND_YIELD_2', 'DIVIDEND_YIELD_3', 'DIVIDEND_YIELD_4'],
    'PX_LAST': ['PX_LAST', 'PX_LAST_2', 'PX_LAST_3', 'PX_LAST_4'],
}

for group_name, cols in iv_groups.items():
    for i in range(4):
        rank_col = f'{group_name}_Rank_{i+1}'
        idx_col = f'_sort_idx_{i}'

        def get_sorted_value(row, original_cols=cols, idx_col=idx_col):
            idx = int(row[idx_col])
            if idx < len(original_cols) and original_cols[idx] in row.index:
                return row[original_cols[idx]]
            return np.nan

        df[rank_col] = df.apply(get_sorted_value, axis=1)

# IV Skew 和 Premium 排序版本
for i in range(4):
    put_col = f'PUT_IMP_VOL_2M_25D_Rank_{i+1}'
    call_col = f'CALL_IMP_VOL_2M_25D_Rank_{i+1}'
    if put_col in df.columns and call_col in df.columns:
        df[f'IV_Skew_Rank_{i+1}'] = df[put_col] - df[call_col]

    iv_col = f'PUT_IMP_VOL_3M_Rank_{i+1}'
    hv_col = f'VOLATILITY_90D_Rank_{i+1}'
    if iv_col in df.columns and hv_col in df.columns:
        df[f'IV_Premium_Rank_{i+1}'] = (df[iv_col] - df[hv_col]) / df[hv_col].replace(0, np.nan)

# 排序後的風險特徵
df['KI_Distance_Std_Sorted'] = (
    (df['Strike (%)'] - df['KI Barrier (%)']) / 100 /
    (df['PUT_IMP_VOL_3M_Rank_1'] / 100 * np.sqrt(df['Tenor (m)'] / 12))
)

mean_rank1_iv = df['PUT_IMP_VOL_3M_Rank_1'].mean()
df['Risk_Score_Sorted'] = (
    (df['PUT_IMP_VOL_3M_Rank_1'] / mean_rank1_iv) *
    (df['KI Barrier (%)'] / 100) *
    (1 + 0.2 * (df['Basket_Size'] - 1))
)

# 移除輔助欄位
for i in range(4):
    df = df.drop([f'_sort_idx_{i}'], axis=1, errors='ignore')

# No_KO 交互特徵
df['No_KO_Tenor_Interaction'] = df['No_KO_Flag'] * df['Tenor (m)']
df['No_KO_Basket_Interaction'] = df['No_KO_Flag'] * df['Basket_Size']
df['No_KO_KI_Interaction'] = df['No_KO_Flag'] * df['KI Barrier (%)']
df['No_KO_Strike_Interaction'] = df['No_KO_Flag'] * df['Strike (%)']

print(f"特徵工程後資料形狀: {df.shape}")

# ============================================================================
# 4. 準備訓練資料
# ============================================================================
print("\n" + "=" * 80)
print("4. 準備訓練資料")
print("=" * 80)

target = 'Coupon'

# 排除欄位 (與 V2 相同，保留原始 IV)
exclude_cols = [
    'Coupon', 'Coupon p.a. (%)',
    'Pricing Date', 'Date_Key', 'Date_Str',
    'BBG Code 1', 'BBG Code 2', 'BBG Code 3', 'BBG Code 4', 'BBG Code 5',
    'Product', 'Currency', 'KO Type', 'Barrier Type',
    'Issuer', 'Period', 'Unnamed: 17',
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

# 填充 NaN
X = X.fillna(X.median())
X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(X.median())

# 分割資料
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"訓練集: {len(X_train)}, 測試集: {len(X_test)}")

# ============================================================================
# 5. 訓練模型 (使用 V2 的激進參數)
# ============================================================================
print("\n" + "=" * 80)
print("5. 訓練模型 (激進參數)")
print("=" * 80)

model = HistGradientBoostingRegressor(
    max_iter=500,
    max_depth=15,           # 與 V2 相同
    learning_rate=0.05,
    min_samples_leaf=3,     # 與 V2 相同
    l2_regularization=0.1,
    random_state=42
)

model.fit(X_train, y_train)

y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

print("\n【訓練集表現】")
train_r2 = r2_score(y_train, y_pred_train)
print(f"  R² Score: {train_r2:.4f}")
print(f"  RMSE: {np.sqrt(mean_squared_error(y_train, y_pred_train)):.4f}")
print(f"  MAE: {mean_absolute_error(y_train, y_pred_train):.4f}")

print("\n【測試集表現】")
test_r2 = r2_score(y_test, y_pred_test)
test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
test_mae = mean_absolute_error(y_test, y_pred_test)
print(f"  R² Score: {test_r2:.4f}")
print(f"  RMSE: {test_rmse:.4f}")
print(f"  MAE: {test_mae:.4f}")

# 交叉驗證
print("\n【5-Fold 交叉驗證】")
kfold = KFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(model, X, y, cv=kfold, scoring='r2', n_jobs=-1)
print(f"  CV R² = {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# ============================================================================
# 6. 分析各類型樣本表現
# ============================================================================
print("\n" + "=" * 80)
print("6. 各類型樣本表現")
print("=" * 80)

test_basket_size = X_test['Basket_Size'].values

print("\n【按 Basket Size 分析】")
for bs in [1, 2, 3, 4]:
    bs_mask = test_basket_size == bs
    if bs_mask.sum() > 5:
        r2 = r2_score(y_test[bs_mask], y_pred_test[bs_mask])
        mae = mean_absolute_error(y_test[bs_mask], y_pred_test[bs_mask])
        bias = (y_pred_test[bs_mask] - y_test[bs_mask].values).mean()
        print(f"  {bs}檔股票: n={bs_mask.sum()}, R²={r2:.4f}, MAE={mae:.4f}, Bias={bias:+.4f}")

# 高 IV 分析
if 'Basket_Worst_IV' in X_test.columns:
    high_iv_mask = X_test['Basket_Worst_IV'] > 50
    if high_iv_mask.sum() > 5:
        r2 = r2_score(y_test[high_iv_mask], y_pred_test[high_iv_mask])
        mae = mean_absolute_error(y_test[high_iv_mask], y_pred_test[high_iv_mask])
        print(f"\n【高 IV (>50) 表現】")
        print(f"  n={high_iv_mask.sum()}, R²={r2:.4f}, MAE={mae:.4f}")

# ============================================================================
# 7. 計算 No_KO 調整係數 (巴克萊資料)
# ============================================================================
print("\n" + "=" * 80)
print("7. No_KO 調整係數 (巴克萊資料)")
print("=" * 80)

if len(df_barclays) > 0:
    barclays_no_ko = df_barclays[df_barclays['No_KO_Flag'] == 1]
    barclays_normal = df_barclays[df_barclays['No_KO_Flag'] == 0]

    print(f"巴克萊 No_KO: {len(barclays_no_ko)} 筆, 平均 Coupon: {barclays_no_ko['Coupon'].mean():.2f}%")
    print(f"巴克萊 正常KO: {len(barclays_normal)} 筆, 平均 Coupon: {barclays_normal['Coupon'].mean():.2f}%")

    if len(barclays_no_ko) > 0 and len(barclays_normal) > 0:
        no_ko_adjustment = barclays_no_ko['Coupon'].mean() - barclays_normal['Coupon'].mean()
        print(f"\nNo_KO 調整係數: {no_ko_adjustment:+.2f}%")

        adjustment_config = {
            'global_no_ko_adjustment': no_ko_adjustment,
            'by_basket_size': {},
            'description': 'No_KO 結構相比正常 KO 的 Coupon 調整值'
        }

        for bs in [1, 2, 3, 4]:
            no_ko_bs = barclays_no_ko[barclays_no_ko['Basket_Size'] == bs]['Coupon'].mean()
            normal_bs = barclays_normal[barclays_normal['Basket_Size'] == bs]['Coupon'].mean()
            if not np.isnan(no_ko_bs) and not np.isnan(normal_bs):
                adjustment_config['by_basket_size'][str(bs)] = no_ko_bs - normal_bs
else:
    adjustment_config = {'global_no_ko_adjustment': 0, 'by_basket_size': {}}

# ============================================================================
# 8. 特徵重要性
# ============================================================================
print("\n" + "=" * 80)
print("8. 特徵重要性 Top 20")
print("=" * 80)

if hasattr(model, 'feature_importances_'):
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    print(f"{'排名':<5} {'特徵名稱':<40} {'重要性':>10}")
    print("-" * 60)
    for i, (_, row) in enumerate(feature_importance.head(20).iterrows()):
        print(f"{i+1:<5} {row['feature']:<40} {row['importance']:>10.4f}")

# ============================================================================
# 9. 儲存模型
# ============================================================================
print("\n" + "=" * 80)
print("9. 儲存模型")
print("=" * 80)

model_filename = 'fcn_model_v8_optimal.pkl'
joblib.dump(model, model_filename)
print(f"模型已儲存: {model_filename}")

features_path = 'model_features_v8.txt'
with open(features_path, 'w') as f:
    for feat in feature_cols:
        f.write(f"{feat}\n")
print(f"特徵列表已儲存: {features_path}")

# 儲存 No_KO 調整配置
with open('no_ko_adjustment.json', 'w') as f:
    json.dump(adjustment_config, f, indent=2)
print(f"No_KO 調整配置已儲存")

# 複製到 web-app
import shutil
webapp_model_dir = 'fcn-web-app/backend/models'
if os.path.exists(webapp_model_dir):
    shutil.copy(model_filename, os.path.join(webapp_model_dir, 'fcn_model_histgradient_boosting_deep.pkl'))
    shutil.copy(features_path, os.path.join(webapp_model_dir, 'model_features.txt'))
    print(f"已複製到 web-app: {webapp_model_dir}")

# ============================================================================
# 10. 總結
# ============================================================================
print("\n" + "=" * 80)
print("10. 訓練總結")
print("=" * 80)

print(f"""
📊 資料規模:
   - 總 UBS 樣本: {len(y)}
   - 訓練集: {len(X_train)}
   - 測試集: {len(X_test)}
   - 特徵數: {len(feature_cols)}
   - 4檔樣本: {(df['Basket_Size'] == 4).sum()}

🏆 模型表現:
   - 訓練集 R²: {train_r2:.4f}
   - 測試集 R²: {test_r2:.4f}
   - 測試集 RMSE: {test_rmse:.4f}
   - 測試集 MAE: {test_mae:.4f}
   - CV R²: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}

📝 No_KO 調整:
   - 全局調整: {adjustment_config.get('global_no_ko_adjustment', 0):+.2f}%

✅ 支援功能:
   - 4 檔股票支援
   - No_KO 調整係數
   - IV 排序特徵
""")

print("=" * 80)
print("訓練完成！請重啟後端服務。")
print("=" * 80)
