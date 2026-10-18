# setup_influx.py
# Tạo Bucket và cấu hình Retention Policy theo yêu cầu 3.2

from influxdb_client import InfluxDBClient, BucketRetentionRules
from config import *

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
buckets_api = client.buckets_api()

def create_bucket_with_retention(bucket_name, retention_days):
    """Tạo bucket với thời gian lưu trữ (retention) tính bằng ngày"""
    # Kiểm tra bucket đã tồn tại chưa
    existing = buckets_api.find_bucket_by_name(bucket_name)
    if existing:
        print(f"[INFO] Bucket '{bucket_name}' đã tồn tại. Bỏ qua.")
        return

    # Tạo retention rule (đơn vị: giây)
    retention_seconds = retention_days * 24 * 60 * 60
    retention_rules = BucketRetentionRules(type="expire", every_seconds=retention_seconds)

    # Tạo bucket
    bucket = buckets_api.create_bucket(
        bucket_name=bucket_name,
        org=INFLUX_ORG,
        retention_rules=retention_rules
    )
    print(f"[DONE] Đã tạo bucket '{bucket_name}' với retention {retention_days} ngày.")

if __name__ == "__main__":
    print("=" * 50)
    print("THIẾT LẬP INFLUXDB BUCKET & RETENTION POLICY")
    print("=" * 50)
    create_bucket_with_retention(INFLUX_BUCKET, RETENTION_DAYS)
    client.close()