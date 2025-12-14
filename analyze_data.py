import pandas as pd
import os
from datetime import datetime

# 查看IV資料檔案
files = [f for f in os.listdir('iv_data') if f.endswith('.xlsx')]
files.sort()
print('IV資料檔案:')
for f in files:
    print(f)

# 讀取FCN資料
df_fcn = pd.read_excel('FCN資料表.xlsx')
print('\nFCN資料表中的日期:')
print(df_fcn['Pricing Date'].dt.strftime('%Y%m%d').unique())

# 查看第一個IV檔案的詳細結構
print('\n查看20250710.xlsx的結構:')
df_iv = pd.read_excel('iv_data/20250710.xlsx')
print(df_iv.head(10))
