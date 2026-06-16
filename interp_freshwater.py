import pickle
import xarray as xr
import numpy as np
import os
import multiprocessing
from itertools import repeat

def interpolate_data_in_file(year, input_template, output_prefix, new_lat_dim, new_lon_dim):
    """
    PKLファイル内のxarrayデータを新しい解像度に内挿する。
    処理前に不要な非次元座標を削除し、linspaceには純粋な数値を渡す。
    """
    input_file = input_template.format(year)
    output_file = f"{output_prefix}_{year}.pkl"

    if not os.path.exists(input_file):
        print(f"[{year}年] 入力ファイル {input_file} が見つからないため、スキップします。")
        return f"[{year}年] スキップ"

    print(f"[{year}年] 内挿処理を開始します... ファイル: {input_file}")
    try:
        with open(input_file, 'rb') as f:
            high_res_dict = pickle.load(f)

        interpolated_results = {}
        is_grid_defined = False
        new_latitude, new_longitude = None, None

        for key, high_res_da in high_res_dict.items():
            coords_to_drop = [coord for coord in high_res_da.coords if coord not in high_res_da.dims]
            if coords_to_drop:
                high_res_da = high_res_da.drop_vars(coords_to_drop)

            if 'latitude' in high_res_da.dims and 'longitude' in high_res_da.dims:
                if not is_grid_defined:
                    lat_coords = high_res_da['latitude']
                    lon_coords = high_res_da['longitude']
                   
                    # ★★★ ここが今回の修正点 ★★★
                    # .item() を使って、xarrayオブジェクトから純粋な数値を取り出して渡す
                    new_latitude = np.linspace(lat_coords.min().item(), lat_coords.max().item(), new_lat_dim)
                    new_longitude = np.linspace(lon_coords.min().item(), lon_coords.max().item(), new_lon_dim)
                    # ★★★ 修正ここまで ★★★

                    is_grid_defined = True
               
                # is_grid_definedがFalseのまま（有効な空間データが一つもなかった）場合を考慮
                if not is_grid_defined:
                    interpolated_da = high_res_da.copy()
                else:
                    interpolated_da = high_res_da.interp(
                        latitude=new_latitude,
                        longitude=new_longitude,
                        method='linear'
                    )
            else:
                interpolated_da = high_res_da.copy()
           
            interpolated_results[key] = interpolated_da
       
        with open(output_file, 'wb') as f:
            pickle.dump(interpolated_results, f)
       
        result_message = f"[{year}年] 内挿処理が完了しました。 ✨"
        print(result_message)
        return result_message

    except Exception as e:
        print(f"[{year}年] 処理中にエラーが発生しました。")
        raise e

if __name__ == '__main__':
    # --- ユーザー設定 ---
    START_YEAR = 2024
    END_YEAR = 2025
    NUM_CORES = None
    NEW_LATITUDE_DIM = 180
    NEW_LONGITUDE_DIM = 360
   
    # ご自身のファイル名に合わせてパスを修正してください
    INPUT_FILE_TEMPLATE = '../10dy/10dy_freshwater/freshwater_10dy_{}.pkl'
    OUTPUT_FILENAME_PREFIX = '../10dy/interp_freshwater/freshwater_10dy_interpolated'

    # --- マルチコア処理の実行 ---
    years_to_process = list(range(START_YEAR, END_YEAR + 1))
    args_for_starmap = zip(
        years_to_process,
        repeat(INPUT_FILE_TEMPLATE),
        repeat(OUTPUT_FILENAME_PREFIX),
        repeat(NEW_LATITUDE_DIM),
        repeat(NEW_LONGITUDE_DIM)
    )

    print(f"=== 内挿処理の並列実行 ({START_YEAR}年～{END_YEAR}年) を開始します ===")
    print(f"変換後の解像度: Latitude={NEW_LATITUDE_DIM}, Longitude={NEW_LONGITUDE_DIM}")
    print("-" * 50)

    with multiprocessing.Pool(processes=NUM_CORES) as pool:
        pool.starmap(interpolate_data_in_file, args_for_starmap)

    print("-" * 50)
    print("=== 全ての年の処理が完了しました ===")

