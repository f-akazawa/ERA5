import os
import pickle
import numpy as np
import xarray as xr
import multiprocessing as mp
import time
from tqdm import tqdm

# --- 1. 設定項目 ---

# ★★★ SSTファイルの情報をここに設定 ★★★
variables_to_process = {
    'sst': {
        'input_dir': './output_sst_180x360',
        'output_dir': './output_filled/sst',
        'input_filename': 'sst_10dy_{year}_180x360.pkl', # リサイズスクリプトの出力ファイル名
        'output_filename': '{year}_filled_sst.pkl'
    }
}

# 処理対象の年範囲
start_year = 2024
end_year = 2025 # 必要に応じて変更してください

# 穴埋め計算のパラメータ
max_iterations = 1000
tolerance = 1e-7

# 穴埋めに使うマスクファイル
kmt_data_path = 'kmt_data.txt'
lsm_path = 'lsm_180x360.nc'

# --- 2. 穴埋め箇所の特定（マスク準備） ---
# この関数はメインの処理が始まる前に一度だけ呼ばれます
def prepare_masks_and_indices(kmt_path, nc_lsm_path):
    print("Preparing masks and indices for hole-filling...")
    try:
        top = np.full((15, 360), 0); bottom = np.full((10, 360), 0)
        data = np.loadtxt(kmt_path, dtype='int')
        estocmask = np.append(np.append(top, data, axis=0), bottom, axis=0)
        estoclandmask = (estocmask == 0)
    except Exception as e: print(f"Error generating estoclandmask: {e}"); return None
    if not os.path.exists(nc_lsm_path): print(f"Error: {nc_lsm_path} not found"); return None
    try:
        with xr.open_dataset(nc_lsm_path) as ds: lsm_data = ds['lsm'].values
        fill_target_mask = (estoclandmask == True) & (lsm_data == 0)
        landindex = np.where(fill_target_mask)
        print(f"Identified {len(landindex[0])} points to fill.")
    except Exception as e: print(f"Error processing lsm.nc: {e}"); return None
    try:
        initial_estocweight = np.where(estoclandmask == True, 0.0, 1.0)
        left_col = initial_estocweight[:, 0].reshape(-1, 1)
        right_col = initial_estocweight[:, 359].reshape(-1, 1)
        estocweight_orig_362 = np.hstack([right_col, initial_estocweight, left_col])
    except Exception as e: print(f"Error preparing weights: {e}"); return None
    return landindex, estocweight_orig_362

# --- 3. ヘルパー関数 ---
def add_periodic_boundary(grid_2d):
    rows, cols = grid_2d.shape
    left = grid_2d[:, 0].reshape(rows, 1); right = grid_2d[:, cols-1].reshape(rows, 1)
    return np.hstack([right, grid_2d, left])

# --- 4. 穴埋め処理のコア関数 ---
# 1年分のファイルを受け取り、中の全データを穴埋めする
def fill_holes_in_year_file(args):
    year, config = args
    # 設定を展開
    input_dir, output_dir = config['input_dir'], config['output_dir']
    input_format, output_format = config['input_filename'], config['output_filename']
    landindex, estocweight_orig_362 = config['landindex'], config['estocweight_orig_362']
    max_iter, tol = config['max_iterations'], config['tolerance']

    input_path = os.path.join(input_dir, input_format.format(year=year))
    output_path = os.path.join(output_dir, output_format.format(year=year))

    if not os.path.exists(input_path):
        return f"Skipped: {year} (File not found)"
    try:
        with open(input_path, 'rb') as f:
            year_data = pickle.load(f)

        filled_yearly_data = {}

        for period_key, data_cube in year_data.items():
            if not isinstance(data_cube, xr.DataArray):
                filled_yearly_data[period_key] = data_cube
                continue

            # 元のxarrayの座標を保持
            original_coords = data_cube.coords
           
            # 結果を格納する空のNumpy配列
            filled_cube_np = np.zeros_like(data_cube.values)

            # 月のループ (12層のデータキューブから各月の2Dデータを取り出す)
            for month_idx in range(12):
                original_grid = data_cube.values[month_idx, :, :]
               
                if np.isnan(original_grid).all():
                    filled_cube_np[month_idx, :, :] = original_grid
                    continue
               
                # --- 穴埋め計算ロジック ---
                data_362 = add_periodic_boundary(original_grid)
                data_362_old = data_362.copy()
                current_estocweight_362 = estocweight_orig_362.copy()
                for _ in range(max_iter):
                    resmax = -np.inf
                    estocweight_old_362 = current_estocweight_362.copy()
                    estocweight_old_362[:, 0], estocweight_old_362[:, 361] = estocweight_old_362[:, 360], estocweight_old_362[:, 1]
                    data_362_old[:, :] = data_362[:, :]
                    data_362_old[:, 0], data_362_old[:, 361] = data_362_old[:, 360], data_362_old[:, 1]
                    for i in range(len(landindex[0])):
                        lat, lon_orig = landindex[0][i], landindex[1][i]; lon = lon_orig + 1
                        if lat == 0 or lat == 179: continue
                        calcflag = (estocweight_old_362[lat-1,lon] + estocweight_old_362[lat+1,lon] + estocweight_old_362[lat,lon-1] + estocweight_old_362[lat,lon+1])
                        if calcflag > 1e-9:
                            calcdata = (data_362_old[lat-1,lon] * estocweight_old_362[lat-1,lon] + data_362_old[lat+1,lon] * estocweight_old_362[lat+1,lon] + data_362_old[lat,lon-1] * estocweight_old_362[lat,lon-1] + data_362_old[lat,lon+1] * estocweight_old_362[lat,lon+1])
                            calcweight = calcdata / calcflag
                            res = abs(data_362_old[lat,lon] - calcweight)
                            data_362[lat,lon] = calcweight
                            current_estocweight_362[lat,lon] = 1.0
                            resmax = max(resmax, res)
                    if resmax < tol:
                        break
                filled_cube_np[month_idx, :, :] = data_362[:, 1:361]
           
            # 穴埋め後のNumpy配列を、元の座標を持つxarray.DataArrayに戻す
            filled_yearly_data[period_key] = xr.DataArray(filled_cube_np, coords=original_coords, dims=data_cube.dims)

        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'wb') as f:
            pickle.dump(filled_yearly_data, f)
       
        return f"Success: {year}"
    except Exception as e:
        return f"Error: {year} ({e})"

# --- 5. メイン処理 ---
if __name__ == '__main__':
    mp.freeze_support()
    main_start_time = time.time()

    # マスクとインデックスを一度だけ準備
    landindex, estocweight_orig_362 = prepare_masks_and_indices(kmt_data_path, lsm_path)
    if landindex is None:
        print("Exiting due to error during mask preparation."); exit()

    # SSTを処理
    for var_name, var_config in variables_to_process.items():
        print(f"\n{'='*20} Starting Hole-Filling for: {var_name.upper()} {'='*20}")
       
        # この変数用の設定を作成
        config = {
            'input_dir': var_config['input_dir'],
            'output_dir': var_config['output_dir'],
            'input_filename': var_config['input_filename'],
            'output_filename': var_config['output_filename'],
            'landindex': landindex,
            'estocweight_orig_362': estocweight_orig_362,
            'max_iterations': max_iterations,
            'tolerance': tolerance
        }
       
        # 処理タスクのリストを作成
        tasks = [(year, config) for year in range(start_year, end_year + 1)]
       
        #num_processes = max(1, mp.cpu_count() - 1)
        num_processes = 84
        print(f"Processing {len(tasks)} files using up to {num_processes} processes...")
       
        results = []
        # tqdmを使って進捗バーを表示
        with mp.Pool(processes=num_processes) as pool:
            results = list(tqdm(pool.imap(fill_holes_in_year_file, tasks), total=len(tasks)))
       
        print(f"\n--- Summary for {var_name.upper()} ---")
        success_count = sum(1 for r in results if "Success" in r)
        skipped_count = sum(1 for r in results if "Skipped" in r)
        error_count = sum(1 for r in results if "Error" in r)
        print(f"  Successful: {success_count}\n  Skipped (not found): {skipped_count}\n  Errors: {error_count}")

    main_end_time = time.time()
    print(f"\n{'='*50}\nTotal execution time: {main_end_time - main_start_time:.2f} seconds")
    print("All hole-filling processing finished.")

