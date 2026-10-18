# preprocess.py
# Tiền xử lý dữ liệu đầy đủ theo yêu cầu 3.3:
# - Đọc dữ liệu theo khoảng thời gian
# - Xử lý missing values
# - Phát hiện & xử lý outlier (IQR)
# - Resampling theo cửa sổ thời gian
# - Tạo đặc trưng (rolling mean, delta)
# - Chuẩn hóa dữ liệu (Min-Max Scaling)
# - Lưu kết quả vào measurement mới

import pandas as pd
import numpy as np
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from config import *

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = client.query_api()
write_api = client.write_api(write_options=SYNCHRONOUS)

def fetch_raw_data(minutes=60):
    """1. Đọc dữ liệu từ database theo khoảng thời gian"""
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{minutes}m)
      |> filter(fn: (r) => r["_measurement"] == "{MEASUREMENT_RAW}")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    print(f"[INFO] Đọc dữ liệu {minutes} phút gần nhất...")
    df = query_api.query_data_frame(query)

    if df.empty:
        print("[WARN] Không có dữ liệu.")
        return None

    cols = ["_time", "temperature", "humidity", "distance_cm", "rssi"]
    df = df[[c for c in cols if c in df.columns]].copy()
    df = df.rename(columns={"_time": "time"}).set_index("time").sort_index()
    print(f"[INFO] Đã lấy {len(df)} bản ghi thô.")
    return df

def handle_missing_values(df):
    """2. Xử lý giá trị thiếu (missing values)"""
    print("[INFO] Xử lý missing values (nội suy tuyến tính)...")
    missing_before = df.isna().sum().sum()
    df = df.interpolate(method="linear").dropna()
    print(f"  - Đã xử lý {missing_before} giá trị thiếu.")
    return df

def remove_outliers_iqr(df, columns):
    """3. Phát hiện và xử lý outlier bằng IQR"""
    print("[INFO] Phát hiện outlier bằng IQR...")
    for col in columns:
        if col not in df.columns:
            continue
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        before = len(df)
        df = df[(df[col] >= lower) & (df[col] <= upper)]
        print(f"  - {col}: loại {before - len(df)} outlier.")
    return df

def resample_data(df, window="1min"):
    """4. Resampling theo cửa sổ thời gian"""
    print(f"[INFO] Resampling cửa sổ {window} (lấy trung bình)...")
    df_res = df.resample(window).mean().dropna()
    print(f"  - Sau resampling: {len(df_res)} bản ghi.")
    return df_res

def create_features(df):
    """5. Tạo đặc trưng đơn giản (rolling mean, delta)"""
    print("[INFO] Tạo đặc trưng (rolling mean, delta)...")
    # Rolling mean cửa sổ 3 mẫu
    df["temp_rolling_mean"] = df["temperature"].rolling(window=3, min_periods=1).mean()
    df["humid_rolling_mean"] = df["humidity"].rolling(window=3, min_periods=1).mean()
    # Delta (chênh lệch so với mẫu trước)
    df["temp_delta"] = df["temperature"].diff().fillna(0)
    df["humid_delta"] = df["humidity"].diff().fillna(0)
    return df

def normalize_data(df, columns):
    """6. Chuẩn hóa dữ liệu (Min-Max Scaling về [0, 1])"""
    print("[INFO] Chuẩn hóa dữ liệu (Min-Max)...")
    df_norm = df.copy()
    for col in columns:
        if col in df_norm.columns:
            min_val = df_norm[col].min()
            max_val = df_norm[col].max()
            if max_val - min_val > 0:
                df_norm[col + "_norm"] = (df_norm[col] - min_val) / (max_val - min_val)
            else:
                df_norm[col + "_norm"] = 0.0
    return df_norm

def save_to_influx(df):
    """7. Lưu kết quả vào measurement mới"""
    print("[INFO] Ghi dữ liệu đã xử lý vào InfluxDB...")
    points = []
    for ts, row in df.iterrows():
        p = (
            Point(MEASUREMENT_PROCESSED)
            .tag("device", "esp32_node_01")
            .field("temperature", float(row["temperature"]))
            .field("humidity", float(row["humidity"]))
            .field("distance_cm", float(row["distance_cm"]))
            .field("temp_rolling_mean", float(row["temp_rolling_mean"]))
            .field("humid_rolling_mean", float(row["humid_rolling_mean"]))
            .field("temp_delta", float(row["temp_delta"]))
            .field("humid_delta", float(row["humid_delta"]))
            .field("temperature_norm", float(row["temperature_norm"]))
            .field("humidity_norm", float(row["humidity_norm"]))
            .time(ts)
        )
        points.append(p)

    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
    print(f"[DONE] Đã ghi {len(points)} bản ghi vào '{MEASUREMENT_PROCESSED}'.")

def preprocess():
    df = fetch_raw_data(minutes=60)
    if df is None:
        return

    df = handle_missing_values(df)
    df = remove_outliers_iqr(df, ["temperature", "humidity", "distance_cm"])
    df = resample_data(df, window="1min")
    df = create_features(df)
    df = normalize_data(df, ["temperature", "humidity"])
    save_to_influx(df)

if __name__ == "__main__":
    print("=" * 50)
    print("TIỀN XỬ LÝ DỮ LIỆU IoT (ĐẦY ĐỦ)")
    print("=" * 50)
    preprocess()
    client.close()