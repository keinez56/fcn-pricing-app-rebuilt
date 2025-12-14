import pandas as pd
import numpy as np

print("=" * 80)
print("資料前處理分析")
print("=" * 80)

# 讀取合併後的資料
df = pd.read_excel('FCN_merged_data.xlsx')
print(f"\n原始資料形狀: {df.shape}")

# ============================================================================
# 1. 檢查資料品質
# ============================================================================
print("\n" + "=" * 80)
print("1. 資料品質檢查")
print("=" * 80)

# 1.1 檢查缺失值
print("\n【缺失值統計】")
missing_stats = pd.DataFrame({
    '缺失數量': df.isnull().sum(),
    '缺失比例(%)': (df.isnull().sum() / len(df) * 100).round(2)
})
missing_stats = missing_stats[missing_stats['缺失數量'] > 0].sort_values('缺失數量', ascending=False)
print(missing_stats)

# 1.2 檢查Coupon欄位
print("\n【Coupon p.a. (%) 分析】")
print(f"資料類型: {df['Coupon p.a. (%)'].dtype}")
print(f"包含'-'的數量: {(df['Coupon p.a. (%)'] == '-').sum()}")
print(f"有效數值的數量: {(df['Coupon p.a. (%)'] != '-').sum()}")

# 查看Coupon的值範圍
valid_coupon = df[df['Coupon p.a. (%)'] != '-']['Coupon p.a. (%)'].astype(float)
print(f"\n有效Coupon統計:")
print(f"  最小值: {valid_coupon.min():.2f}%")
print(f"  最大值: {valid_coupon.max():.2f}%")
print(f"  平均值: {valid_coupon.mean():.2f}%")
print(f"  中位數: {valid_coupon.median():.2f}%")

# 1.3 檢查BBG Code的分佈
print("\n【標的組合分析】")
print(f"單一標的 (只有BBG Code 1): {df['BBG Code 2'].isna().sum()}")
print(f"兩個標的 (BBG Code 1, 2): {(df['BBG Code 2'].notna() & df['BBG Code 3'].isna()).sum()}")
print(f"三個標的 (BBG Code 1, 2, 3): {df['BBG Code 3'].notna().sum()}")

# 1.4 檢查數值欄位的範圍
print("\n【數值欄位範圍】")
numeric_cols = ['Strike (%)', 'KO Barrier (%)', 'KI Barrier (%)', 'Tenor (m)',
                'Cost (%)', 'Non-call Periods (m)']
for col in numeric_cols:
    if col in df.columns:
        print(f"{col}: {df[col].min()} ~ {df[col].max()} (唯一值: {df[col].nunique()})")

# ============================================================================
# 2. 資料清理
# ============================================================================
print("\n" + "=" * 80)
print("2. 資料清理")
print("=" * 80)

df_clean = df.copy()

# 2.1 移除不必要的欄位
print("\n【移除不必要欄位】")
cols_to_drop = ['Unnamed: 17', 'BBG Code 4', 'BBG Code 5', 'Product']  # Product都是FCN
existing_cols_to_drop = [col for col in cols_to_drop if col in df_clean.columns]
if existing_cols_to_drop:
    df_clean = df_clean.drop(existing_cols_to_drop, axis=1)
    print(f"已移除: {existing_cols_to_drop}")

# 2.2 處理Coupon欄位：將'-'標記為無效，並轉換為數值
print("\n【處理目標變數 Coupon】")
df_clean['Coupon_Valid'] = (df_clean['Coupon p.a. (%)'] != '-')
df_clean['Coupon'] = df_clean['Coupon p.a. (%)'].apply(
    lambda x: float(x) if x != '-' else np.nan
)
print(f"有效Coupon數量: {df_clean['Coupon_Valid'].sum()}")
print(f"無效Coupon數量: {(~df_clean['Coupon_Valid']).sum()}")

# 2.3 轉換數據類型
print("\n【轉換數據類型】")

# 確保數值欄位為float
numeric_features = ['Strike (%)', 'KO Barrier (%)', 'KI Barrier (%)',
                   'Tenor (m)', 'Cost (%)', 'Non-call Periods (m)']

for col in numeric_features:
    if col in df_clean.columns:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

# IV相關數值欄位
iv_numeric_cols = []
for suffix in ['', '_2', '_3']:
    for prefix in ['PX_LAST', 'PUT_IMP_VOL_3M', 'CALL_IMP_VOL_2M_25D',
                   'PUT_IMP_VOL_2M_25D', 'HIST_PUT_IMP_VOL', 'VOL_STDDEV',
                   'VOLATILITY_90D', 'VOL_PERCENTILE', 'CHG_PCT_1YR',
                   'CORR_COEF', 'DIVIDEND_YIELD']:
        col_name = prefix + suffix
        if col_name in df_clean.columns:
            df_clean[col_name] = pd.to_numeric(df_clean[col_name], errors='coerce')
            iv_numeric_cols.append(col_name)

print(f"已轉換 {len(numeric_features)} 個FCN特徵欄位")
print(f"已轉換 {len(iv_numeric_cols)} 個IV特徵欄位")

# ============================================================================
# 3. 特徵工程準備
# ============================================================================
print("\n" + "=" * 80)
print("3. 特徵工程分析")
print("=" * 80)

# 3.1 分析類別型變數
print("\n【類別型變數】")
categorical_cols = ['Currency', 'KO Type', 'Barrier Type']
for col in categorical_cols:
    if col in df_clean.columns:
        print(f"{col}: {df_clean[col].unique()}")

# 3.2 標的數量特徵
print("\n【建立標的數量特徵】")
df_clean['Num_Underlyings'] = (
    df_clean['BBG Code 1'].notna().astype(int) +
    df_clean['BBG Code 2'].notna().astype(int) +
    df_clean['BBG Code 3'].notna().astype(int)
)
print(df_clean['Num_Underlyings'].value_counts().sort_index())

# ============================================================================
# 4. 儲存清理後的資料
# ============================================================================
print("\n" + "=" * 80)
print("4. 儲存處理後資料")
print("=" * 80)

# 只保留有效Coupon的資料用於訓練
df_valid = df_clean[df_clean['Coupon_Valid']].copy()
print(f"\n有效資料形狀: {df_valid.shape}")

# 儲存完整清理資料（包含無效Coupon）
output_file_all = 'FCN_preprocessed_all.xlsx'
df_clean.to_excel(output_file_all, index=False)
print(f"完整資料已儲存至: {output_file_all}")

# 儲存有效資料（僅有效Coupon，用於訓練）
output_file_valid = 'FCN_preprocessed_valid.xlsx'
df_valid.to_excel(output_file_valid, index=False)
print(f"有效資料已儲存至: {output_file_valid}")

# ============================================================================
# 5. 資料摘要
# ============================================================================
print("\n" + "=" * 80)
print("5. 前處理摘要")
print("=" * 80)

print(f"\n原始資料: {df.shape}")
print(f"清理後完整資料: {df_clean.shape}")
print(f"有效訓練資料: {df_valid.shape}")

print("\n【欄位清單】")
print(f"總欄位數: {len(df_clean.columns)}")
print("\nFCN條件特徵:")
fcn_features = ['Pricing Date', 'Currency', 'Non-call Periods (m)',
                'BBG Code 1', 'BBG Code 2', 'BBG Code 3',
                'Strike (%)', 'KO Type', 'KO Barrier (%)',
                'Tenor (m)', 'Barrier Type', 'KI Barrier (%)',
                'Cost (%)', 'Num_Underlyings']
for i, col in enumerate(fcn_features, 1):
    if col in df_clean.columns:
        print(f"  {i}. {col}")

print("\n市場IV特徵 (標的1):")
iv_features_1 = [col for col in df_clean.columns if col in [
    'PX_LAST', 'PUT_IMP_VOL_3M', 'CALL_IMP_VOL_2M_25D',
    'PUT_IMP_VOL_2M_25D', 'HIST_PUT_IMP_VOL', 'VOL_STDDEV',
    'VOLATILITY_90D', 'VOL_PERCENTILE', 'CHG_PCT_1YR',
    'CORR_COEF', 'DIVIDEND_YIELD'
]]
for i, col in enumerate(iv_features_1, 1):
    print(f"  {i}. {col}")

print("\n目標變數:")
print(f"  - Coupon (原始: Coupon p.a. (%))")
print(f"  - Coupon_Valid (是否有效)")

print("\n" + "=" * 80)
print("資料前處理完成！")
print("=" * 80)
