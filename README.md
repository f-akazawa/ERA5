# ERA５データからESTOC用のデータセットを作成するプロジェクト

## 必要な環境
python3.x

xarray

pandas

numpy

kmt_data.txt：ESTOCの海陸を０と１で表現したテキストファイル

## 実行順

ERA5サイトからデータダウンロード（要ユーザー登録）
登録するとAPIキーが発行されるのでPythonスクリプトで複数ダウンロードできるようになる。

FreshWater

１）10日平均ファイルを作成

make10dy_LHTFL.py
make10dy_PRATE.py

1時間ごとのデータなので1日平均を計算したのち、10日平均を作る、結果はPKLファイル

２）FreshWaterの計算

calc_freshwater.py

Lhtfl,prateを利用して計算する（NCEPと同じ計算式）,結果はPKLファイル

３）ERA5のグリッド1440*721 をESTOCのグリッド360*180に合わせる内挿計算

interp_freshwater.py

４）海陸ファイルの作成

make_land_sea_mask.py:ERA5の海陸データをNCファイル形式で保存

resample_lsm.py:ESTOCのサイズに内挿計算(lsm_180x360.ncができる）

５）海陸マスクを作って穴埋め計算

freshwater_filled_multicore.py

６）merge_fw.py

PKLファイルからデータ部分を古い順に連結して一つのNPYファイルにする

７）ESTOC提出用にエンディアン変換と陸地に-1.0e33というありえないデカい値を入れる

byteswap_to_estoc.py


ーーーーーーーーーーー

NetHeatFlux
NetSolarFlux

10日平均をつくるのは同じ

１）DSWRF,DLWRF,USWRF,ULWRF,SHTFL,LHTFLをつかって計算

heat_flux_calc.py

netHeatFlux,netSolarFluxを同時に計算する、結果はPKLファイル

２）ぐりっどをESTOCにあわせる内挿計算

interp_net_H_S_flux.py

３）あなうめ計算

netheatflux_filled_multicore.py
netsolarflux_filled_multicore.py

４）PKLファイルをマージして一つのNPYファイルに変換

merge_nhf.py
merge_nsf.py


５）提出用に変換

byteswap_to_estoc.py


------------------------

SST,Vflux,Uflux

Uflux,Vflux
１）単位変換

UVflux_calc.py

２）ESTOCサイズにリグリッド

interp_UVflux.py

3) 穴埋め計算

Uflux_filled_multicore.py
Vflux_filled_mulitcore.py

4）PKLファイルを１つのNPYファイルにマージ

merge_UVflux.py

5）提出用に変換

byteswap_to_estoc.py


SST

１）グリッドサイズ変更

interp_sst.py

２）穴埋め計算

SST_filled_multicore.py

３）PKLファイルを１つのNPYファイルにマージ

merge_SST.py

４）提出用に変換

byteswap_to_estoc.py

