import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("FCN 報價預測模型訓練")
print("=" * 80)

# ============================================================================
# 1. 載入資料
# ============================================================================
print("\n" + "=" * 80)
print("1. 載入資料")
print("=" * 80)

df = pd.read_excel('FCN_features_v3_sorted.xlsx')
print(f"資料形狀: {df.shape}")

# ============================================================================
# 2. 特徵選擇
# ============================================================================
print("\n" + "=" * 80)
print("2. 特徵選擇")
print("=" * 80)

# 定義目標變數
target = 'Coupon'

# 定義不應該作為特徵的欄位
exclude_cols = [
    # 目標變數
    'Coupon', 'Coupon p.a. (%)', 'Coupon_Valid',
    # 日期和識別欄位
    'Pricing Date',
    # 原始BBG Code (類別型，需要特殊處理)
    'BBG Code 1', 'BBG Code 2', 'BBG Code 3',
    # 常數欄位 (只有一個值)
    'Product', 'Currency', 'KO Type',
    # 原始未排序的IV欄位 (使用排序後的版本)
    'PUT_IMP_VOL_3M', 'PUT_IMP_VOL_3M_2', 'PUT_IMP_VOL_3M_3',
    'VOLATILITY_90D', 'VOLATILITY_90D_2', 'VOLATILITY_90D_3',
    'CALL_IMP_VOL_2M_25D', 'CALL_IMP_VOL_2M_25D_2', 'CALL_IMP_VOL_2M_25D_3',
    'PUT_IMP_VOL_2M_25D', 'PUT_IMP_VOL_2M_25D_2', 'PUT_IMP_VOL_2M_25D_3',
    'HIST_PUT_IMP_VOL', 'HIST_PUT_IMP_VOL_2', 'HIST_PUT_IMP_VOL_3',
    'VOL_STDDEV', 'VOL_STDDEV_2', 'VOL_STDDEV_3',
    'VOL_PERCENTILE', 'VOL_PERCENTILE_2', 'VOL_PERCENTILE_3',
    'CHG_PCT_1YR', 'CHG_PCT_1YR_2', 'CHG_PCT_1YR_3',
    'CORR_COEF', 'CORR_COEF_2', 'CORR_COEF_3',
    'DIVIDEND_YIELD', 'DIVIDEND_YIELD_2', 'DIVIDEND_YIELD_3',
    'PX_LAST', 'PX_LAST_2', 'PX_LAST_3',
    'IV_Skew_1', 'IV_Skew_2', 'IV_Skew_3',
    'IV_Premium_1', 'IV_Premium_2', 'IV_Premium_3',
    # 舊的聚合特徵 (使用排序後的更精確)
    'Avg_IV_3M', 'Max_IV_3M', 'Min_IV_3M', 'Avg_Historical_Vol_90D',
    'Basket_Worst_IV', 'Basket_Best_IV', 'Basket_Avg_IV',
    'Basket_Worst_HV', 'Basket_Best_HV', 'Basket_Avg_HV',
]

# 獲取所有數值型特徵
all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

# 過濾出要使用的特徵
feature_cols = [col for col in all_numeric_cols if col not in exclude_cols]

print(f"總欄位數: {len(df.columns)}")
print(f"排除欄位數: {len(exclude_cols)}")
print(f"使用特徵數: {len(feature_cols)}")

# 處理類別變數
print("\n【類別變數處理】")
# Barrier Type 已經有 Barrier_Type_AKI 的編碼

# 顯示最終使用的特徵
print("\n【使用的特徵列表】")
for i, col in enumerate(sorted(feature_cols), 1):
    print(f"  {i:3d}. {col}")

# ============================================================================
# 3. 準備訓練資料
# ============================================================================
print("\n" + "=" * 80)
print("3. 準備訓練資料")
print("=" * 80)

X = df[feature_cols].copy()
y = df[target].copy()

print(f"X shape: {X.shape}")
print(f"y shape: {y.shape}")

# 檢查缺失值
print(f"\n【特徵缺失值統計】")
missing_stats = X.isnull().sum()
missing_features = missing_stats[missing_stats > 0].sort_values(ascending=False)
print(f"有缺失值的特徵數: {len(missing_features)}")
if len(missing_features) > 0:
    print("\nTop 10 缺失特徵:")
    print(missing_features.head(10))

# 分割訓練/測試集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\n訓練集: {X_train.shape}")
print(f"測試集: {X_test.shape}")

# ============================================================================
# 4. 訓練模型
# ============================================================================
print("\n" + "=" * 80)
print("4. 訓練模型")
print("=" * 80)

# 嘗試導入XGBoost
try:
    import xgboost as xgb
    HAS_XGB = True
    print("✅ XGBoost 可用")
except ImportError:
    HAS_XGB = False
    print("❌ XGBoost 不可用")

# 嘗試導入LightGBM
try:
    import lightgbm as lgb
    HAS_LGB = True
    print("✅ LightGBM 可用")
except ImportError:
    HAS_LGB = False
    print("❌ LightGBM 不可用")

# 導入基本模型
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

results = {}

# 4.1 HistGradient Boosting (支援NaN，作為基準)
print("\n【4.1 HistGradient Boosting (sklearn, 支援NaN)】")
from sklearn.ensemble import HistGradientBoostingRegressor

hgb_model = HistGradientBoostingRegressor(
    max_iter=300,
    max_depth=10,
    learning_rate=0.1,
    min_samples_leaf=5,
    random_state=42
)
hgb_model.fit(X_train, y_train)
hgb_pred = hgb_model.predict(X_test)

hgb_rmse = np.sqrt(mean_squared_error(y_test, hgb_pred))
hgb_mae = mean_absolute_error(y_test, hgb_pred)
hgb_r2 = r2_score(y_test, hgb_pred)

print(f"  RMSE: {hgb_rmse:.4f}")
print(f"  MAE:  {hgb_mae:.4f}")
print(f"  R²:   {hgb_r2:.4f}")

results['HistGradient Boosting'] = {'RMSE': hgb_rmse, 'MAE': hgb_mae, 'R2': hgb_r2, 'model': hgb_model}

# 4.2 HistGradient Boosting (更深的樹)
print("\n【4.2 HistGradient Boosting (深層)】")

hgb_deep_model = HistGradientBoostingRegressor(
    max_iter=500,
    max_depth=15,
    learning_rate=0.05,
    min_samples_leaf=3,
    random_state=42
)
hgb_deep_model.fit(X_train, y_train)
hgb_deep_pred = hgb_deep_model.predict(X_test)

hgb_deep_rmse = np.sqrt(mean_squared_error(y_test, hgb_deep_pred))
hgb_deep_mae = mean_absolute_error(y_test, hgb_deep_pred)
hgb_deep_r2 = r2_score(y_test, hgb_deep_pred)

print(f"  RMSE: {hgb_deep_rmse:.4f}")
print(f"  MAE:  {hgb_deep_mae:.4f}")
print(f"  R²:   {hgb_deep_r2:.4f}")

results['HistGradient Boosting Deep'] = {'RMSE': hgb_deep_rmse, 'MAE': hgb_deep_mae, 'R2': hgb_deep_r2, 'model': hgb_deep_model}

# 4.3 XGBoost
if HAS_XGB:
    print("\n【4.3 XGBoost】")
    xgb_model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbosity=0
    )
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)

    xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))
    xgb_mae = mean_absolute_error(y_test, xgb_pred)
    xgb_r2 = r2_score(y_test, xgb_pred)

    print(f"  RMSE: {xgb_rmse:.4f}")
    print(f"  MAE:  {xgb_mae:.4f}")
    print(f"  R²:   {xgb_r2:.4f}")

    results['XGBoost'] = {'RMSE': xgb_rmse, 'MAE': xgb_mae, 'R2': xgb_r2, 'model': xgb_model}

# 4.4 LightGBM
if HAS_LGB:
    print("\n【4.4 LightGBM】")
    lgb_model = lgb.LGBMRegressor(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbosity=-1
    )
    lgb_model.fit(X_train, y_train)
    lgb_pred = lgb_model.predict(X_test)

    lgb_rmse = np.sqrt(mean_squared_error(y_test, lgb_pred))
    lgb_mae = mean_absolute_error(y_test, lgb_pred)
    lgb_r2 = r2_score(y_test, lgb_pred)

    print(f"  RMSE: {lgb_rmse:.4f}")
    print(f"  MAE:  {lgb_mae:.4f}")
    print(f"  R²:   {lgb_r2:.4f}")

    results['LightGBM'] = {'RMSE': lgb_rmse, 'MAE': lgb_mae, 'R2': lgb_r2, 'model': lgb_model}

# ============================================================================
# 5. 模型比較
# ============================================================================
print("\n" + "=" * 80)
print("5. 模型比較")
print("=" * 80)

print("\n【各模型表現】")
print(f"{'模型':<20} {'RMSE':>10} {'MAE':>10} {'R²':>10}")
print("-" * 52)
for name, metrics in sorted(results.items(), key=lambda x: x[1]['R2'], reverse=True):
    print(f"{name:<20} {metrics['RMSE']:>10.4f} {metrics['MAE']:>10.4f} {metrics['R2']:>10.4f}")

# 選擇最佳模型
best_model_name = max(results.keys(), key=lambda x: results[x]['R2'])
best_model = results[best_model_name]['model']
best_r2 = results[best_model_name]['R2']

print(f"\n🏆 最佳模型: {best_model_name} (R² = {best_r2:.4f})")

# ============================================================================
# 6. 交叉驗證
# ============================================================================
print("\n" + "=" * 80)
print("6. 交叉驗證 (5-Fold)")
print("=" * 80)

kfold = KFold(n_splits=5, shuffle=True, random_state=42)

for name, metrics in results.items():
    model = metrics['model']
    cv_scores = cross_val_score(model, X, y, cv=kfold, scoring='r2', n_jobs=-1)
    print(f"{name:<20} CV R² = {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

# ============================================================================
# 7. 特徵重要性分析
# ============================================================================
print("\n" + "=" * 80)
print("7. 特徵重要性分析")
print("=" * 80)

# 使用最佳模型的特徵重要性
if hasattr(best_model, 'feature_importances_'):
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': best_model.feature_importances_
    }).sort_values('importance', ascending=False)

    print(f"\n【{best_model_name} 特徵重要性 Top 25】")
    print(f"{'排名':<5} {'特徵名稱':<40} {'重要性':>10} {'佔比':>10}")
    print("-" * 70)

    total_importance = feature_importance['importance'].sum()
    cumulative = 0
    for i, row in feature_importance.head(25).iterrows():
        rank = feature_importance.index.get_loc(i) + 1
        pct = row['importance'] / total_importance * 100
        cumulative += pct
        print(f"{rank:<5} {row['feature']:<40} {row['importance']:>10.4f} {pct:>9.2f}%")

    print(f"\nTop 25 特徵累積重要性: {cumulative:.2f}%")

    # 儲存特徵重要性
    feature_importance.to_excel('feature_importance.xlsx', index=False)
    print("\n特徵重要性已儲存至: feature_importance.xlsx")

# ============================================================================
# 8. 預測誤差分析
# ============================================================================
print("\n" + "=" * 80)
print("8. 預測誤差分析")
print("=" * 80)

best_pred = best_model.predict(X_test)
errors = y_test - best_pred

print(f"\n【誤差分佈】")
print(f"平均誤差 (Mean Error): {errors.mean():.4f}")
print(f"誤差標準差 (Std):      {errors.std():.4f}")
print(f"最大高估:              {errors.min():.4f}")
print(f"最大低估:              {errors.max():.4f}")

# 誤差百分位數
print(f"\n【誤差百分位數】")
for pct in [5, 25, 50, 75, 95]:
    print(f"  {pct}%: {np.percentile(errors, pct):.4f}")

# 絕對誤差分佈
abs_errors = np.abs(errors)
print(f"\n【絕對誤差分佈】")
print(f"平均絕對誤差 (MAE): {abs_errors.mean():.4f}")
print(f"  < 0.5%:  {(abs_errors < 0.5).sum() / len(abs_errors) * 100:.1f}%")
print(f"  < 1.0%:  {(abs_errors < 1.0).sum() / len(abs_errors) * 100:.1f}%")
print(f"  < 2.0%:  {(abs_errors < 2.0).sum() / len(abs_errors) * 100:.1f}%")
print(f"  < 3.0%:  {(abs_errors < 3.0).sum() / len(abs_errors) * 100:.1f}%")

# ============================================================================
# 9. 儲存模型
# ============================================================================
print("\n" + "=" * 80)
print("9. 儲存模型")
print("=" * 80)

import joblib

# 儲存最佳模型
model_filename = f'fcn_model_{best_model_name.lower().replace(" ", "_")}.pkl'
joblib.dump(best_model, model_filename)
print(f"模型已儲存至: {model_filename}")

# 儲存特徵列表
feature_list_filename = 'model_features.txt'
with open(feature_list_filename, 'w') as f:
    for feat in feature_cols:
        f.write(f"{feat}\n")
print(f"特徵列表已儲存至: {feature_list_filename}")

# 儲存預測結果比較
prediction_df = pd.DataFrame({
    'Actual': y_test.values,
    'Predicted': best_pred,
    'Error': errors.values,
    'Abs_Error': abs_errors.values
})
prediction_df.to_excel('prediction_results.xlsx', index=False)
print(f"預測結果已儲存至: prediction_results.xlsx")

# ============================================================================
# 10. 總結
# ============================================================================
print("\n" + "=" * 80)
print("10. 模型訓練總結")
print("=" * 80)

print(f"""
📊 資料規模:
   - 訓練樣本: {len(X_train)}
   - 測試樣本: {len(X_test)}
   - 特徵數量: {len(feature_cols)}

🏆 最佳模型: {best_model_name}
   - R²:   {results[best_model_name]['R2']:.4f}
   - RMSE: {results[best_model_name]['RMSE']:.4f}
   - MAE:  {results[best_model_name]['MAE']:.4f}

📈 預測準確度:
   - {(abs_errors < 1.0).sum() / len(abs_errors) * 100:.1f}% 的預測誤差 < 1%
   - {(abs_errors < 2.0).sum() / len(abs_errors) * 100:.1f}% 的預測誤差 < 2%

💾 輸出檔案:
   - {model_filename}: 訓練好的模型
   - model_features.txt: 特徵列表
   - feature_importance.xlsx: 特徵重要性
   - prediction_results.xlsx: 預測結果
""")

print("=" * 80)
print("模型訓練完成！")
print("=" * 80)
