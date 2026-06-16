import pickle
import os
import numpy as np
import gc
import multiprocessing as mp
import time
import xarray # xarrayを扱うためにインポート

# --- 設定項目 ---
pickle_directory = './output_multiplied_180x360/vflx/'
start_year = 1940
end_year = 2025
input_filename_format = '{year}_multiplied_vflx.pkl'
output_filename_format = '{year}_filled_vflx.pkl'
max_iterations = 1000
tolerance = 1e-7
kmt_data_path = 'kmt_data.txt'
lsm_path = 'lsm_180x360.nc'

# --- マスクとインデックスの準備 ---
def prepare_masks_and_indices(kmt_path, nc_lsm_path):
    print("Preparing masks and indices...")
    try:
        top = np.full((15, 360), 0); bottom = np.full((10, 360), 0)
        data = np.loadtxt(kmt_path, dtype='int')
        estocmask = np.append(np.append(top, data, axis=0), bottom, axis=0)
        estoclandmask = (estocmask == 0)
    except Exception as e: print(f"Error generating estoclandmask: {e}"); return None
    if not os.path.exists(nc_lsm_path): print(f"Error: {nc_lsm_path} not found"); return None
    try:
        with xarray.open_dataset(nc_lsm_path) as ds: lsm_data = ds['lsm'].values
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

# --- ヘルパー関数 ---
def add_periodic_boundary(grid_2d):
    rows, cols = grid_2d.shape
    left = grid_2d[:, 0].reshape(rows, 1); right = grid_2d[:, cols-1].reshape(rows, 1)
    return np.hstack([right, grid_2d, left])

# --- 年単位の処理関数 ---
def process_single_year(args):
    year, config = args
    pickle_dir, input_format, output_format = config['pickle_directory'], config['input_filename_format'], config['output_filename_format']
    landindex, estocweight_orig_362 = config['landindex'], config['estocweight_orig_362']
    max_iter, tol = config['max_iterations'], config['tolerance']

    input_pickle_file_path = os.path.join(pickle_dir, input_format.format(year=year))
    output_pickle_file_path = os.path.join(pickle_dir, output_format.format(year=year))
    log_prefix = f"[Year {year}]"

    if not os.path.exists(input_pickle_file_path):
        return f"Skipped: {year} (File not found)"

    try:
        print(f"{log_prefix} Processing...")
        with open(input_pickle_file_path, 'rb') as f:
            year_data = pickle.load(f)

        filled_yearly_data = {'year': year, 'calculated_monthly_results_filled': {}}
        period_key_map = {'1_to_10': 'days_1_10_avg', '11_to_20': 'days_11_20_avg', '21_to_end': 'days_21_end_avg'}

        for month_idx in range(12):
            month_num = month_idx + 1
            filled_yearly_data['calculated_monthly_results_filled'][month_num] = {}
            for period_out, period_in in period_key_map.items():
                if period_in in year_data:
                    xarray_cube = year_data[period_in]
                    monthly_slice_xarray = xarray_cube[month_idx, :, :]
                    original_grid = monthly_slice_xarray.values.copy()
                   
                    if np.isnan(original_grid).any():
                        filled_yearly_data['calculated_monthly_results_filled'][month_num][period_out] = original_grid
                        continue

                    data_362 = add_periodic_boundary(original_grid)
                    data_362_old = data_362.copy()
                    current_estocweight_362 = estocweight_orig_362.copy()
                    converged = False
                    for counter in range(max_iter):
                        resmax = -np.inf
                        estocweight_old_362 = current_estocweight_362.copy()
                        estocweight_old_362[:, 0], estocweight_old_362[:, 361] = estocweight_old_362[:, 360], estocweight_old_362[:, 1]
                        data_362_old[:, :] = data_362[:, :]
                        data_362_old[:, 0], data_362_old[:, 361] = data_362_old[:, 360], data_362_old[:, 1]
                        for i in range(len(landindex[0])):
                            lat, lon_orig = landindex[0][i], landindex[1][i]; lon = lon_orig + 1
                           
                            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★
                            # ★★★ ここを修正: 180 を 179 に変更 ★★★
                            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★
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
                            converged = True; break
                   
                    filled_yearly_data['calculated_monthly_results_filled'][month_num][period_out] = data_362[:, 1:361]
                else:
                    filled_yearly_data['calculated_monthly_results_filled'][month_num][period_out] = np.full((180, 360), np.nan)
       
        with open(output_pickle_file_path, 'wb') as f:
            pickle.dump(filled_yearly_data, f)
       
        print(f"{log_prefix} Successfully processed and saved.")
        return f"Success: {year}"
    except Exception as e:
        import traceback
        print(f"{log_prefix} CRITICAL ERROR: {e}\n{traceback.format_exc()}")
        return f"Error: {year}"

# --- メイン処理 ---
if __name__ == '__main__':
    mp.freeze_support()
    main_start_time = time.time()
    preparation_result = prepare_masks_and_indices(kmt_data_path, lsm_path)
    if preparation_result is None:
        print("Exiting due to error during mask/index preparation."); exit()

    landindex, estocweight_orig_362 = preparation_result
    config = {'pickle_directory': pickle_directory, 'input_filename_format': input_filename_format, 'output_filename_format': output_filename_format, 'landindex': landindex, 'estocweight_orig_362': estocweight_orig_362, 'max_iterations': max_iterations, 'tolerance': tolerance}

    years_to_process = list(range(start_year, end_year + 1))
    num_processes = max(1, mp.cpu_count() - 1)
    print(f"\nProcessing {len(years_to_process)} year-files using up to {num_processes} processes...")
   
    args_list = [(year, config) for year in years_to_process]
    try:
        with mp.Pool(processes=num_processes) as pool:
            results = pool.map(process_single_year, args_list)
       
        print("\n--- Processing Summary ---")
        success_count = sum(1 for r in results if "Success" in r)
        skipped_count = sum(1 for r in results if "Skipped" in r)
        error_count = sum(1 for r in results if "Error" in r)
        print(f"Total years targeted: {len(years_to_process)}")
        print(f"  Successful: {success_count}\n  Skipped (not found): {skipped_count}\n  Errors: {error_count}")
    except Exception as e:
        print(f"\nAn critical error occurred during parallel processing: {e}")

    main_end_time = time.time()
    print(f"\nTotal execution time: {main_end_time - main_start_time:.2f} seconds")
    print("Processing finished.")
