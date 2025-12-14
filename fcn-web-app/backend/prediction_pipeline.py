"""
FCN 報價預測 Pipeline
======================
這個模組提供完整的預測流程：
1. 接收使用者輸入的FCN條件
2. 自動查詢對應日期的IV資料
3. 執行特徵工程
4. 預測Coupon

使用方式：
    from prediction_pipeline import FCNPredictor

    predictor = FCNPredictor()

    result = predictor.predict(
        pricing_date='2025-07-10',
        bbg_codes=['NVDA US', 'TSLA US', 'AMD US'],
        strike=95,
        ko_barrier=140,
        ki_barrier=65,
        tenor=6,
        non_call=1,
        cost=99,
        barrier_type='AKI'
    )

    print(f"預測Coupon: {result['predicted_coupon']:.2f}%")
"""

import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class FCNPredictor:
    """FCN報價預測器"""

    def __init__(self, model_path='fcn_model_histgradient_boosting_deep.pkl',
                 iv_data_folder='iv_data'):
        """
        初始化預測器

        Parameters:
        -----------
        model_path : str
            模型檔案路徑
        iv_data_folder : str
            IV資料資料夾路徑
        """
        self.model_path = model_path
        self.iv_data_folder = iv_data_folder

        # 載入模型
        print("載入模型...")
        self.model = joblib.load(model_path)
        print(f"✅ 模型載入成功: {model_path}")

        # 載入特徵列表
        self.feature_cols = self._load_feature_list()
        print(f"✅ 特徵數量: {len(self.feature_cols)}")

        # 快取IV資料
        self.iv_cache = {}

    def _load_feature_list(self):
        """載入特徵列表"""
        with open('model_features.txt', 'r') as f:
            return [line.strip() for line in f.readlines()]

    def _load_iv_data(self, pricing_date):
        """
        載入指定日期的IV資料

        Parameters:
        -----------
        pricing_date : str
            定價日期 (格式: YYYY-MM-DD 或 YYYYMMDD)

        Returns:
        --------
        pd.DataFrame
            IV資料
        """
        # 統一日期格式
        if '-' in pricing_date:
            date_key = pricing_date.replace('-', '')
        else:
            date_key = pricing_date

        # 檢查快取
        if date_key in self.iv_cache:
            return self.iv_cache[date_key]

        # 載入IV檔案
        iv_file = os.path.join(self.iv_data_folder, f'{date_key}.xlsx')

        if not os.path.exists(iv_file):
            raise FileNotFoundError(f"找不到IV資料檔案: {iv_file}")

        df_iv = pd.read_excel(iv_file)

        # 跳過第一行（中文標題）
        df_iv = df_iv.iloc[1:].reset_index(drop=True)

        # 設定欄位名稱
        df_iv.columns = ['BBG_Code', 'PX_LAST', 'PUT_IMP_VOL_3M', 'CALL_IMP_VOL_2M_25D',
                         'PUT_IMP_VOL_2M_25D', 'HIST_PUT_IMP_VOL', 'VOL_STDDEV',
                         'VOLATILITY_90D', 'VOL_PERCENTILE', 'CHG_PCT_1YR',
                         'CORR_COEF', 'DIVIDEND_YIELD']

        # 移除" Equity"後綴
        df_iv['BBG_Code'] = df_iv['BBG_Code'].str.replace(' Equity', '', regex=False)

        # 轉換數值欄位
        numeric_cols = ['PX_LAST', 'PUT_IMP_VOL_3M', 'CALL_IMP_VOL_2M_25D',
                        'PUT_IMP_VOL_2M_25D', 'HIST_PUT_IMP_VOL', 'VOL_STDDEV',
                        'VOLATILITY_90D', 'VOL_PERCENTILE', 'CHG_PCT_1YR',
                        'CORR_COEF', 'DIVIDEND_YIELD']
        for col in numeric_cols:
            df_iv[col] = pd.to_numeric(df_iv[col], errors='coerce')

        # 快取
        self.iv_cache[date_key] = df_iv

        return df_iv

    def _get_stock_iv(self, iv_data, bbg_code):
        """取得特定股票的IV資料"""
        stock_data = iv_data[iv_data['BBG_Code'] == bbg_code]
        if len(stock_data) == 0:
            return None
        return stock_data.iloc[0].to_dict()

    def _compute_features(self, input_data, iv_data_list):
        """
        計算所有特徵

        Parameters:
        -----------
        input_data : dict
            使用者輸入的FCN條件
        iv_data_list : list
            各標的的IV資料 (已按IV降冪排序)

        Returns:
        --------
        pd.DataFrame
            特徵DataFrame (單行)
        """
        features = {}

        # ==================== 基本FCN條件特徵 ====================
        features['Strike (%)'] = input_data['strike']
        features['KO Barrier (%)'] = input_data['ko_barrier']
        features['KI Barrier (%)'] = input_data['ki_barrier']
        features['Tenor (m)'] = input_data['tenor']
        features['Non-call Periods (m)'] = input_data['non_call']
        features['Cost (%)'] = input_data['cost']
        features['Barrier_Type_AKI'] = 1 if input_data['barrier_type'] == 'AKI' else 0

        # ==================== 費用特徵 ====================
        features['Fee'] = 100 - input_data['cost']
        features['Annualized_Fee'] = features['Fee'] / input_data['tenor'] * 12

        # ==================== 時間特徵 ====================
        features['Tenor_Sqrt'] = np.sqrt(input_data['tenor'])
        features['Tenor_Squared'] = input_data['tenor'] ** 2
        features['Callable_Period'] = input_data['tenor'] - input_data['non_call']
        features['Callable_Ratio'] = features['Callable_Period'] / input_data['tenor']
        features['NonCall_Ratio'] = input_data['non_call'] / input_data['tenor']

        # ==================== 障礙價特徵 ====================
        features['KO_Strike_Distance'] = input_data['ko_barrier'] - input_data['strike']
        features['Strike_KI_Distance'] = input_data['strike'] - input_data['ki_barrier']
        features['KO_KI_Range'] = input_data['ko_barrier'] - input_data['ki_barrier']
        features['KI_Strike_Ratio'] = input_data['ki_barrier'] / input_data['strike']
        features['KO_Strike_Ratio'] = input_data['ko_barrier'] / input_data['strike']
        features['KI_Distance_Pct'] = input_data['strike'] - input_data['ki_barrier']
        features['KO_Distance_Pct'] = input_data['ko_barrier'] - input_data['strike']

        # ==================== Basket特徵 ====================
        basket_size = len(iv_data_list)
        features['Basket_Size'] = basket_size
        features['Num_Underlyings'] = basket_size
        features['Basket_Complexity_Factor'] = basket_size / 3.0

        # ==================== 排序後的IV特徵 (Rank_1, 2, 3) ====================
        # IV資料已經按PUT_IMP_VOL_3M降冪排序

        iv_cols_mapping = {
            'PUT_IMP_VOL_3M': 'PUT_IMP_VOL_3M_Rank',
            'CALL_IMP_VOL_2M_25D': 'CALL_IMP_VOL_2M_25D_Rank',
            'PUT_IMP_VOL_2M_25D': 'PUT_IMP_VOL_2M_25D_Rank',
            'HIST_PUT_IMP_VOL': 'HIST_PUT_IMP_VOL_Rank',
            'VOL_STDDEV': 'VOL_STDDEV_Rank',
            'VOLATILITY_90D': 'VOLATILITY_90D_Rank',
            'VOL_PERCENTILE': 'VOL_PERCENTILE_Rank',
            'CHG_PCT_1YR': 'CHG_PCT_1YR_Rank',
            'CORR_COEF': 'CORR_COEF_Rank',
            'DIVIDEND_YIELD': 'DIVIDEND_YIELD_Rank',
            'PX_LAST': 'PX_LAST_Rank',
        }

        for orig_col, rank_prefix in iv_cols_mapping.items():
            for i in range(3):
                rank_col = f'{rank_prefix}_{i+1}'
                if i < basket_size and iv_data_list[i] is not None:
                    features[rank_col] = iv_data_list[i].get(orig_col, np.nan)
                else:
                    features[rank_col] = np.nan

        # ==================== IV Skew 和 Premium ====================
        for i in range(3):
            if i < basket_size and iv_data_list[i] is not None:
                put_iv = iv_data_list[i].get('PUT_IMP_VOL_2M_25D', np.nan)
                call_iv = iv_data_list[i].get('CALL_IMP_VOL_2M_25D', np.nan)
                hist_iv = iv_data_list[i].get('VOLATILITY_90D', np.nan)
                iv_3m = iv_data_list[i].get('PUT_IMP_VOL_3M', np.nan)

                # IV Skew
                if pd.notna(put_iv) and pd.notna(call_iv):
                    features[f'IV_Skew_Rank_{i+1}'] = put_iv - call_iv
                else:
                    features[f'IV_Skew_Rank_{i+1}'] = np.nan

                # IV Premium
                if pd.notna(iv_3m) and pd.notna(hist_iv) and hist_iv != 0:
                    features[f'IV_Premium_Rank_{i+1}'] = (iv_3m - hist_iv) / hist_iv
                else:
                    features[f'IV_Premium_Rank_{i+1}'] = np.nan
            else:
                features[f'IV_Skew_Rank_{i+1}'] = np.nan
                features[f'IV_Premium_Rank_{i+1}'] = np.nan

        # ==================== Basket聚合特徵 ====================
        # 收集有效的IV值
        iv_values = [d.get('PUT_IMP_VOL_3M') for d in iv_data_list if d and pd.notna(d.get('PUT_IMP_VOL_3M'))]
        hv_values = [d.get('VOLATILITY_90D') for d in iv_data_list if d and pd.notna(d.get('VOLATILITY_90D'))]
        corr_values = [d.get('CORR_COEF') for d in iv_data_list if d and pd.notna(d.get('CORR_COEF'))]
        skew_values = [features.get(f'IV_Skew_Rank_{i+1}') for i in range(basket_size)
                       if pd.notna(features.get(f'IV_Skew_Rank_{i+1}'))]
        premium_values = [features.get(f'IV_Premium_Rank_{i+1}') for i in range(basket_size)
                          if pd.notna(features.get(f'IV_Premium_Rank_{i+1}'))]

        # IV相關聚合
        features['IV_Spread'] = max(iv_values) - min(iv_values) if len(iv_values) >= 2 else 0
        features['Basket_IV_Range'] = features['IV_Spread']

        # 相關性聚合
        features['Basket_Avg_Corr'] = np.mean(corr_values) if corr_values else np.nan
        features['Basket_Min_Corr'] = min(corr_values) if corr_values else np.nan
        features['Max_Correlation'] = max(corr_values) if corr_values else np.nan
        features['Min_Correlation'] = min(corr_values) if corr_values else np.nan

        # Skew聚合
        features['Basket_Avg_Skew'] = np.mean(skew_values) if skew_values else np.nan
        features['Basket_Max_Skew'] = max(skew_values) if skew_values else np.nan

        # IV Premium聚合
        features['Basket_Avg_IV_Premium'] = np.mean(premium_values) if premium_values else np.nan
        features['Basket_Max_IV_Premium'] = max(premium_values) if premium_values else np.nan

        # IV/HV比率
        if iv_values and hv_values:
            features['IV_HV_Ratio'] = np.mean(iv_values) / np.mean(hv_values)
        else:
            features['IV_HV_Ratio'] = np.nan

        # ==================== 風險評分特徵 ====================
        # 使用Rank_1 (最高IV)
        rank_1_iv = features.get('PUT_IMP_VOL_3M_Rank_1', np.nan)

        if pd.notna(rank_1_iv):
            # 年化波動因子
            features['Annualized_Vol_Factor'] = rank_1_iv / 100 * np.sqrt(input_data['tenor'] / 12)

            # 標準化KI距離
            if features['Annualized_Vol_Factor'] > 0:
                features['KI_Distance_Std'] = features['KI_Distance_Pct'] / 100 / features['Annualized_Vol_Factor']
                features['KO_Distance_Std'] = features['KO_Distance_Pct'] / 100 / features['Annualized_Vol_Factor']
                features['KI_Distance_Std_Sorted'] = features['KI_Distance_Std']
            else:
                features['KI_Distance_Std'] = np.nan
                features['KO_Distance_Std'] = np.nan
                features['KI_Distance_Std_Sorted'] = np.nan

            # 年化波動率
            features['Annualized_Vol'] = rank_1_iv * np.sqrt(input_data['tenor'] / 12)

            # 相關性調整IV
            if pd.notna(features['Basket_Avg_Corr']) and basket_size > 1:
                features['Corr_Adjusted_IV'] = rank_1_iv * (1 + 0.1 * (basket_size - 1) * (1 - features['Basket_Avg_Corr']))
            else:
                features['Corr_Adjusted_IV'] = rank_1_iv

            # KI風險評分
            features['KI_Risk_Score'] = (rank_1_iv / 43.5) * (input_data['ki_barrier'] / 100)  # 43.5是訓練時的平均IV

            # Basket風險評分
            features['Basket_Risk_Score'] = features['KI_Risk_Score'] * (1 + 0.2 * (basket_size - 1))
            if pd.notna(features['Basket_Avg_Corr']) and basket_size > 1:
                features['Basket_Risk_Score'] *= (1 + 0.1 * (1 - features['Basket_Avg_Corr']))

            # 排序後的風險評分
            features['Risk_Score_Sorted'] = (rank_1_iv / 52.4) * (input_data['ki_barrier'] / 100) * (1 + 0.2 * (basket_size - 1))

        else:
            features['Annualized_Vol_Factor'] = np.nan
            features['KI_Distance_Std'] = np.nan
            features['KO_Distance_Std'] = np.nan
            features['KI_Distance_Std_Sorted'] = np.nan
            features['Annualized_Vol'] = np.nan
            features['Corr_Adjusted_IV'] = np.nan
            features['KI_Risk_Score'] = np.nan
            features['Basket_Risk_Score'] = np.nan
            features['Risk_Score_Sorted'] = np.nan

        # 收益潛力
        features['Return_Potential'] = (input_data['ko_barrier'] / 100) * (input_data['tenor'] / 12)

        # 轉換為DataFrame
        df = pd.DataFrame([features])

        return df

    def predict(self, pricing_date, bbg_codes, strike, ko_barrier, ki_barrier,
                tenor, non_call, cost, barrier_type='AKI'):
        """
        預測FCN的Coupon

        Parameters:
        -----------
        pricing_date : str
            定價日期 (格式: YYYY-MM-DD 或 YYYYMMDD)
        bbg_codes : list
            標的股票代碼列表 (1-3個)，例如 ['NVDA US', 'TSLA US', 'AMD US']
        strike : float
            履約價 (%)
        ko_barrier : float
            敲出障礙價 (%)
        ki_barrier : float
            敲入障礙價 (%)
        tenor : int
            期限 (月)
        non_call : int
            不可贖回期間 (月)
        cost : float
            成本 (%)
        barrier_type : str
            障礙類型 ('AKI' 或 'EKI')

        Returns:
        --------
        dict
            預測結果，包含 predicted_coupon, features, iv_data 等
        """
        # 驗證輸入
        if len(bbg_codes) < 1 or len(bbg_codes) > 3:
            raise ValueError("標的數量必須在1-3之間")

        if barrier_type not in ['AKI', 'EKI']:
            raise ValueError("barrier_type 必須是 'AKI' 或 'EKI'")

        # 載入IV資料
        iv_data = self._load_iv_data(pricing_date)

        # 取得各標的的IV資料
        iv_data_list = []
        for bbg in bbg_codes:
            stock_iv = self._get_stock_iv(iv_data, bbg)
            if stock_iv is None:
                print(f"⚠️ 警告: 找不到 {bbg} 的IV資料")
            iv_data_list.append(stock_iv)

        # 按PUT_IMP_VOL_3M降冪排序
        valid_iv_data = [(i, d) for i, d in enumerate(iv_data_list) if d is not None]
        valid_iv_data.sort(key=lambda x: x[1].get('PUT_IMP_VOL_3M', 0) or 0, reverse=True)
        sorted_iv_data = [d for _, d in valid_iv_data]

        # 填補到3個（用None）
        while len(sorted_iv_data) < 3:
            sorted_iv_data.append(None)

        # 準備輸入資料
        input_data = {
            'strike': strike,
            'ko_barrier': ko_barrier,
            'ki_barrier': ki_barrier,
            'tenor': tenor,
            'non_call': non_call,
            'cost': cost,
            'barrier_type': barrier_type
        }

        # 計算特徵
        features_df = self._compute_features(input_data, sorted_iv_data)

        # 確保特徵順序正確
        X = features_df.reindex(columns=self.feature_cols)

        # 預測
        predicted_coupon = self.model.predict(X)[0]

        # 組織結果
        result = {
            'predicted_coupon': predicted_coupon,
            'input': {
                'pricing_date': pricing_date,
                'bbg_codes': bbg_codes,
                'strike': strike,
                'ko_barrier': ko_barrier,
                'ki_barrier': ki_barrier,
                'tenor': tenor,
                'non_call': non_call,
                'cost': cost,
                'barrier_type': barrier_type
            },
            'sorted_bbg_codes': [bbg_codes[i] for i, _ in valid_iv_data],
            'sorted_ivs': [d.get('PUT_IMP_VOL_3M') if d else None for d in sorted_iv_data],
            'features': features_df.to_dict('records')[0]
        }

        return result

    def batch_predict(self, df_input):
        """
        批量預測

        Parameters:
        -----------
        df_input : pd.DataFrame
            包含所有FCN條件的DataFrame

        Returns:
        --------
        pd.DataFrame
            加入predicted_coupon欄位的DataFrame
        """
        predictions = []

        for idx, row in df_input.iterrows():
            try:
                # 收集BBG codes
                bbg_codes = []
                for i in range(1, 4):
                    col = f'BBG Code {i}'
                    if col in row and pd.notna(row[col]):
                        bbg_codes.append(row[col])

                result = self.predict(
                    pricing_date=row['Pricing Date'].strftime('%Y%m%d') if hasattr(row['Pricing Date'], 'strftime') else str(row['Pricing Date']),
                    bbg_codes=bbg_codes,
                    strike=row['Strike (%)'],
                    ko_barrier=row['KO Barrier (%)'],
                    ki_barrier=row['KI Barrier (%)'],
                    tenor=row['Tenor (m)'],
                    non_call=row['Non-call Periods (m)'],
                    cost=row['Cost (%)'],
                    barrier_type=row['Barrier Type']
                )
                predictions.append(result['predicted_coupon'])
            except Exception as e:
                print(f"警告: 第{idx}筆預測失敗: {e}")
                predictions.append(np.nan)

        df_input['Predicted_Coupon'] = predictions
        return df_input


# ============================================================================
# 測試範例
# ============================================================================
if __name__ == '__main__':
    print("=" * 80)
    print("FCN 報價預測 Pipeline 測試")
    print("=" * 80)

    # 初始化預測器
    predictor = FCNPredictor()

    # 測試案例1: 三標的FCN
    print("\n" + "-" * 40)
    print("測試案例1: 三標的FCN")
    print("-" * 40)

    result1 = predictor.predict(
        pricing_date='2025-07-10',
        bbg_codes=['NVDA US', 'TSLA US', 'AMD US'],
        strike=95,
        ko_barrier=140,
        ki_barrier=65,
        tenor=6,
        non_call=1,
        cost=99,
        barrier_type='AKI'
    )

    print(f"\n輸入條件:")
    print(f"  標的: {result1['input']['bbg_codes']}")
    print(f"  Strike: {result1['input']['strike']}%")
    print(f"  KO Barrier: {result1['input']['ko_barrier']}%")
    print(f"  KI Barrier: {result1['input']['ki_barrier']}%")
    print(f"  Tenor: {result1['input']['tenor']}個月")
    print(f"  Cost: {result1['input']['cost']}%")

    print(f"\n排序後標的 (按IV降冪):")
    for i, (bbg, iv) in enumerate(zip(result1['sorted_bbg_codes'], result1['sorted_ivs'])):
        if iv:
            print(f"  Rank {i+1}: {bbg} (IV={iv:.2f}%)")

    print(f"\n🎯 預測Coupon: {result1['predicted_coupon']:.2f}%")

    # 測試案例2: 雙標的FCN
    print("\n" + "-" * 40)
    print("測試案例2: 雙標的FCN")
    print("-" * 40)

    result2 = predictor.predict(
        pricing_date='2025-07-10',
        bbg_codes=['AAPL US', 'META US'],
        strike=100,
        ko_barrier=110,
        ki_barrier=70,
        tenor=9,
        non_call=1,
        cost=98.5,
        barrier_type='EKI'
    )

    print(f"\n輸入條件:")
    print(f"  標的: {result2['input']['bbg_codes']}")
    print(f"  Strike: {result2['input']['strike']}%")
    print(f"  KO Barrier: {result2['input']['ko_barrier']}%")
    print(f"  KI Barrier: {result2['input']['ki_barrier']}%")

    print(f"\n🎯 預測Coupon: {result2['predicted_coupon']:.2f}%")

    # 測試案例3: 單一標的FCN
    print("\n" + "-" * 40)
    print("測試案例3: 單一標的FCN")
    print("-" * 40)

    result3 = predictor.predict(
        pricing_date='2025-07-10',
        bbg_codes=['NVDA US'],
        strike=90,
        ko_barrier=130,
        ki_barrier=60,
        tenor=12,
        non_call=1,
        cost=99,
        barrier_type='AKI'
    )

    print(f"\n輸入條件:")
    print(f"  標的: {result3['input']['bbg_codes']}")

    print(f"\n🎯 預測Coupon: {result3['predicted_coupon']:.2f}%")

    print("\n" + "=" * 80)
    print("Pipeline 測試完成！")
    print("=" * 80)
