import xarray as xr
import pandas as pd
import pickle
import os
import multiprocessing
from itertools import repeat

def process_precipitation_data(year, file_template, var_name, time_coord_name, output_prefix):
    """
    毎時の降水量NCファイルを読み込み、単位変換、日平均化、月別期間平均化を行い、PKLファイルで保存する。
    """
    input_file = file_template.format(year)
    output_file = f"../10dy/10dy_prate/{output_prefix}_{year}.pkl"

    if not os.path.exists(input_file):
        print(f"[{year}年] 入力ファイル {input_file} が見つからないため、スキップします。")
        return f"[{year}年] スキップ"

    print(f"[{year}年] 処理を開始します... ファイル: {input_file}")
    try:
        # ★★★ 修正点 ★★★
        # データをチャンクで開くことで、メモリ使用量を大幅に削減する
        # これにより、ファイル全体を一度にメモリに読み込まなくなる
        with xr.open_dataset(input_file, chunks={time_coord_name: 'auto'}) as ds:
           
            # 時間座標の名前を'time'に統一
            if time_coord_name in ds.coords and time_coord_name != 'time':
                ds = ds.rename({time_coord_name: 'time'})
                print(f"  - [{year}年] 座標'{time_coord_name}'を'time'にリネームしました。")
           
            # ステップ1: 単位を 'kg m-2 s-1' (mm/s) から 'mm/day' に変換
            print(f"  - [{year}年] 単位変換 (kg m-2 s-1 -> mm/day) を実行中...")
            precip_mm_day = ds[var_name] * 86400
            precip_mm_day.attrs['units'] = 'mm/day'
            precip_mm_day.attrs['long_name'] = 'Daily precipitation rate'

            # ステップ2: 日平均を計算
            print(f"  - [{year}年] 日平均を計算中...")
            daily_data = precip_mm_day.resample(time='D').mean(skipna=True)

            # ステップ3: 月ごとにグループ化し、3期間で平均を計算
            print(f"  - [{year}年] 月別の期間平均を計算中...")
            monthly_groups = daily_data.groupby('time.month')
           
            # .compute() を呼び出すことで、ここまでの遅延計算（Dask）が実行される
            # チャンク処理のため、計算には時間がかかる場合がある
            avg_period1 = monthly_groups.apply(lambda x: x.sel(time=x.time.dt.day.isin(range(1, 11))).mean(dim='time', skipna=True)).compute()
            avg_period2 = monthly_groups.apply(lambda x: x.sel(time=x.time.dt.day.isin(range(11, 21))).mean(dim='time', skipna=True)).compute()
            avg_period3 = monthly_groups.apply(lambda x: x.sel(time=x.time.dt.day >= 21).mean(dim='time', skipna=True)).compute()
           
            final_results = {
                'days_1_10_avg': avg_period1,
                'days_11_20_avg': avg_period2,
                'days_21_end_avg': avg_period3
            }

            # ステップ4: Pickleファイルとして保存
            print(f"  - [{year}年] 結果を {output_file} に保存中...")
            with open(output_file, 'wb') as f:
                pickle.dump(final_results, f)
           
            result_message = f"[{year}年] {output_file} の作成が完了しました。 ✨"
            print(result_message)
            return result_message

    except Exception as e:
        error_message = f"[{year}年] 処理中にエラーが発生しました: {e}"
        print(error_message)
        return error_message

if __name__ == '__main__':
    # --- ユーザー設定 ---
    START_YEAR = 2024
    END_YEAR = 2025

    # ★★★ 追加の対策 ★★★
    # メモリ不足が続く場合、使用するコア数を減らしてみてください。
    # 例えば NUM_CORES = 2 や NUM_CORES = 4 のように設定します。
    NUM_CORES = 40
   
    TIME_COORDINATE_NAME = 'valid_time'
    INPUT_FILE_TEMPLATE = '../PRATE/prate_{}.nc'
    VARIABLE_NAME = 'avg_tprate'
    OUTPUT_FILENAME_PREFIX = 'prate_10dy_averages'

    # --- マルチコア処理の実行 ---
    years_to_process = list(range(START_YEAR, END_YEAR + 1))
    args_for_starmap = zip(
        years_to_process,
        repeat(INPUT_FILE_TEMPLATE),
        repeat(VARIABLE_NAME),
        repeat(TIME_COORDINATE_NAME),
        repeat(OUTPUT_FILENAME_PREFIX)
    )
    print(f"=== 降水量データの並列処理 ({START_YEAR}年～{END_YEAR}年) を開始します ===")
    print(f"入力ファイル: {INPUT_FILE_TEMPLATE}")
    print(f"時間座標名: '{TIME_COORDINATE_NAME}'")
    print("-" * 50)
    with multiprocessing.Pool(processes=NUM_CORES) as pool:
        pool.starmap(process_precipitation_data, args_for_starmap)
    print("-" * 50)
    print("=== 全ての年の処理が完了しました ===")
