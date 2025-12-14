import pandas as pd
import numpy as np

print("=" * 80)
print("FCN 特徵工程 V2 - 進階特徵")
print("=" * 80)

# 讀取已處理的資料
df = pd.read_excel('FCN_basket_handled.xlsx')
print(f"\n原始資料形狀: {df.shape}")

# ============================================================================
# 1. 時間價值特徵 (Time Value Features)
# ============================================================================
print("\n" + "=" * 80)
print("1. 時間價值特徵 (Time Value Features)")
print("=" * 80)

# 1.1 Tenor的非線性變換
# 波動率隨時間的平方根關係 (來自Black-Scholes)
df['Tenor_Sqrt'] = np.sqrt(df['Tenor (m)'])

# 捕捉長期FCN的非線性風險
df['Tenor_Squared'] = df['Tenor (m)'] ** 2

# 1.2 Non-call 與 Tenor 的交互
# 可提前贖回的期間
df['Callable_Period'] = df['Tenor (m)'] - df['Non-call Periods (m)']

# 可贖回期間佔比 (越高代表越容易提前結束)
df['Callable_Ratio'] = df['Callable_Period'] / df['Tenor (m)']

print("\n【時間價值特徵統計】")
time_features = ['Tenor (m)', 'Tenor_Sqrt', 'Tenor_Squared',
                 'Non-call Periods (m)', 'Callable_Period', 'Callable_Ratio']
print(df[time_features].describe())

print("\n【時間價值特徵與Coupon的相關性】")
time_corr = df[time_features + ['Coupon']].corr()['Coupon'].sort_values(ascending=False)
print(time_corr)

print("\n【Callable_Ratio範例】")
print("短Non-call (1個月) + 長Tenor (12個月):")
example1 = df[(df['Non-call Periods (m)'] == 1) & (df['Tenor (m)'] == 12)][
    ['Tenor (m)', 'Non-call Periods (m)', 'Callable_Period', 'Callable_Ratio', 'Coupon']
].head(3)
print(example1)

print("\n長Non-call (3個月) + 短Tenor (3個月):")
example2 = df[(df['Non-call Periods (m)'] == 3) & (df['Tenor (m)'] == 3)][
    ['Tenor (m)', 'Non-call Periods (m)', 'Callable_Period', 'Callable_Ratio', 'Coupon']
].head(3)
print(example2)

# ============================================================================
# 2. 障礙價距離的標準化 (Normalized Barrier Distance)
# ============================================================================
print("\n" + "=" * 80)
print("2. 障礙價距離的標準化 (Normalized Barrier Distance)")
print("=" * 80)

print("\n【概念說明】")
print("同樣20%的KI距離：")
print("  - 高波動股票(IV=60%)：更容易觸及 → 風險高")
print("  - 低波動股票(IV=30%)：較難觸及 → 風險低")
print("標準化後：用「幾個標準差」來衡量距離")

# 2.1 KI距離標準化
# KI_Distance_Std = (Strike - KI_Barrier) / (σ * sqrt(T))
# 代表「敲入點距離現價幾個標準差」

# 年化波動率調整
df['Annualized_Vol_Factor'] = df['Basket_Worst_IV'] / 100 * np.sqrt(df['Tenor (m)'] / 12)

# KI距離（百分比）
df['KI_Distance_Pct'] = df['Strike (%)'] - df['KI Barrier (%)']

# 標準化KI距離（幾個標準差）
df['KI_Distance_Std'] = df['KI_Distance_Pct'] / 100 / df['Annualized_Vol_Factor']

# 2.2 KO距離標準化
df['KO_Distance_Pct'] = df['KO Barrier (%)'] - df['Strike (%)']
df['KO_Distance_Std'] = df['KO_Distance_Pct'] / 100 / df['Annualized_Vol_Factor']

print("\n【標準化距離統計】")
barrier_std_features = ['KI_Distance_Pct', 'KI_Distance_Std',
                        'KO_Distance_Pct', 'KO_Distance_Std',
                        'Annualized_Vol_Factor']
print(df[barrier_std_features].describe())

print("\n【標準化距離與Coupon的相關性】")
barrier_std_corr = df[barrier_std_features + ['Coupon']].corr()['Coupon'].sort_values(ascending=False)
print(barrier_std_corr)

print("\n【標準化的效果驗證】")
print("高波動 + 短距離 vs 低波動 + 長距離:")

# 找出高IV低KI距離的案例
high_iv_mask = df['Basket_Worst_IV'] > df['Basket_Worst_IV'].quantile(0.75)
low_ki_dist_mask = df['KI_Distance_Pct'] < df['KI_Distance_Pct'].quantile(0.25)

print("\n高波動 + 小KI距離 (高風險):")
high_risk = df[high_iv_mask & low_ki_dist_mask][
    ['Basket_Worst_IV', 'KI_Distance_Pct', 'KI_Distance_Std', 'Coupon']
].head(3)
print(high_risk)

# 找出低IV高KI距離的案例
low_iv_mask = df['Basket_Worst_IV'] < df['Basket_Worst_IV'].quantile(0.25)
high_ki_dist_mask = df['KI_Distance_Pct'] > df['KI_Distance_Pct'].quantile(0.75)

print("\n低波動 + 大KI距離 (低風險):")
low_risk = df[low_iv_mask & high_ki_dist_mask][
    ['Basket_Worst_IV', 'KI_Distance_Pct', 'KI_Distance_Std', 'Coupon']
].head(3)
print(low_risk)

# ============================================================================
# 3. 隱含波動率曲面特徵 (IV Surface Features)
# ============================================================================
print("\n" + "=" * 80)
print("3. 隱含波動率曲面特徵 (IV Surface Features)")
print("=" * 80)

print("\n【概念說明】")
print("IV Skew (Put-Call IV差異)：")
print("  - Skew > 0：市場預期下跌風險大於上漲")
print("  - Skew越大：市場越恐慌，敲入風險越高")

# 3.1 計算每個標的的IV Skew
# IV_Skew = Put IV - Call IV

# 標的1的Skew
df['IV_Skew_1'] = df['PUT_IMP_VOL_2M_25D'] - df['CALL_IMP_VOL_2M_25D']

# 標的2的Skew
df['IV_Skew_2'] = df['PUT_IMP_VOL_2M_25D_2'] - df['CALL_IMP_VOL_2M_25D_2']

# 標的3的Skew
df['IV_Skew_3'] = df['PUT_IMP_VOL_2M_25D_3'] - df['CALL_IMP_VOL_2M_25D_3']

# 3.2 Basket層級的IV Skew聚合
def safe_mean(row, cols):
    values = [row[col] for col in cols if pd.notna(row[col])]
    return np.mean(values) if values else np.nan

def safe_max(row, cols):
    values = [row[col] for col in cols if pd.notna(row[col])]
    return max(values) if values else np.nan

skew_cols = ['IV_Skew_1', 'IV_Skew_2', 'IV_Skew_3']

# 平均Skew
df['Basket_Avg_Skew'] = df.apply(lambda row: safe_mean(row, skew_cols), axis=1)

# 最大Skew (最悲觀的標的)
df['Basket_Max_Skew'] = df.apply(lambda row: safe_max(row, skew_cols), axis=1)

print("\n【IV Skew統計】")
skew_features = ['IV_Skew_1', 'IV_Skew_2', 'IV_Skew_3', 'Basket_Avg_Skew', 'Basket_Max_Skew']
print(df[skew_features].describe())

print("\n【IV Skew與Coupon的相關性】")
skew_corr = df[skew_features + ['Coupon']].corr()['Coupon'].sort_values(ascending=False)
print(skew_corr)

# 3.3 IV Premium (隱含波動率溢價)
# IV相對於歷史波動率的高估程度
# IV_Premium = (IV - HV) / HV

df['IV_Premium_1'] = (df['PUT_IMP_VOL_3M'] - df['VOLATILITY_90D']) / df['VOLATILITY_90D']
df['IV_Premium_2'] = (df['PUT_IMP_VOL_3M_2'] - df['VOLATILITY_90D_2']) / df['VOLATILITY_90D_2']
df['IV_Premium_3'] = (df['PUT_IMP_VOL_3M_3'] - df['VOLATILITY_90D_3']) / df['VOLATILITY_90D_3']

premium_cols = ['IV_Premium_1', 'IV_Premium_2', 'IV_Premium_3']

# 平均IV Premium
df['Basket_Avg_IV_Premium'] = df.apply(lambda row: safe_mean(row, premium_cols), axis=1)

# 最大IV Premium (最貴的選擇權)
df['Basket_Max_IV_Premium'] = df.apply(lambda row: safe_max(row, premium_cols), axis=1)

print("\n【IV Premium統計】")
premium_features = ['IV_Premium_1', 'Basket_Avg_IV_Premium', 'Basket_Max_IV_Premium']
print(df[premium_features].describe())

print("\n【IV Premium與Coupon的相關性】")
premium_corr = df[premium_features + ['Coupon']].corr()['Coupon'].sort_values(ascending=False)
print(premium_corr)

print("\n【IV Premium解釋】")
print("IV_Premium > 0：隱含波動率 > 歷史波動率（市場預期未來波動加大）")
print("IV_Premium < 0：隱含波動率 < 歷史波動率（市場預期未來波動減小）")

# ============================================================================
# 4. 綜合檢查新增特徵
# ============================================================================
print("\n" + "=" * 80)
print("4. 新增特徵總覽")
print("=" * 80)

new_features_v2 = [
    # 時間價值特徵
    'Tenor_Sqrt', 'Tenor_Squared', 'Callable_Period', 'Callable_Ratio',
    # 標準化障礙距離
    'Annualized_Vol_Factor', 'KI_Distance_Pct', 'KI_Distance_Std',
    'KO_Distance_Pct', 'KO_Distance_Std',
    # IV曲面特徵
    'IV_Skew_1', 'IV_Skew_2', 'IV_Skew_3', 'Basket_Avg_Skew', 'Basket_Max_Skew',
    'IV_Premium_1', 'IV_Premium_2', 'IV_Premium_3',
    'Basket_Avg_IV_Premium', 'Basket_Max_IV_Premium'
]

print(f"\n本次新增特徵數量: {len(new_features_v2)}")
print("\n特徵列表:")
for i, feat in enumerate(new_features_v2, 1):
    print(f"  {i:2d}. {feat}")

# ============================================================================
# 5. 所有新特徵與Coupon的相關性排名
# ============================================================================
print("\n" + "=" * 80)
print("5. 新增特徵與Coupon相關性排名")
print("=" * 80)

all_new_corr = df[new_features_v2 + ['Coupon']].corr()['Coupon'].drop('Coupon')
all_new_corr_sorted = all_new_corr.abs().sort_values(ascending=False)

print("\n【絕對值相關性排序】")
for i, (feat, abs_corr) in enumerate(all_new_corr_sorted.items(), 1):
    actual_corr = all_new_corr[feat]
    print(f"{i:2d}. {feat:30s} {actual_corr:7.4f} (|{abs_corr:.4f}|)")

# ============================================================================
# 6. 儲存資料
# ============================================================================
print("\n" + "=" * 80)
print("6. 儲存資料")
print("=" * 80)

output_file = 'FCN_features_v2.xlsx'
df.to_excel(output_file, index=False)

print(f"\n資料已儲存至: {output_file}")
print(f"最終形狀: {df.shape}")

# ============================================================================
# 7. 總結
# ============================================================================
print("\n" + "=" * 80)
print("7. V2特徵工程總結")
print("=" * 80)

print("\n✅ 時間價值特徵:")
print("  - Tenor_Sqrt: 波動率的時間平方根效應 (Black-Scholes基礎)")
print("  - Tenor_Squared: 長期FCN的非線性風險")
print("  - Callable_Period/Ratio: 可提前贖回的時間結構")

print("\n✅ 標準化障礙距離:")
print("  - KI_Distance_Std: 敲入距離「幾個標準差」")
print("  - KO_Distance_Std: 敲出距離「幾個標準差」")
print("  → 自動考慮波動率和時間的影響！")

print("\n✅ IV曲面特徵:")
print("  - IV_Skew: Put-Call IV差異，捕捉市場恐慌程度")
print("  - IV_Premium: IV相對HV的溢價，捕捉市場預期")

print("\n🎯 預期效果:")
print("  - KI_Distance_Std直接對應敲入機率")
print("  - IV_Skew捕捉市場對下跌的定價")
print("  - 時間特徵降低模型學習非線性關係的難度")

print("\n" + "=" * 80)
print("V2特徵工程完成！")
print("=" * 80)
