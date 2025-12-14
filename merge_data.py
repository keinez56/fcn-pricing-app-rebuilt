import pandas as pd
import os
from datetime import datetime

print("開始合併FCN資料與IV資料...")

# 讀取FCN資料表
df_fcn = pd.read_excel('FCN資料表.xlsx')
print(f"FCN資料表載入完成: {df_fcn.shape}")

# 建立日期欄位（格式: YYYYMMDD）
df_fcn['Date_Key'] = df_fcn['Pricing Date'].dt.strftime('%Y%m%d')

# 讀取所有IV檔案
iv_files = [f for f in os.listdir('iv_data') if f.endswith('.xlsx')]
iv_files.sort()

all_iv_data = []

for iv_file in iv_files:
    date_key = iv_file.replace('.xlsx', '')
    print(f"\n處理 {iv_file}...")

    # 讀取IV檔案
    df_iv = pd.read_excel(f'iv_data/{iv_file}')

    # 跳過第一行（中文標題）
    df_iv = df_iv.iloc[1:].reset_index(drop=True)

    # 設定欄位名稱
    df_iv.columns = ['BBG_Code', 'PX_LAST', 'PUT_IMP_VOL_3M', 'CALL_IMP_VOL_2M_25D',
                     'PUT_IMP_VOL_2M_25D', 'HIST_PUT_IMP_VOL', 'VOL_STDDEV',
                     'VOLATILITY_90D', 'VOL_PERCENTILE', 'CHG_PCT_1YR',
                     'CORR_COEF', 'DIVIDEND_YIELD']

    # 移除BBG_Code中的" Equity"後綴，保持格式一致（如：AAPL US）
    df_iv['BBG_Code'] = df_iv['BBG_Code'].str.replace(' Equity', '', regex=False)

    # 添加日期key
    df_iv['Date_Key'] = date_key

    print(f"  - 載入 {len(df_iv)} 個標的")
    all_iv_data.append(df_iv)

# 合併所有IV資料
df_iv_all = pd.concat(all_iv_data, ignore_index=True)
print(f"\n所有IV資料合併完成: {df_iv_all.shape}")

# 開始merge：需要針對每個BBG Code欄位進行merge
# FCN資料中最多有3個標的（BBG Code 1-3）

print("\n開始merge FCN資料與IV資料...")

# 先複製FCN資料
df_merged = df_fcn.copy()

# 對每個BBG Code欄位進行merge
for i in range(1, 4):  # BBG Code 1, 2, 3
    bbg_col = f'BBG Code {i}'

    if bbg_col in df_merged.columns:
        print(f"\n處理 {bbg_col}...")

        # Merge IV資料
        df_temp = df_merged.merge(
            df_iv_all,
            left_on=['Date_Key', bbg_col],
            right_on=['Date_Key', 'BBG_Code'],
            how='left',
            suffixes=('', f'_{i}')
        )

        # 重新命名合併的欄位
        for col in ['PX_LAST', 'PUT_IMP_VOL_3M', 'CALL_IMP_VOL_2M_25D',
                    'PUT_IMP_VOL_2M_25D', 'HIST_PUT_IMP_VOL', 'VOL_STDDEV',
                    'VOLATILITY_90D', 'VOL_PERCENTILE', 'CHG_PCT_1YR',
                    'CORR_COEF', 'DIVIDEND_YIELD']:
            if i == 1:
                # 第一個標的不加後綴
                if col in df_temp.columns:
                    continue
            else:
                # 第2、3個標的加後綴
                old_name = f'{col}_{i}' if f'{col}_{i}' in df_temp.columns else col
                new_name = f'{col}_{i}'
                if old_name in df_temp.columns and old_name != new_name:
                    df_temp = df_temp.rename(columns={old_name: new_name})

        # 移除BBG_Code欄位（已經有BBG Code 1/2/3了）
        if 'BBG_Code' in df_temp.columns:
            df_temp = df_temp.drop('BBG_Code', axis=1)

        df_merged = df_temp
        print(f"  - Merge完成，當前形狀: {df_merged.shape}")

# 移除Date_Key（輔助欄位）
if 'Date_Key' in df_merged.columns:
    df_merged = df_merged.drop('Date_Key', axis=1)

print(f"\n最終合併結果: {df_merged.shape}")
print("\n欄位列表:")
for i, col in enumerate(df_merged.columns, 1):
    print(f"{i}. {col}")

# 儲存合併後的資料
output_file = 'FCN_merged_data.xlsx'
df_merged.to_excel(output_file, index=False)
print(f"\n合併資料已儲存至: {output_file}")

# 顯示前幾筆資料
print("\n前3筆資料預覽:")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print(df_merged.head(3))

print("\n資料統計:")
print(f"總筆數: {len(df_merged)}")
print(f"有效Coupon筆數: {len(df_merged[df_merged['Coupon p.a. (%)'] != '-'])}")
print(f"無效Coupon筆數: {len(df_merged[df_merged['Coupon p.a. (%)'] == '-'])}")
