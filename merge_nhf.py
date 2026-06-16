import os
import pickle
import numpy as np
from tqdm import tqdm # 進捗バーを表示するためのライブラリ

# --- 設定項目 ---

# 穴埋め済みPKLふぁいるの場所
# 前のスクリプトの出力先を指定してください
input_directory = 'output_fluxes_180x360/'


# 出力するNPYファイル名
output_file_path = 'merged_NetHeatFlux_1940-2025.npy'

# マージ対象の年（開始年と終了年）
start_year = 1940
end_year = 2025

# 入力ファイル名の形式
filename_format = '{year}_filled_NetHeatFlux.pkl'

# --- 処理開始 ---

print("マージ処理を開始します...")

# 全ての期間の2次元データを格納するためのリスト
all_periods_data = []

# tqdmを使って進捗を分かりやすく表示
# 古い年から順番にループ
for year in tqdm(range(start_year, end_year + 1), desc="年を処理中"):
   
    file_path = os.path.join(input_directory, filename_format.format(year=year))

    # ファイルが存在するかチェック
    if not os.path.exists(file_path):
        print(f"\n警告: {file_path} が見つかりません。この年をスキップします。")
        # 1年分(12ヶ月 * 3期間 = 36)のNaN配列で埋めて、時系列がずれないようにする
        for _ in range(36):
            all_periods_data.append(np.full((180, 360), np.nan))
        continue

    # Pickleファイルを読み込む
    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
    except Exception as e:
        print(f"\nエラー: {file_path} の読み込みに失敗しました: {e}")
        continue

    # 1月から12月まで、時系列順にデータをリストに追加していく
    monthly_results = data.get('calculated_monthly_results_filled', {})
    for month in range(1, 13):
        # 期間の順番を固定
        periods = ['1_to_10', '11_to_20', '21_to_end']
       
        # 月のデータが存在するかチェック
        period_data = monthly_results.get(month, {})
       
        for period in periods:
            # 期間のデータ(180x360のNumpy配列)を取得
            # データが存在しない場合は、NaNで埋められた配列を代わりに使用
            grid_data = period_data.get(period, np.full((180, 360), np.nan))
           
            # リストに追加
            all_periods_data.append(grid_data)

# リストに集めた全ての2D配列を、新しい次元(時間軸)で連結して1つの3D配列にする
try:
    print("\n全てのデータをNumPy配列に変換しています...")
    final_array = np.array(all_periods_data)
except ValueError as e:
    print(f"\nエラー: 配列の形状が不一致のため、変換に失敗しました。{e}")
    print("入力ファイルが壊れているか、一部のデータ形式が異なっている可能性があります。")
    exit()

# 最終的な配列の形状を確認
# 形状: (総期間数, 緯度, 経度)
# 例: ( (2015-1806+1) * 12 * 3, 180, 360 )
print(f"最終的な配列の形状: {final_array.shape}")

# NumPy配列を.npyファイルとして保存
print(f"配列を {output_file_path} として保存しています...")
np.save(output_file_path, final_array)

print("✅ マージ処理が完了しました。")
