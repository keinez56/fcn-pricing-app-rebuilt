import pandas as pd
import numpy as np

print("=" * 80)
print("FCN 特徵工程 V3 - IV 降冪排序 (Sorted IVs)")
print("=" * 80)

# 讀取V2資料
df = pd.read_excel('FCN_features_v2.xlsx')
print(f"\n原始資料形狀: {df.shape}")

# ============================================================================
# 1. 為什麼需要IV排序？
# ============================================================================
print("\n" + "=" * 80)
print("1. 為什麼需要IV排序？")
print("=" * 80)

print("""
【問題】
假設有兩筆FCN：
  - Case A: NVDA(IV=50%) + TSLA(IV=40%) + AAPL(IV=30%)
  - Case B: AAPL(IV=30%) + TSLA(IV=40%) + NVDA(IV=50%)

這兩個Case的風險和Coupon應該完全相同！
但如果不排序，模型會把它們當成不同的輸入。

【解決方案】
強制將IV從大到小排序：
  - IV_Rank_1 = 50% (最危險)
  - IV_Rank_2 = 40% (次危險)
  - IV_Rank_3 = 30% (最安全)

這樣：
  1. 模型不需要學習「排列組合」
  2. IV_Rank_1 直接代表「最危險的標的」
  3. 完美對應 Worst-of 結構的金融邏輯
""")

# ============================================================================
# 2. 實作IV降冪排序
# ============================================================================
print("\n" + "=" * 80)
print("2. 實作IV降冪排序")
print("=" * 80)

# 2.1 定義需要排序的IV相關欄位組
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
    'IV_Skew': ['IV_Skew_1', 'IV_Skew_2', 'IV_Skew_3'],
    'IV_Premium': ['IV_Premium_1', 'IV_Premium_2', 'IV_Premium_3'],
}

# 2.2 使用PUT_IMP_VOL_3M作為排序基準（3個月賣權隱含波動率）
print("\n【排序基準】使用 PUT_IMP_VOL_3M (3個月賣權隱含波動率)")

def get_iv_sort_indices(row):
    """
    根據PUT_IMP_VOL_3M獲取降冪排序的索引
    返回：排序後的索引列表 [idx1, idx2, idx3]，其中idx1對應最大IV
    """
    iv_values = [
        (0, row['PUT_IMP_VOL_3M'] if pd.notna(row['PUT_IMP_VOL_3M']) else -np.inf),
        (1, row['PUT_IMP_VOL_3M_2'] if pd.notna(row.get('PUT_IMP_VOL_3M_2')) else -np.inf),
        (2, row['PUT_IMP_VOL_3M_3'] if pd.notna(row.get('PUT_IMP_VOL_3M_3')) else -np.inf),
    ]
    # 根據IV值降冪排序
    sorted_indices = sorted(iv_values, key=lambda x: x[1], reverse=True)
    return [x[0] for x in sorted_indices]

# 2.3 對每一組特徵進行排序
print("\n開始對所有IV相關特徵進行降冪排序...")

# 先計算排序索引
print("計算排序索引...")
sort_indices = df.apply(get_iv_sort_indices, axis=1)
df['_sort_idx_0'] = sort_indices.apply(lambda x: x[0])
df['_sort_idx_1'] = sort_indices.apply(lambda x: x[1])
df['_sort_idx_2'] = sort_indices.apply(lambda x: x[2])

# 創建排序後的特徵
for group_name, cols in iv_groups.items():
    if all(col in df.columns for col in cols[:1]):  # 至少第一個欄位存在
        # 創建新的排序欄位名稱
        rank_cols = [f'{group_name}_Rank_{i+1}' for i in range(3)]

        print(f"  排序 {group_name}...")

        # 對每一行進行排序
        for i, rank_col in enumerate(rank_cols):
            def get_sorted_value(row, original_cols, sort_idx_col):
                idx = int(row[sort_idx_col])
                if idx < len(original_cols) and original_cols[idx] in row.index:
                    return row[original_cols[idx]]
                return np.nan

            df[rank_col] = df.apply(
                lambda row: get_sorted_value(row, cols, f'_sort_idx_{i}'),
                axis=1
            )

# 移除輔助欄位
df = df.drop(['_sort_idx_0', '_sort_idx_1', '_sort_idx_2'], axis=1)

print("\n排序完成！")

# ============================================================================
# 3. 驗證排序結果
# ============================================================================
print("\n" + "=" * 80)
print("3. 驗證排序結果")
print("=" * 80)

# 檢查PUT_IMP_VOL_3M的排序
print("\n【PUT_IMP_VOL_3M 排序驗證】")
rank_iv_cols = ['PUT_IMP_VOL_3M_Rank_1', 'PUT_IMP_VOL_3M_Rank_2', 'PUT_IMP_VOL_3M_Rank_3']
original_iv_cols = ['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']

print("\n原始順序 vs 排序後：")
sample = df[df['Basket_Size'] == 3].head(5)
print("\n原始順序 (可能亂序):")
print(sample[original_iv_cols])
print("\n排序後 (降冪排列):")
print(sample[rank_iv_cols])

# 驗證確實是降冪
print("\n【驗證降冪排列】")
rank_1 = df['PUT_IMP_VOL_3M_Rank_1']
rank_2 = df['PUT_IMP_VOL_3M_Rank_2']
rank_3 = df['PUT_IMP_VOL_3M_Rank_3']

# 檢查 Rank_1 >= Rank_2 >= Rank_3
valid_order = ((rank_1 >= rank_2) | rank_2.isna()) & ((rank_2 >= rank_3) | rank_3.isna())
print(f"符合降冪排列的比例: {valid_order.sum() / len(df) * 100:.2f}%")

# ============================================================================
# 4. 統計排序後的特徵
# ============================================================================
print("\n" + "=" * 80)
print("4. 排序後特徵統計")
print("=" * 80)

print("\n【PUT_IMP_VOL_3M 排序後統計】")
print(df[rank_iv_cols].describe())

print("\n【各Rank與Coupon的相關性】")
rank_corr = df[rank_iv_cols + ['Coupon']].corr()['Coupon'].drop('Coupon')
for feat, corr in rank_corr.items():
    print(f"  {feat}: {corr:.4f}")

print("\n【重要發現】")
print(f"  Rank_1 (最危險) 相關性: {rank_corr['PUT_IMP_VOL_3M_Rank_1']:.4f}")
print(f"  Rank_2 (次危險) 相關性: {rank_corr['PUT_IMP_VOL_3M_Rank_2']:.4f}")
if 'PUT_IMP_VOL_3M_Rank_3' in rank_corr:
    print(f"  Rank_3 (最安全) 相關性: {rank_corr['PUT_IMP_VOL_3M_Rank_3']:.4f}")

# ============================================================================
# 5. 使用排序後的IV重新計算關鍵特徵
# ============================================================================
print("\n" + "=" * 80)
print("5. 基於排序IV重新計算關鍵特徵")
print("=" * 80)

# 5.1 使用排序後的IV計算風險分數
print("\n【更新風險計算特徵】")

# 使用Rank_1 (最高IV) 計算標準化KI距離
df['KI_Distance_Std_Sorted'] = (
    (df['Strike (%)'] - df['KI Barrier (%)']) / 100 /
    (df['PUT_IMP_VOL_3M_Rank_1'] / 100 * np.sqrt(df['Tenor (m)'] / 12))
)

# 基於排序IV的風險評分
df['Risk_Score_Sorted'] = (
    (df['PUT_IMP_VOL_3M_Rank_1'] / df['PUT_IMP_VOL_3M_Rank_1'].mean()) *
    (df['KI Barrier (%)'] / 100) *
    (1 + 0.2 * (df['Basket_Size'] - 1))
)

print("新增特徵:")
print("  - KI_Distance_Std_Sorted: 基於最高IV的標準化KI距離")
print("  - Risk_Score_Sorted: 基於排序IV的風險評分")

# ============================================================================
# 6. 新增特徵與Coupon相關性排名
# ============================================================================
print("\n" + "=" * 80)
print("6. 排序特徵與Coupon相關性排名")
print("=" * 80)

# 收集所有新增的排序特徵
sorted_features = []
for group_name in iv_groups.keys():
    for i in range(1, 4):
        col_name = f'{group_name}_Rank_{i}'
        if col_name in df.columns:
            sorted_features.append(col_name)

# 加入衍生特徵
sorted_features.extend(['KI_Distance_Std_Sorted', 'Risk_Score_Sorted'])

print(f"\n共新增 {len(sorted_features)} 個排序相關特徵")

# 計算相關性
valid_sorted_features = [f for f in sorted_features if f in df.columns]
sorted_corr = df[valid_sorted_features + ['Coupon']].corr()['Coupon'].drop('Coupon')
sorted_corr_abs = sorted_corr.abs().sort_values(ascending=False)

print("\n【Top 20 排序特徵相關性】")
for i, (feat, abs_corr) in enumerate(sorted_corr_abs.head(20).items(), 1):
    actual_corr = sorted_corr[feat]
    print(f"{i:2d}. {feat:35s} {actual_corr:7.4f} (|{abs_corr:.4f}|)")

# ============================================================================
# 7. 比較排序前後的效果
# ============================================================================
print("\n" + "=" * 80)
print("7. 排序前後效果比較")
print("=" * 80)

print("\n【原始IV vs 排序IV的相關性對比】")
print("\nPUT_IMP_VOL_3M:")
print(f"  原始 IV_1 (隨機順序):     {df['PUT_IMP_VOL_3M'].corr(df['Coupon']):.4f}")
print(f"  排序 Rank_1 (最高IV):     {df['PUT_IMP_VOL_3M_Rank_1'].corr(df['Coupon']):.4f}")

print(f"\n  原始 IV_2 (隨機順序):     {df['PUT_IMP_VOL_3M_2'].corr(df['Coupon']):.4f}")
print(f"  排序 Rank_2 (次高IV):     {df['PUT_IMP_VOL_3M_Rank_2'].corr(df['Coupon']):.4f}")

print("\n【風險評分比較】")
print(f"  原始 Basket_Risk_Score:   {df['Basket_Risk_Score'].corr(df['Coupon']):.4f}")
print(f"  排序 Risk_Score_Sorted:   {df['Risk_Score_Sorted'].corr(df['Coupon']):.4f}")

# ============================================================================
# 8. 儲存資料
# ============================================================================
print("\n" + "=" * 80)
print("8. 儲存資料")
print("=" * 80)

output_file = 'FCN_features_v3_sorted.xlsx'
df.to_excel(output_file, index=False)

print(f"\n資料已儲存至: {output_file}")
print(f"最終形狀: {df.shape}")

# ============================================================================
# 9. 總結
# ============================================================================
print("\n" + "=" * 80)
print("9. IV排序特徵工程總結")
print("=" * 80)

print("""
✅ 為什麼排序很重要：
   1. Worst-of 結構由「最差的標的」決定
   2. 排序後 Rank_1 = 最危險的標的（最高IV）
   3. 模型不需浪費運算力學習「誰是老大」
   4. 消除「換股票順序導致報價改變」的問題

✅ 新增的排序特徵：
   - PUT_IMP_VOL_3M_Rank_1/2/3 (3個月賣權IV)
   - VOLATILITY_90D_Rank_1/2/3 (90天歷史波動率)
   - 其他IV相關欄位的排序版本
   - KI_Distance_Std_Sorted (基於最高IV)
   - Risk_Score_Sorted (基於排序IV)

✅ 預期效果：
   - 模型可解釋性大幅提升
   - 特徵重要性更符合金融邏輯
   - Rank_1 的重要性應遠高於 Rank_2/3
   - 避免排列組合導致的不一致性
""")

print("\n" + "=" * 80)
print("V3 IV排序特徵工程完成！")
print("=" * 80)
