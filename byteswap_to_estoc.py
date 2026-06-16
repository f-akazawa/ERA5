## 提出データ作成のためのbyteswapと書き出し
## ファイル名を書き換えて再利用している
## 提出用データ
## freshwater(prate,lhtflから計算）
## vflux,uflux(単位変換のみNCEPと同じ場合は全グリッドに*10）
## snr (計算式はコード参照、以下同）
## heat(自分のコード上ではghとして計算、提出ファイル名を変更する）

import numpy as np
import os

data = np.load('sst_filled_1940-2025.npy')

mask = np.loadtxt('kmt_data.txt' , dtype='int')
top = np.full((15,360),0)
bottom = np.full((10,360),0)

mask = np.append(top,mask,axis=0)
mask = np.append(mask,bottom,axis=0)
estoclandmask = (mask == 0)

# 陸０のマスクを作る
estocweight = np.where(estoclandmask == True,0,1)

data[:,estocweight == 0] = -1.0e33

# 一番下を削除してサイズを合わせる
for_estoc = data[:,:180,:]

# byteswap
for_estoc = for_estoc.byteswap()

# 書き出し
if os.path.isfile('./SST_1940-2025_big.bin'):
    os.remove('./SST_1940-2025_big.bin')

with open('SST_1940-2025_big.bin' , 'wb') as f:
    for_estoc.tofile(f)

