import xarray as xr

# ds という変数にデータが読み込まれていると仮定します
ds = xr.open_dataset('era5_land_sea_mask_1940.nc')

# 1. 保存したい時刻のデータを .sel() で選択します
data_slice = ds.sel(valid_time='1940-01-01T12:00:00')

# 2. .to_netcdf() を使ってファイルに保存します
# data_sliceはDatasetなので、そのまま保存できます。
output_filename = 'lsm_1940-01-01_12z.nc'
data_slice.to_netcdf(output_filename)

print(f"✅ データのスライスが完了し、'{output_filename}' として保存されました。")

