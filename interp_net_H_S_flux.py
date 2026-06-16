import os
import pickle
import numpy as np
import xarray as xr
from tqdm import tqdm

# --- 1. 設定項目 ---

# 【要設定】リサイズしたい高解像度PKLファイルが入っているディレクトリ
input_directory = './output_fluxes'

# 【要設定】リサイズ後の180x360解像度のPKLファイルを保存するディレクトリ (なければ作成)
output_directory = './output_fluxes_180x360'

# 【要設定】元の座標情報を取得するためのお手本となる元データファイルがあるディレクトリ
# dswrf, uswrf など、どれか1種類の元データディレクトリを指定してください。
coord_ref_directory = '../10dy/10dy_dswrf'

# 処理対象の年範囲
start_year = 2024
end_year = 2025

# --- 2. 目標グリッドの定義 ---
# ESTOCの180x360グリッドに合わせた緯度経度を定義
target_lat = np.linspace(89.5, -89.5, 180)
target_lon = np.linspace(0.5, 359.5, 360)

# --- 処理開始 ---

os.makedirs(output_directory, exist_ok=True)
print(f"リグリッド処理を開始します。 入力元: '{input_directory}', 出力先: '{output_directory}'")

# 年ごとにループ
for year in tqdm(range(start_year, end_year + 1), desc="年を処理中"):

    # --- 3. 元の座標を取得 ---
    # 各年のお手本座標ファイルを探す
    coord_ref_filename = f'dswrf_10dy_{year}.pkl'
    coord_ref_path = os.path.join(coord_ref_directory, coord_ref_filename)

    if not os.path.exists(coord_ref_path):
        print(f"\n座標お手本ファイルが見つかりません: {coord_ref_path}。 {year}年をスキップします。")
        continue
   
    try:
        with open(coord_ref_path, 'rb') as f:
            ref_data = pickle.load(f)
        # 最初のデータから座標を抽出
        sample_xarray = ref_data['days_1_10_avg'][0, :, :] # 1月のデータをサンプルとして使用
        source_lat = sample_xarray.coords['latitude'].values
        source_lon = sample_xarray.coords['longitude'].values
    except Exception as e:
        print(f"\n座標の取得に失敗しました: {coord_ref_path}。{year}年をスキップします。エラー: {e}")
        continue

    # --- 4. NetHeatFlux と NetSolarFlux の両方を処理 ---
    file_types_to_process = {
        'NetHeatFlux': '{year}_NetHeatFlux_period_averages.pkl',
        'NetSolarFlux': '{year}_NetSolarFlux_period_averages.pkl'
    }

    for name, filename_format in file_types_to_process.items():
        high_res_path = os.path.join(input_directory, filename_format.format(year=year))
        low_res_path = os.path.join(output_directory, filename_format.format(year=year))

        if not os.path.exists(high_res_path):
            continue # 処理対象ファイルがなければ次へ

        # 高解像度データを読み込む
        with open(high_res_path, 'rb') as f:
            high_res_data = pickle.load(f)

        # リサイズ後のデータを格納する新しい辞書を準備
        regridded_data = {
            'year': year,
            'monthly_averages': {}
        }

        # 月と期間でループして、各データをリサイズ
        for month in range(1, 13):
            regridded_data['monthly_averages'][month] = {}
            for period in ['days_1_10_avg', 'days_11_20_avg', 'days_21_end_avg']:
               
                # 元のデータを取得
                high_res_np = high_res_data['monthly_averages'][month][period]
               
                if isinstance(high_res_np, np.ndarray):
                    # 元の座標を持つxarray.DataArrayを一時的に作成
                    high_res_xr = xr.DataArray(
                        high_res_np,
                        coords=[source_lat, source_lon],
                        dims=['lat', 'lon']
                    )
                    # 目標グリッドに補間（リグリッド）
                    low_res_xr = high_res_xr.interp(lat=target_lat, lon=target_lon, method='linear')
                   
                    # 新しい辞書にNumpy配列として格納
                    regridded_data['monthly_averages'][month][period] = low_res_xr.values
                else:
                    # データが配列でない場合（NaNなど）はそのままコピー
                    regridded_data['monthly_averages'][month][period] = high_res_np

        # リグリッド済みのデータを新しいPickleファイルとして保存
        with open(low_res_path, 'wb') as f:
            pickle.dump(regridded_data, f)

print("全てのリグリッド処理が完了しました。")

