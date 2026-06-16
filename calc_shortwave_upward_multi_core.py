import xarray as xr
import os
import multiprocessing
from itertools import repeat

def calculate_and_save_hourly_upward_sw(year, net_sw_var, down_sw_var):
    """
    1時間ごとの上向き短波放射を計算し、新しいNetCDFファイルとして保存する。
    下向き短波放射(J m-2)はワット(W m-2)に単位変換してから計算する。
    """
    # 短波用のファイル名を定義
    net_sw_file = f'../net_flux/net_shortwave_radiation_flux_{year}.nc'
    down_sw_file = f'../DSWRF/surface_solar_radiation_{year}.nc'
    output_nc_file = f'../USWRF/upward_shortwave_radiation_hourly_{year}.nc'

    # 入力ファイルの存在を確認
    if not (os.path.exists(net_sw_file) and os.path.exists(down_sw_file)):
        print(f"[{year}年] 短波放射のデータファイルが見つからないため、スキップします。")
        return f"[{year}年] スキップ"

    print(f"[{year}年] 短波放射の処理を開始します...")
    try:
        # 1. データを読み込む
        ds_net = xr.open_dataset(net_sw_file)
        ds_down_joules = xr.open_dataset(down_sw_file)

        # 2. 単位変換 (J/m^2 -> W/m^2)
        print(f"  - [{year}年] 単位変換 (J m-2 -> W m-2) を実行中...")
        # 1時間(3600秒)で割ることで、平均電力(W)に変換する
        downward_watts = ds_down_joules[down_sw_var] / 3600.0
       
        # 3. 上向き短波放射を計算
        print(f"  - [{year}年] 上向き短波放射を計算中...")
        # ネット放射(W/m^2) - 下向き放射(W/m^2)
        upward_sw_da = ds_net[net_sw_var] - downward_watts

        # 4. メタデータ（変数名や説明）を設定
        upward_sw_da.name = 'upward_sw'
        upward_sw_da.attrs['long_name'] = 'Upward Shortwave Radiation'
        upward_sw_da.attrs['units'] = 'W m-2'
        upward_sw_da.attrs['calculation_note'] = 'Calculated as net_shortwave - (downward_shortwave_J_m-2 / 3600)'

        # 5. 新しいNetCDFファイルとして保存
        print(f"  - [{year}年] 結果を {output_nc_file} に保存中...")
        ds_upward = upward_sw_da.to_dataset()
        ds_upward.to_netcdf(output_nc_file)

        result_message = f"[{year}年] {output_nc_file} の作成が完了しました。 ✨"
        print(result_message)
        return result_message

    except Exception as e:
        error_message = f"[{year}年] 処理中にエラーが発生しました: {e}"
        print(error_message)
        return error_message

    finally:
        # ファイルが開かれていれば確実に閉じる
        if 'ds_net' in locals() and ds_net:
            ds_net.close()
        if 'ds_down_joules' in locals() and ds_down_joules:
            ds_down_joules.close()

if __name__ == '__main__':
    # --- ユーザー設定 ---

    # 処理したい期間（開始年と終了年）を設定
    START_YEAR = 1940
    END_YEAR = 1942

    # 使用するCPUコア数 (Noneで全コア使用)
    NUM_CORES = 10

    # NetCDFファイル内の「変数名」をデータに合わせて変更してください
    NET_SHORTWAVE_VARIABLE_NAME = 'avg_snswrf'  # 例: 'nswrs', 'msnswrf' など
    SURFACE_SOLAR_VARIABLE_NAME = 'ssrd'  # 例: 'ssrd', 'msdwswrf' など

    # --- マルチコア処理の実行 ---
    years_to_process = list(range(START_YEAR, END_YEAR + 1))
    args_for_starmap = zip(
        years_to_process,
        repeat(NET_SHORTWAVE_VARIABLE_NAME),
        repeat(SURFACE_SOLAR_VARIABLE_NAME)
    )

    print(f"=== 短波放射の並列処理 ({START_YEAR}年～{END_YEAR}年) を開始します ===")
    print(f"使用するCPUコア数: {NUM_CORES or multiprocessing.cpu_count()}")
    print("-" * 50)

    with multiprocessing.Pool(processes=NUM_CORES) as pool:
        pool.starmap(calculate_and_save_hourly_upward_sw, args_for_starmap)

    print("-" * 50)
    print("=== 全ての年の処理が完了しました ===")
