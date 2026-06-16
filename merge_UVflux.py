
import os
import pickle
import numpy as np
import xarray as xr
from tqdm import tqdm

# --- 1. 設定項目 ---

# ★★★ マージしたい変数の情報をここに設定 ★★★
variables_to_process = {
    'uflx': {
        'input_dir': './output_filled/uflx',
        'input_filename': '{year}_filled_uflx.pkl',
        'output_npy_file': 'uflx_filled_1940-2025.npy'
    },
    'vflx': {
        'input_dir': './output_filled/vflx',
        'input_filename': '{year}_filled_vflx.pkl',
        'output_npy_file': 'vflx_filled_1940-2025.npy'
    }
}

# 処理対象の年範囲
start_year = 1940
end_year = 2025

# --- 処理開始 ---
print("マージ処理を開始します...")

# uflxとvflxを順番に処理
for var_name, config in variables_to_process.items():
    print(f"\n{'='*20} Processing: {var_name.upper()} {'='*20}")

    # 全ての期間の2次元データを格納するためのリスト
    all_periods_data = []

    # 古い年から順番にループ
    for year in tqdm(range(start_year, end_year + 1), desc=f"  {var_name} 年処理中"):
       
        file_path = os.path.join(config['input_dir'], config['input_filename'].format(year=year))

        # ファイルが存在するかチェック
        if not os.path.exists(file_path):
            print(f"\n  警告: {file_path} が見つかりません。この年はNaNで埋めます。")
            # 1年分(12ヶ月 * 3期間 = 36)のNaN配列で埋めて、時系列がずれないようにする
            for _ in range(36):
                all_periods_data.append(np.full((180, 360), np.nan))
            continue

        try:
            with open(file_path, 'rb') as f:
                year_data = pickle.load(f)
        except Exception as e:
            print(f"\n  エラー: {file_path} の読み込みに失敗しました: {e}")
            continue
       
        # 1月から12月まで、時系列順にデータをリストに追加
        for month_idx in range(12):
            for period_key in ['days_1_10_avg', 'days_11_20_avg', 'days_21_end_avg']:
                try:
                    # 3Dデータキューブから月のスライスを取得し、Numpy配列に変換
                    data_cube = year_data[period_key]
                    grid_data = data_cube.values[month_idx, :, :]
                    all_periods_data.append(grid_data)
                except (KeyError, IndexError, AttributeError):
                    # データが期待通りでない場合、NaNで埋める
                    all_periods_data.append(np.full((180, 360), np.nan))

    # リストに集めた全ての2D配列を、1つの大きな3D配列に変換
    try:
        print("\n  全てのデータをNumPy配列に変換しています...")
        final_array = np.array(all_periods_data)
    except ValueError as e:
        print(f"  エラー: 配列の形状が不一致のため、変換に失敗しました。{e}")
        continue # この変数の処理を中断して次へ

    # 最終的な配列の形状を確認
    print(f"  最終的な配列の形状: {final_array.shape}")

    # NumPy配列を.npyファイルとして保存
    output_path = config['output_npy_file']
    print(f"  配列を {output_path} として保存しています...")
    np.save(output_path, final_array)
    print(f"  ✅ {var_name.upper()} のマージが完了しました。")

print("\n{'='*50}\n全ての処理が完了しました。")
