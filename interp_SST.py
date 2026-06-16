import os
import pickle
import numpy as np
import xarray as xr
from tqdm import tqdm

# --- 1. 設定項目 ---

# 【要設定】リサイズしたいSSTのPKLファイルが入っているディレクトリ
input_directory = '../10dy/10dy_sst'

# 【要設定】リサイズ後の180x360解像度のSSTファイルを保存するディレクトリ (なければ作成)
output_directory = './output_sst_180x360'

# 【要設定】元の座標情報を取得するためのお手本となる元データファイルがあるディレクトリ
# dswrf, uswrf など、どれか1種類の元データディレクトリを指定してください。
coord_ref_directory = '../10dy/10dy_dswrf'

# 処理対象の年範囲
start_year = 2024
end_year = 2025 # 必要に応じて変更してください

# --- 2. 目標グリッドの定義 ---
# ESTOCの180x360グリッドに合わせた緯度経度を定義
target_lat = np.linspace(89.5, -89.5, 180)
target_lon = np.linspace(0.5, 359.5, 360)

# --- 処理開始 ---

os.makedirs(output_directory, exist_ok=True)
print(f"SSTのリグリッド処理を開始します。")
print(f"入力元: '{input_directory}'")
print(f"出力先: '{output_directory}'")

# 年ごとにループ
for year in tqdm(range(start_year, end_year + 1), desc="年を処理中"):

    # --- 3. 元の座標を取得 ---
    # 各年のお手本座標ファイルを探す
    coord_ref_path = os.path.join(coord_ref_directory, f'dswrf_10dy_{year}.pkl')

    if not os.path.exists(coord_ref_path):
        print(f"\n座標お手本ファイルが見つかりません: {coord_ref_path}。 {year}年をスキップします。")
        continue
   
    try:
        with open(coord_ref_path, 'rb') as f:
            ref_data = pickle.load(f)
        # 最初のデータから座標を抽出
        sample_xarray = ref_data['days_1_10_avg']
        source_lat = sample_xarray.coords['latitude'].values
        source_lon = sample_xarray.coords['longitude'].values
    except Exception as e:
        print(f"\n座標の取得に失敗しました: {coord_ref_path}。{year}年をスキップします。エラー: {e}")
        continue

    # --- 4. SSTファイルの処理 ---
    high_res_path = os.path.join(input_directory, f'sst_10dy_{year}.pkl')
    low_res_path = os.path.join(output_directory, f'sst_10dy_{year}_180x360.pkl') # 出力ファイル名を分かりやすく変更

    if not os.path.exists(high_res_path):
        continue # 処理対象ファイルがなければこの年をスキップ

    # 高解像度データを読み込む
    with open(high_res_path, 'rb') as f:
        high_res_data = pickle.load(f)

    # リサイズ後のデータを格納する新しい辞書を準備
    regridded_data = {}

    # ファイル内の各期間キーでループ ('days_1_10_avg'など)
    for period_key, data_cube in high_res_data.items():
       
        # 3次元のデータキューブ全体をリグリッド
        if isinstance(data_cube, xr.DataArray):
            # 目標グリッドに補間（リグリッド）
            low_res_xr = data_cube.interp(latitude=target_lat, longitude=target_lon, method='linear')
           
            # 新しい辞書にxarray.DataArrayとして格納
            regridded_data[period_key] = low_res_xr
        else:
            # データが配列でない場合はそのままコピー
            regridded_data[period_key] = data_cube

    # リグリッド済みのデータを新しいPickleファイルとして保存
    with open(low_res_path, 'wb') as f:
        pickle.dump(regridded_data, f)

print(f"\n✅ 全てのリグリッド処理が完了しました。")

