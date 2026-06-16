import pickle
import xarray as xr
import os
import multiprocessing
from itertools import repeat

def perform_calculation(year, prate_template, lhtfl_template, output_prefix):
    """
    2つのPKLファイルを読み込み、指定された計算を実行して新しいPKLファイルに保存する。
    """
    prate_file = prate_template.format(year)
    lhtfl_file = lhtfl_template.format(year)
    output_file = f"{output_prefix}_{year}.pkl"

    # 1. 両方の入力ファイルが存在するか確認
    if not (os.path.exists(prate_file) and os.path.exists(lhtfl_file)):
        print(f"[{year}年] 入力ファイルが見つからないため、処理をスキップします。")
        return f"[{year}年] スキップ"

    print(f"[{year}年] 処理を開始します...")
    try:
        # 2. 2つのPKLファイルからデータを読み込む
        with open(prate_file, 'rb') as f:
            prate_dict = pickle.load(f)
        with open(lhtfl_file, 'rb') as f:
            lhtfl_dict = pickle.load(f)

        yearly_results = {}
        # prateデータのキー（'days_1_10_avg'など）を基準にループ
        period_keys = prate_dict.keys()

        print(f"  - [{year}年] 3期間のデータを計算中...")
        for key in period_keys:
            # 対応する期間のDataArrayを取得
            prate_da = prate_dict[key] # これがavg_tprateのデータ
            lhtfl_da = lhtfl_dict[key] # これがmslhfのデータ

            # 3. 各グリッド毎に計算を実行
            # (avg_tprate - mslhf / 2.5e6) * 0.1
            # xarrayが座標を自動で合わせて計算してくれる
            result_da = (prate_da - lhtfl_da / 2.5e6) * 0.1
           
            # 結果のDataArrayに名前と説明を付けておく
            result_da.name = 'calculation_freshwater'
            result_da.attrs['long_name'] = 'Result of (prate - lhtfl/Le) * 0.1'
            result_da.attrs['calculation_formula'] = '(prate_mm_day - mslhf_W_m-2 / 2.5e6) * 0.1'

            # 計算結果を辞書に格納
            yearly_results[key] = result_da

        # 4. 新しいPKLファイルとして結果を保存
        print(f"  - [{year}年] 結果を {output_file} に保存中...")
        with open(output_file, 'wb') as f:
            pickle.dump(yearly_results, f)

        result_message = f"[{year}年] {output_file} の作成が完了しました。 ✨"
        print(result_message)
        return result_message

    except Exception as e:
        error_message = f"[{year}年] 処理中にエラーが発生しました: {e}"
        print(error_message)
        return error_message

if __name__ == '__main__':
    # --- ユーザー設定 ---
    # 処理したい期間（開始年と終了年）
    START_YEAR = 1940
    END_YEAR = 2025

    # 使用するCPUコア数 (Noneで全コア使用)
    NUM_CORES = 85
   
    # ★★★ 入力ファイルと出力ファイル名を設定 ★★★
   
    # 1. 降水量データのPKLファイル名のテンプレート
    PRATE_FILE_TEMPLATE = '../10dy/10dy_prate/prate_10dy_averages_{}.pkl'

    # 2. 潜熱フラックスデータのPKLファイル名のテンプレート
    LHTFL_FILE_TEMPLATE = '../10dy/10dy_lhtfl/lhtfl_10dy_{}.pkl' 
   
    # 3. 出力されるPickleファイルの接頭辞
    OUTPUT_FILENAME_PREFIX = '../Freshwater/freshwater_10dy'

    # --- マルチコア処理の実行 ---
    years_to_process = list(range(START_YEAR, END_YEAR + 1))
   
    args_for_starmap = zip(
        years_to_process,
        repeat(PRATE_FILE_TEMPLATE),
        repeat(LHTFL_FILE_TEMPLATE),
        repeat(OUTPUT_FILENAME_PREFIX)
    )

    print(f"=== 計算処理の並列実行 ({START_YEAR}年～{END_YEAR}年) を開始します ===")
    print("-" * 50)

    with multiprocessing.Pool(processes=NUM_CORES) as pool:
        pool.starmap(perform_calculation, args_for_starmap)

    print("-" * 50)
    print("=== 全ての年の処理が完了しました ===")

