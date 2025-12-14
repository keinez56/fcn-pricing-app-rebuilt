import pandas as pd
import numpy as np

print("=" * 80)
print("FCN 特徵工程")
print("=" * 80)

# 讀取前處理後的有效資料
df = pd.read_excel('FCN_preprocessed_valid.xlsx')
print(f"\n原始資料形狀: {df.shape}")

# ============================================================================
# 1. 年化費用特徵 (Annualized Fee) - 最關鍵的特徵
# ============================================================================
print("\n" + "=" * 80)
print("1. 年化費用特徵 (Annualized Fee)")
print("=" * 80)

# Cost (%) 代表客戶支付的價格，100 - Cost 就是費用
# 例如：Cost = 99 表示支付 99%，費用 = 1%
# 年化費用 = (100 - Cost) / Tenor * 12

df['Fee'] = 100 - df['Cost (%)']
df['Annualized_Fee'] = (df['Fee'] / df['Tenor (m)']) * 12

print("\n【年化費用統計】")
print(df[['Cost (%)', 'Tenor (m)', 'Fee', 'Annualized_Fee', 'Coupon']].describe())

print("\n【年化費用範例】")
print("\n短期 FCN (3個月):")
short_term = df[df['Tenor (m)'] == 3][['Cost (%)', 'Tenor (m)', 'Fee', 'Annualized_Fee', 'Coupon']].head(3)
print(short_term)

print("\n長期 FCN (12個月):")
long_term = df[df['Tenor (m)'] == 12][['Cost (%)', 'Tenor (m)', 'Fee', 'Annualized_Fee', 'Coupon']].head(3)
print(long_term)

# 計算相關性
corr_fee_coupon = df[['Fee', 'Annualized_Fee', 'Coupon']].corr()
print("\n【與Coupon的相關性】")
print(corr_fee_coupon['Coupon'].sort_values(ascending=False))

# ============================================================================
# 2. 障礙價相關特徵 (Barrier Features)
# ============================================================================
print("\n" + "=" * 80)
print("2. 障礙價相關特徵")
print("=" * 80)

# 2.1 KO-Strike 距離 (敲出空間)
df['KO_Strike_Distance'] = df['KO Barrier (%)'] - df['Strike (%)']

# 2.2 Strike-KI 距離 (敲入緩衝)
df['Strike_KI_Distance'] = df['Strike (%)'] - df['KI Barrier (%)']

# 2.3 KO-KI 總範圍
df['KO_KI_Range'] = df['KO Barrier (%)'] - df['KI Barrier (%)']

# 2.4 風險係數：KI相對於Strike的比例 (越低越危險)
df['KI_Strike_Ratio'] = df['KI Barrier (%)'] / df['Strike (%)']

# 2.5 安全係數：KO相對於Strike的比例 (越高越容易敲出)
df['KO_Strike_Ratio'] = df['KO Barrier (%)'] / df['Strike (%)']

print("\n【障礙價特徵統計】")
barrier_features = ['KO_Strike_Distance', 'Strike_KI_Distance', 'KO_KI_Range',
                   'KI_Strike_Ratio', 'KO_Strike_Ratio']
print(df[barrier_features].describe())

print("\n【障礙價特徵與Coupon的相關性】")
barrier_corr = df[barrier_features + ['Coupon']].corr()['Coupon'].sort_values(ascending=False)
print(barrier_corr)

# ============================================================================
# 3. 波動率相關特徵 (Volatility Features)
# ============================================================================
print("\n" + "=" * 80)
print("3. 波動率相關特徵")
print("=" * 80)

# 3.1 多標的平均波動率
# 對於有多個標的的情況，計算平均隱含波動率
df['Avg_IV_3M'] = df[['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']].mean(axis=1, skipna=True)
df['Avg_Historical_Vol_90D'] = df[['VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3']].mean(axis=1, skipna=True)

# 3.2 最大/最小波動率 (worst case)
df['Max_IV_3M'] = df[['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']].max(axis=1, skipna=True)
df['Min_IV_3M'] = df[['PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3']].min(axis=1, skipna=True)

# 3.3 波動率差異 (標的間的波動率分散度)
df['IV_Spread'] = df['Max_IV_3M'] - df['Min_IV_3M']

# 3.4 隱含波動率 vs 歷史波動率比例
df['IV_HV_Ratio'] = df['Avg_IV_3M'] / df['Avg_Historical_Vol_90D']

# 3.5 最大相關係數 (標的間的相關性)
df['Max_Correlation'] = df[['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3']].max(axis=1, skipna=True)
df['Min_Correlation'] = df[['CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3']].min(axis=1, skipna=True)

print("\n【波動率特徵統計】")
vol_features = ['Avg_IV_3M', 'Avg_Historical_Vol_90D', 'Max_IV_3M', 'Min_IV_3M',
                'IV_Spread', 'IV_HV_Ratio', 'Max_Correlation', 'Min_Correlation']
print(df[vol_features].describe())

print("\n【波動率特徵與Coupon的相關性】")
vol_corr = df[vol_features + ['Coupon']].corr()['Coupon'].sort_values(ascending=False)
print(vol_corr)

# ============================================================================
# 4. 期限相關特徵 (Tenor Features)
# ============================================================================
print("\n" + "=" * 80)
print("4. 期限相關特徵")
print("=" * 80)

# 4.1 Non-call比例
df['NonCall_Ratio'] = df['Non-call Periods (m)'] / df['Tenor (m)']

# 4.2 年化波動率 (調整期限影響)
# 波動率通常以年為單位，但期限不同時風險不同
# sqrt(Tenor/12) 是時間平方根調整
df['Annualized_Vol'] = df['Avg_IV_3M'] * np.sqrt(df['Tenor (m)'] / 12)

print("\n【期限特徵統計】")
tenor_features = ['NonCall_Ratio', 'Annualized_Vol']
print(df[tenor_features].describe())

print("\n【期限特徵與Coupon的相關性】")
tenor_corr = df[tenor_features + ['Coupon']].corr()['Coupon'].sort_values(ascending=False)
print(tenor_corr)

# ============================================================================
# 5. 風險評分特徵 (Risk Score)
# ============================================================================
print("\n" + "=" * 80)
print("5. 複合風險評分")
print("=" * 80)

# 5.1 敲入風險分數：波動率高 + KI barrier高 = 高風險
# 標準化後的綜合風險
df['KI_Risk_Score'] = (df['Avg_IV_3M'] / df['Avg_IV_3M'].mean()) * (df['KI Barrier (%)'] / 100)

# 5.2 收益潛力分數：KO barrier高 = 不容易提前結束 = 能收更多coupon
df['Return_Potential'] = (df['KO Barrier (%)'] / 100) * (df['Tenor (m)'] / 12)

print("\n【風險評分統計】")
risk_features = ['KI_Risk_Score', 'Return_Potential']
print(df[risk_features].describe())

print("\n【風險評分與Coupon的相關性】")
risk_corr = df[risk_features + ['Coupon']].corr()['Coupon'].sort_values(ascending=False)
print(risk_corr)

# ============================================================================
# 6. 類別變數編碼
# ============================================================================
print("\n" + "=" * 80)
print("6. 類別變數編碼")
print("=" * 80)

# 6.1 Barrier Type: AKI vs EKI
df['Barrier_Type_AKI'] = (df['Barrier Type'] == 'AKI').astype(int)

print("\n【Barrier Type分佈】")
print(df.groupby('Barrier Type')['Coupon'].agg(['count', 'mean', 'std']))

# ============================================================================
# 7. 檢查新增特徵
# ============================================================================
print("\n" + "=" * 80)
print("7. 新增特徵總覽")
print("=" * 80)

new_features = [
    # 費用特徵
    'Fee', 'Annualized_Fee',
    # 障礙價特徵
    'KO_Strike_Distance', 'Strike_KI_Distance', 'KO_KI_Range',
    'KI_Strike_Ratio', 'KO_Strike_Ratio',
    # 波動率特徵
    'Avg_IV_3M', 'Avg_Historical_Vol_90D', 'Max_IV_3M', 'Min_IV_3M',
    'IV_Spread', 'IV_HV_Ratio', 'Max_Correlation', 'Min_Correlation',
    # 期限特徵
    'NonCall_Ratio', 'Annualized_Vol',
    # 風險評分
    'KI_Risk_Score', 'Return_Potential',
    # 編碼特徵
    'Barrier_Type_AKI'
]

print(f"\n新增特徵數量: {len(new_features)}")
print("\n特徵列表:")
for i, feat in enumerate(new_features, 1):
    print(f"  {i}. {feat}")

# ============================================================================
# 8. 儲存特徵工程後的資料
# ============================================================================
print("\n" + "=" * 80)
print("8. 儲存資料")
print("=" * 80)

output_file = 'FCN_engineered_features.xlsx'
df.to_excel(output_file, index=False)
print(f"\n特徵工程完成！")
print(f"資料已儲存至: {output_file}")
print(f"最終形狀: {df.shape}")

# ============================================================================
# 9. 特徵重要性預覽 (基於相關性)
# ============================================================================
print("\n" + "=" * 80)
print("9. 特徵相關性排名 (Top 20)")
print("=" * 80)

# 選擇所有數值型特徵
numeric_features = df.select_dtypes(include=[np.number]).columns.tolist()
# 移除目標變數和輔助欄位
exclude_cols = ['Coupon', 'Coupon_Valid', 'Coupon p.a. (%)']
feature_cols = [col for col in numeric_features if col not in exclude_cols]

# 計算與Coupon的相關性
correlations = df[feature_cols + ['Coupon']].corr()['Coupon'].drop('Coupon')
correlations_abs = correlations.abs().sort_values(ascending=False)

print("\n【絕對值相關性 Top 20】")
for i, (feat, corr) in enumerate(correlations_abs.head(20).items(), 1):
    actual_corr = correlations[feat]
    print(f"{i:2d}. {feat:30s} {actual_corr:7.4f} (|{corr:.4f}|)")

print("\n" + "=" * 80)
print("特徵工程完成！關鍵洞察:")
print("=" * 80)
print("1. ✅ Annualized_Fee: 消除了Tenor的規模偏差，模型更容易學習費用對Coupon的影響")
print("2. ✅ 障礙價特徵: 將絕對值轉為相對距離和比率，捕捉風險結構")
print("3. ✅ 波動率聚合: 處理多標的情況，提取最大/最小/平均波動率")
print("4. ✅ 複合風險分數: 結合多個維度的風險因子")
print("=" * 80)
