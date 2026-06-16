import xarray as xr
import os
import multiprocessing # マルチコア処理のためにインポート
from itertools import repeat # 複数の引数を渡すためにインポート

def calculate_and_save_hourly_upward_lw(year, net_lw_var, down_lw_var):
    """
    1時間ごとの上向き長波放射を計算し、新しいNetCDFファイルとして保存する。
    (この関数自体は変更ありません)
    """
    # 入力ファイルと出力ファイルの名前を定義
    net_lw_file = f'../net_flux/net_longwave_radiation_flux_{year}.nc'
    down_lw_file = f'../DLWRF/surface_longwave_radiation_{year}.nc'
    output_nc_file = f'../ULWRF/upward_longwave_radiation_hourly_{year}.nc'

    # 入力ファイルの存在を確認。両方が揃っていない場合は処理をスキップ
    if not (os.path.exists(net_lw_file) and os.path.exists(down_lw_file)):
        print(f"[{year}年] データファイルが見つからないため、スキップします。")
        return f"[{year}年] スキップ"

    print(f"[{year}年] 処理を開始します...")
    try:
        # 1. データを読み込む
        ds_net = xr.open_dataset(net_lw_file)
        ds_down = xr.open_dataset(down_lw_file)

        # 2. 上向き長波放射を計算
        upward_lw_da = ds_net[net_lw_var] - ds_down[down_lw_var]
       
        # 3. メタデータ（変数名や説明）を設定
        upward_lw_da.name = 'upward_lw'
        upward_lw_da.attrs['long_name'] = 'Upward Longwave Radiation'
        upward_lw_da.attrs['units'] = 'W m**-2'
        upward_lw_da.attrs['calculation_note'] = 'Calculated as net_radiation - downward_radiation'

        # 4. 新しいNetCDFファイルとして保存
        ds_upward = upward_lw_da.to_dataset()
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
        if 'ds_down' in locals() and ds_down:
            ds_down.close()


if __name__ == '__main__':
    # --- ユーザー設定 ---

    # 処理したい期間（開始年と終了年）を設定
    START_YEAR = 2024
    END_YEAR = 2025

    # 使用するCPUコア数を設定
    # Noneに設定すると、お使いのPCの全てのCPUコアを自動的に使用します
    # 例えば4コアだけ使いたい場合は NUM_CORES = 4 のように指定します
    NUM_CORES = 10

    # NetCDFファイル内の「変数名」
    NET_LONGWAVE_VARIABLE_NAME = 'avg_snlwrf'
    SURFACE_LONGWAVE_VARIABLE_NAME = 'avg_sdlwrf'

    # --- マルチコア処理の実行 ---
   
    # 処理対象の年のリストを作成
    years_to_process = list(range(START_YEAR, END_YEAR + 1))
   
    # 並列処理用の引数リストを作成
    # [(1940, 'lwnet', 'lwdn'), (1941, 'lwnet', 'lwdn'), ...] のようなリストを作る
    args_for_starmap = zip(
        years_to_process,
        repeat(NET_LONGWAVE_VARIABLE_NAME),
        repeat(SURFACE_LONGWAVE_VARIABLE_NAME)
    )

    print(f"=== {START_YEAR}年から{END_YEAR}年の並列処理を開始します ===")
    print(f"使用するCPUコア数: {NUM_CORES or multiprocessing.cpu_count()}")
    print("-" * 50)

    # multiprocessing.Poolを使って並列処理を実行
    # with構文を使うことで、処理終了後に自動で後片付けをしてくれる
    with multiprocessing.Pool(processes=NUM_CORES) as pool:
        # starmapは、(引数1, 引数2, ...) のタプル形式で引数を渡せる
        results = pool.starmap(calculate_and_save_hourly_upward_lw, args_for_starmap)

    print("-" * 50)
    print("=== 全ての年の処理が完了しました ===")
    # オプション: 各プロセスの実行結果を表示
    # for res in results:
    #     print(res)
