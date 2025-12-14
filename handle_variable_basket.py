import pandas as pd
import numpy as np

print("=" * 80)
print("處理變長資產籃 (Variable-Length Basket Handling)")
print("=" * 80)

# 讀取特徵工程後的資料
df = pd.read_excel('FCN_engineered_features.xlsx')
print(f"\n原始資料形狀: {df.shape}")

# ============================================================================
# 1. 分析資產籃結構
# ============================================================================
print("\n" + "=" * 80)
print("1. 資產籃結構分析")
print("=" * 80)

# 已經有 Num_Underlyings，但我們重新命名為更專業的 Basket_Size
df['Basket_Size'] = df['Num_Underlyings']

print("\n【資產籃大小分佈】")
basket_dist = df['Basket_Size'].value_counts().sort_index()
print(basket_dist)
print(f"\n佔比:")
for size in sorted(df['Basket_Size'].unique()):
    count = (df['Basket_Size'] == size).sum()
    pct = count / len(df) * 100
    print(f"  {size}檔標的: {count:4d} 筆 ({pct:5.2f}%)")

# 分析每個Basket Size的Coupon差異
print("\n【不同Basket Size的Coupon統計】")
basket_coupon_stats = df.groupby('Basket_Size')['Coupon'].agg(['count', 'mean', 'std', 'min', 'max'])
print(basket_coupon_stats)

# ============================================================================
# 2. 錯誤做法示範 (不要這樣做！)
# ============================================================================
print("\n" + "=" * 80)
print("2. ❌ 錯誤做法示範 (僅供參考，不實際使用)")
print("=" * 80)

# 示範：如果填0會發生什麼
df_wrong = df.copy()
iv_cols_to_fill = ['PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3']
for col in iv_cols_to_fill:
    if col in df_wrong.columns:
        df_wrong[f'{col}_FILLED_ZERO'] = df_wrong[col].fillna(0)

print("\n❌ 填0的問題：")
print("  - IV=0 代表股價不會動，風險為0，這是完全錯誤的訊號")
print("  - 會讓模型誤以為單一標的FCN的風險最低")
print("  - 實際上：單一標的可能風險更集中！")

# 不保留這些錯誤欄位
df_wrong = df.copy()

# ============================================================================
# 3. 正確做法：Basket-aware特徵
# ============================================================================
print("\n" + "=" * 80)
print("3. ✅ 正確做法：Basket-aware特徵工程")
print("=" * 80)

# 3.1 Worst-Case IV (驅動因子)
# Worst Case Performance 原則：FCN的敲入通常由表現最差的標的觸發
print("\n【3.1 Worst-Case IV (最高波動率 = 最大風險)】")

# 計算最高隱含波動率（忽略NaN）
df['Basket_Worst_IV'] = df[['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']].max(axis=1, skipna=True)

# 計算最高歷史波動率
df['Basket_Worst_HV'] = df[['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3']].max(axis=1, skipna=True)

print("Basket_Worst_IV 統計:")
print(df.groupby('Basket_Size')['Basket_Worst_IV'].agg(['mean', 'std', 'min', 'max']))

# 3.2 Best-Case IV (最低波動率)
print("\n【3.2 Best-Case IV (最低波動率 = 最小風險)】")

df['Basket_Best_IV'] = df[['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']].min(axis=1, skipna=True)
df['Basket_Best_HV'] = df[['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3']].min(axis=1, skipna=True)

print("Basket_Best_IV 統計:")
print(df.groupby('Basket_Size')['Basket_Best_IV'].agg(['mean', 'std', 'min', 'max']))

# 3.3 IV Range (波動率範圍 = 分散度)
print("\n【3.3 Basket IV Range (標的間波動率差異)】")

df['Basket_IV_Range'] = df['Basket_Worst_IV'] - df['Basket_Best_IV']

# 對於單一標的，Range應該為0
print("Basket_IV_Range 統計:")
print(df.groupby('Basket_Size')['Basket_IV_Range'].agg(['mean', 'std', 'min', 'max']))

# 3.4 加權平均IV (考慮標的數量)
print("\n【3.4 Basket Weighted Average IV】")

# 計算有效標的數量的IV總和，然後除以Basket_Size
# 這樣可以正確處理NaN
def safe_mean_iv(row, cols):
    """安全計算平均IV，自動忽略NaN"""
    values = [row[col] for col in cols if pd.notna(row[col])]
    return np.mean(values) if values else np.nan

iv_3m_cols = ['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']
hv_90d_cols = ['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3']

df['Basket_Avg_IV'] = df.apply(lambda row: safe_mean_iv(row, iv_3m_cols), axis=1)
df['Basket_Avg_HV'] = df.apply(lambda row: safe_mean_iv(row, hv_90d_cols), axis=1)

print("Basket_Avg_IV 統計:")
print(df.groupby('Basket_Size')['Basket_Avg_IV'].agg(['mean', 'std', 'min', 'max']))

# 3.5 Correlation Features (相關性特徵)
print("\n【3.5 Basket Correlation Features】")

# 對於多標的FCN，相關性很重要
# 相關性低 = 分散效果好 = 風險較低 = Coupon應該較低

# 最低相關性（最差情況：標的獨立變動）
df['Basket_Min_Corr'] = df[['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3']].min(axis=1, skipna=True)

# 平均相關性
def safe_mean_corr(row, cols):
    values = [row[col] for col in cols if pd.notna(row[col])]
    return np.mean(values) if values else np.nan

corr_cols = ['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3']
df['Basket_Avg_Corr'] = df.apply(lambda row: safe_mean_corr(row, corr_cols), axis=1)

# 對於單一標的，相關性特徵無意義，設為NaN是合理的
print("Basket_Avg_Corr 統計 (單一標的為NaN是正確的):")
print(df.groupby('Basket_Size')['Basket_Avg_Corr'].agg(['count', 'mean', 'std']))

# ============================================================================
# 4. 多樣性風險調整 (Diversification Adjustment)
# ============================================================================
print("\n" + "=" * 80)
print("4. 多樣性風險調整")
print("=" * 80)

# 4.1 理論基礎
print("\n【理論基礎】")
print("單一標的：風險集中，但只要這檔不跌破KI就安全")
print("多標的：Worst-of結構，只要有一檔觸發KI就敲入")
print("因此：標的越多，理論上敲入機率越高（但相關性會降低此效應）")

# 4.2 多樣性折價因子 (Diversification Discount)
# 公式：sqrt(1/N) 的概念（來自投資組合理論）
# 但對於Worst-of，實際上是增加風險，所以我們用相反的概念

df['Basket_Complexity_Factor'] = df['Basket_Size'] / 3.0  # 標準化到1檔=0.33, 3檔=1.0

# 4.3 相關性調整後的有效IV
# 如果標的完全相關（corr=1），就像單一標的
# 如果標的完全不相關（corr=0），worst-of效應最大

# 對於有相關性數據的記錄，計算調整後IV
# Effective_IV = Worst_IV * (1 + Basket_Size_Effect * (1 - Avg_Corr))
# 相關性低時，Basket Size效應放大

df['Corr_Adjusted_IV'] = df['Basket_Worst_IV'].copy()

# 只對多標的進行調整
multi_asset_mask = (df['Basket_Size'] > 1) & (df['Basket_Avg_Corr'].notna())

df.loc[multi_asset_mask, 'Corr_Adjusted_IV'] = (
    df.loc[multi_asset_mask, 'Basket_Worst_IV'] *
    (1 + 0.1 * (df.loc[multi_asset_mask, 'Basket_Size'] - 1) *
     (1 - df.loc[multi_asset_mask, 'Basket_Avg_Corr']))
)

print("\n【相關性調整後的IV】")
print("Corr_Adjusted_IV vs Basket_Worst_IV:")
print(df.groupby('Basket_Size')[['Basket_Worst_IV', 'Corr_Adjusted_IV']].mean())

# ============================================================================
# 5. Basket-specific Risk Score
# ============================================================================
print("\n" + "=" * 80)
print("5. Basket-specific Risk Score")
print("=" * 80)

# 綜合風險評分，考慮：
# 1. Worst-case波動率
# 2. KI Barrier高度
# 3. Basket複雜度
# 4. 相關性效應

df['Basket_Risk_Score'] = (
    (df['Basket_Worst_IV'] / df['Basket_Worst_IV'].mean()) *  # 標準化波動率
    (df['KI Barrier (%)'] / 100) *  # KI高度
    (1 + 0.2 * (df['Basket_Size'] - 1))  # Basket複雜度調整
)

# 對於有相關性數據的，進一步調整
df.loc[multi_asset_mask, 'Basket_Risk_Score'] = (
    df.loc[multi_asset_mask, 'Basket_Risk_Score'] *
    (1 + 0.1 * (1 - df.loc[multi_asset_mask, 'Basket_Avg_Corr']))
)

print("\n【Basket Risk Score統計】")
print(df.groupby('Basket_Size')['Basket_Risk_Score'].agg(['mean', 'std', 'min', 'max']))

print("\n【與Coupon的相關性】")
print(f"Basket_Risk_Score vs Coupon: {df['Basket_Risk_Score'].corr(df['Coupon']):.4f}")

# ============================================================================
# 6. 驗證：比較不同處理方式的效果
# ============================================================================
print("\n" + "=" * 80)
print("6. 驗證不同Basket Size的特徵表現")
print("=" * 80)

basket_features = [
    'Basket_Size', 'Basket_Worst_IV', 'Basket_Best_IV', 'Basket_IV_Range',
    'Basket_Avg_IV', 'Basket_Avg_Corr', 'Basket_Complexity_Factor',
    'Corr_Adjusted_IV', 'Basket_Risk_Score'
]

print("\n【單一標的 (Basket_Size=1) 範例】")
single_asset = df[df['Basket_Size'] == 1][basket_features + ['Coupon']].head(3)
print(single_asset)

print("\n【三標的 (Basket_Size=3) 範例】")
triple_asset = df[df['Basket_Size'] == 3][basket_features + ['Coupon']].head(3)
print(triple_asset)

# ============================================================================
# 7. 特徵相關性分析
# ============================================================================
print("\n" + "=" * 80)
print("7. 新增Basket特徵與Coupon的相關性")
print("=" * 80)

basket_feature_list = [
    'Basket_Size', 'Basket_Worst_IV', 'Basket_Best_IV', 'Basket_IV_Range',
    'Basket_Avg_IV', 'Basket_Avg_HV', 'Basket_Min_Corr', 'Basket_Avg_Corr',
    'Basket_Complexity_Factor', 'Corr_Adjusted_IV', 'Basket_Risk_Score',
    'Basket_Worst_HV', 'Basket_Best_HV'
]

correlations = df[basket_feature_list + ['Coupon']].corr()['Coupon'].drop('Coupon')
correlations_sorted = correlations.abs().sort_values(ascending=False)

print("\n【絕對值相關性排序】")
for i, (feat, abs_corr) in enumerate(correlations_sorted.items(), 1):
    actual_corr = correlations[feat]
    print(f"{i:2d}. {feat:30s} {actual_corr:7.4f} (|{abs_corr:.4f}|)")

# ============================================================================
# 8. 處理剩餘的NaN值
# ============================================================================
print("\n" + "=" * 80)
print("8. 處理剩餘的NaN值策略")
print("=" * 80)

print("\n【關鍵原則】")
print("1. ✅ Basket聚合特徵 (Worst/Best/Avg IV) - 已正確處理，自動忽略NaN")
print("2. ✅ Basket_Avg_Corr - 單一標的保持NaN是正確的（無相關性概念）")
print("3. ⚠️  個別標的IV (IV_2, IV_3) - 建議保留NaN，讓模型學習")

print("\n【NaN保留策略】")
print("- 對於樹模型 (XGBoost/LightGBM)：原生支援NaN，會自動學習最佳分割")
print("- 對於線性模型：需要填補或使用indicator features")

print("\n決策：我們為樹模型保留NaN，但創建Basket聚合特徵作為替代方案")

# ============================================================================
# 9. 儲存處理後的資料
# ============================================================================
print("\n" + "=" * 80)
print("9. 儲存資料")
print("=" * 80)

output_file = 'FCN_basket_handled.xlsx'
df.to_excel(output_file, index=False)

print(f"\n資料已儲存至: {output_file}")
print(f"最終形狀: {df.shape}")

print("\n【新增的Basket特徵】")
new_basket_features = [
    'Basket_Size',           # 資產籃大小 (1-3)
    'Basket_Worst_IV',       # 最高IV (worst case)
    'Basket_Best_IV',        # 最低IV (best case)
    'Basket_IV_Range',       # IV範圍
    'Basket_Avg_IV',         # 平均IV
    'Basket_Worst_HV',       # 最高歷史波動率
    'Basket_Best_HV',        # 最低歷史波動率
    'Basket_Avg_HV',         # 平均歷史波動率
    'Basket_Min_Corr',       # 最低相關性
    'Basket_Avg_Corr',       # 平均相關性
    'Basket_Complexity_Factor',  # 複雜度因子
    'Corr_Adjusted_IV',      # 相關性調整後IV
    'Basket_Risk_Score',     # 綜合風險評分
]

print(f"\n新增 {len(new_basket_features)} 個Basket相關特徵:")
for i, feat in enumerate(new_basket_features, 1):
    print(f"  {i:2d}. {feat}")

# ============================================================================
# 10. 總結
# ============================================================================
print("\n" + "=" * 80)
print("10. 變長資產籃處理總結")
print("=" * 80)

print("\n✅ 正確做法：")
print("  1. Basket_Size明確告訴模型有幾檔標的")
print("  2. Worst/Best/Avg IV使用skipna=True，自動忽略不存在的標的")
print("  3. 單一標的的Basket_IV_Range自動為0，符合邏輯")
print("  4. 相關性特徵對單一標的保持NaN（無意義）")
print("  5. Basket_Risk_Score綜合考慮複雜度和相關性效應")

print("\n❌ 避免的錯誤：")
print("  1. 不填0（會誤導模型認為IV=0）")
print("  2. 不用全域平均填補（會掩蓋Basket Size差異）")
print("  3. 不刪除有NaN的樣本（會損失大量數據）")

print("\n🎯 預期效果：")
print("  - 模型能正確區分單一/雙/三標的FCN的風險結構")
print("  - Worst-of邏輯被Basket_Worst_IV捕捉")
print("  - 分散效果被Correlation features捕捉")

print("\n" + "=" * 80)
print("變長資產籃處理完成！")
print("=" * 80)
