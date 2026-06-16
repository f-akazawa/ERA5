import os
import pickle
import numpy as np
import xarray as xr
from tqdm import tqdm

# --- 1. 設定項目 ---

# ★★★ リサイズしたい uflx, vflx ファイルが入っている親ディレクトリ ★★★
input_base_directory = './output_multiplied'

# ★★★ リサイズ後のファイルを保存するディレクトリ ★★★
output_directory = './output_multiplied_180x360'

# 【要設定】元の座標情報を取得するためのお手本となる元データファイルがあるディレクトリ
coord_ref_directory = '../10dy/10dy_dswrf'

# 処理対象の年範囲
start_year = 2024
end_year = 2025

# --- 2. 目標グリッドの定義 ---
target_lat = np.linspace(89.5, -89.5, 180)
target_lon = np.linspace(0.5, 359.5, 360)

# --- 処理開始 ---
os.makedirs(output_directory, exist_ok=True)
print(f"リグリッド処理を開始します。出力先: '{output_directory}'")

# 年ごとにループ
for year in tqdm(range(start_year, end_year + 1), desc="年を処理中"):

    # --- 3. 元の座標を取得 ---
    coord_ref_path = os.path.join(coord_ref_directory, f'dswrf_10dy_{year}.pkl')
    if not os.path.exists(coord_ref_path):
        print(f"\n座標お手本ファイルが見つかりません: {coord_ref_path}。 {year}年をスキップします。")
        continue
   
    try:
        with open(coord_ref_path, 'rb') as f:
            ref_data = pickle.load(f)
        sample_xarray = ref_data['days_1_10_avg']
        source_lat = sample_xarray.coords['latitude'].values
        source_lon = sample_xarray.coords['longitude'].values
        # 座標取得は一度で良いので、成功したらメッセージは表示しない
    except Exception as e:
        print(f"\n座標の取得に失敗しました: {coord_ref_path}。{year}年をスキップします。エラー: {e}")
        continue

    # --- 4. ★★★ uflx と vflx の両方を処理するように設定 ★★★ ---
    files_to_process = {
        'uflx': '{year}_multiplied_uflx.pkl',
        'vflx': '{year}_multiplied_vflx.pkl'
    }

    for var_name, filename_format in files_to_process.items():
        # 入力パス: ./output_multiplied/uflx/{year}_multiplied_uflx.pkl
        high_res_path = os.path.join(input_base_directory, var_name, filename_format.format(year=year))
        # 出力パス: ./output_multiplied_180x360/uflx/{year}_multiplied_uflx.pkl
        output_dir_for_var = os.path.join(output_directory, var_name)
        low_res_path = os.path.join(output_dir_for_var, filename_format.format(year=year))

        if not os.path.exists(high_res_path):
            continue

        os.makedirs(output_dir_for_var, exist_ok=True)

        # 高解像度データを読み込む
        with open(high_res_path, 'rb') as f:
            high_res_data = pickle.load(f)

        # リサイズ後のデータを格納する新しい辞書を準備
        regridded_data = {}

        # ★★★ 5. データ構造の違いに対応 ★★★
        # high_res_data は {'days_1_10_avg': <DataArray>, ...} という構造
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

print(f"\n✅ 全てのリグリッド処理が完了しました。出力先: '{output_directory}'")
