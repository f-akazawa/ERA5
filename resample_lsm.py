import xarray as xr
import numpy as np
import os

# --- ユーザー設定 ---

# 1. 入力ファイルと出力ファイルの名前
INPUT_FILE = 'lsm_1940-01-01_12z.nc'
OUTPUT_FILE = 'lsm_180x360.nc'

# 2. NetCDFファイル内の変数名と座標名
#    お使いのファイルに合わせて変更してください
VARIABLE_NAME = 'lsm'       # 陸地マスクデータの変数名
LAT_NAME = 'latitude'     # 緯度座標の名前
LON_NAME = 'longitude'    # 経度座標の名前

# 3. 新しいグリッドの解像度
NEW_LAT_DIM = 180
NEW_LON_DIM = 360

# --- ここからスクリプト本体 ---

def resample_land_sea_mask(input_file, output_file, var_name, lat_name, lon_name, new_lat_dim, new_lon_dim):
    """
    陸地マスクデータを最近傍法でリサンプリングする関数
    """
    if not os.path.exists(input_file):
        print(f"エラー: 入力ファイル '{input_file}' が見つかりません。")
        return

    print(f"入力ファイル '{input_file}' を読み込んでいます...")
    with xr.open_dataset(input_file) as ds:
        # 元のデータ配列を取得
        original_mask = ds[var_name]

        # 新しい緯度・経度の座標を作成
        print(f"新しいグリッド ({new_lat_dim}x{new_lon_dim}) を作成しています...")
        original_lat = ds[lat_name]
        original_lon = ds[lon_name]

        new_latitude = np.linspace(original_lat.min().item(), original_lat.max().item(), new_lat_dim)
        new_longitude = np.linspace(original_lon.min().item(), original_lon.max().item(), new_lon_dim)

        # 内挿処理を実行
        print("「最近傍法」で内挿処理を実行しています...")
        interpolated_mask = original_mask.interp(
            {lat_name: new_latitude, lon_name: new_longitude},
            method='nearest' # ★最近傍法を指定
        )

        # 属性情報を更新
        interpolated_mask.attrs['history'] = f"Resampled to {new_lat_dim}x{new_lon_dim} using nearest neighbor method."

        # 結果を新しいNetCDFファイルとして保存
        print(f"結果を '{output_file}' に保存しています...")
        interpolated_mask.to_netcdf(output_file)

        print("\n処理が完了しました。✨")
        print(f"元の解像度: {original_mask.shape}")
        print(f"新しい解像度: {interpolated_mask.shape}")


if __name__ == '__main__':
    resample_land_sea_mask(
        INPUT_FILE,
        OUTPUT_FILE,
        VARIABLE_NAME,
        LAT_NAME,
        LON_NAME,
        NEW_LAT_DIM,
        NEW_LON_DIM
    )
