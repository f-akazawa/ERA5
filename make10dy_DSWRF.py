
import xarray as xr
import pandas as pd
import pickle
import os
import multiprocessing
from itertools import repeat

def calculate_monthly_period_averages(year, file_template, var_name, time_coord_name, output_prefix):
    """
    毎時のNCファイルを読み込み、日平均化→月別期間平均化を行い、PKLファイルで保存する。
    """
    input_file = file_template.format(year)
    output_file = f"{output_prefix}_{year}.pkl"

    if not os.path.exists(input_file):
        print(f"[{year}年] 入力ファイル {input_file} が見つからないため、スキップします。")
        return f"[{year}年] スキップ"

    print(f"[{year}年] 処理を開始します... ファイル: {input_file}")
    try:
        with xr.open_dataset(input_file) as ds:
            # ★★★ 修正点 ★★★
            # 指定された時間座標が存在すれば、名前を'time'に統一する
            if time_coord_name in ds.coords and time_coord_name != 'time':
                ds = ds.rename({time_coord_name: 'time'})
                print(f"  - [{year}年] 座標'{time_coord_name}'を'time'にリネームしました。")

            # これ以降の処理は'time'座標を前提として、変更なく実行できる
           
            # ステップ1: 1時間データ -> 日平均データ
            print(f"  - [{year}年] 日平均を計算中...")
            daily_data = ds[var_name].resample(time='D').mean(skipna=True)

            # ステップ2: 月ごとにグループ化
            monthly_groups = daily_data.groupby('time.month')

            # ステップ3: 各月の3期間で平均を計算
            print(f"  - [{year}年] 月別の期間平均を計算中...")
            avg_period1 = monthly_groups.apply(lambda x: x.sel(time=x.time.dt.day.isin(range(1, 11))).mean(dim='time', skipna=True))
            avg_period2 = monthly_groups.apply(lambda x: x.sel(time=x.time.dt.day.isin(range(11, 21))).mean(dim='time', skipna=True))
            avg_period3 = monthly_groups.apply(lambda x: x.sel(time=x.time.dt.day >= 21).mean(dim='time', skipna=True))
           
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
    NUM_CORES = 10
   
    # ★★★ 入力ファイルに合わせて以下の設定を確認してください ★★★
   
    # 1. 時間座標の名前を指定
    TIME_COORDINATE_NAME = 'valid_time' # 'time'ではない場合、ここで指定

    # 2. 処理する毎時データファイル名のテンプレート
    INPUT_FILE_TEMPLATE = '../DSWRF/surface_solar_radiation_{}.nc'

    # 3. NetCDFファイル内の変数名
    VARIABLE_NAME = 'ssrd'
   
    # 4. 出力されるPickleファイルの接頭辞
    OUTPUT_FILENAME_PREFIX = '../10dy/10dy_dswrf/dswrf_10dy'

    # --- マルチコア処理の実行 ---
    years_to_process = list(range(START_YEAR, END_YEAR + 1))
   
    # 並列処理用の引数リストを作成（TIME_COORDINATE_NAMEを追加）
    args_for_starmap = zip(
        years_to_process,
        repeat(INPUT_FILE_TEMPLATE),
        repeat(VARIABLE_NAME),
        repeat(TIME_COORDINATE_NAME),
        repeat(OUTPUT_FILENAME_PREFIX)
    )

    print(f"=== 月別・期間平均の並列処理 ({START_YEAR}年～{END_YEAR}年) を開始します ===")
    print(f"入力ファイル: {INPUT_FILE_TEMPLATE}")
    print(f"時間座標名: '{TIME_COORDINATE_NAME}'")
    print("-" * 50)

    with multiprocessing.Pool(processes=NUM_CORES) as pool:
        pool.starmap(calculate_monthly_period_averages, args_for_starmap)

    print("-" * 50)
    print("=== 全ての年の処理が完了しました ===")

