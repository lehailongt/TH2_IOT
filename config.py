# config.py
# ===== CẤU HÌNH CHUNG CHO TOÀN BỘ HỆ THỐNG =====

# --- MQTT Broker (Mosquitto trên máy tính) ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "admin"             # <<< THAY BẰNG USERNAME MOSQUITTO
MQTT_PASS = "admin123"            # <<< THAY BẰNG PASSWORD MOSQUITTO
MQTT_TOPIC = "iot/sensor/data"  # Phải khớp với code ESP32

# --- InfluxDB 2.x ---
INFLUX_URL = "eddBAIqwosXmSRKeREOQvsmTS93vEWxAohrDJl5j18yRxJTAsA7D576MhWQrcQgawEBEVxdprhlGRZDT-qKi3Q=="
INFLUX_TOKEN = "DÁN_API_TOKEN_CỦA_BẠN_VÀO_ĐÂY"  # <<< Lấy ở Bước 2.3
INFLUX_ORG = "influxdb"                            # <<< Tên Organization
INFLUX_BUCKET = "iot_data"                       # <<< Tên Bucket

# --- Tên Measurement ---
MEASUREMENT_RAW = "sensor_reading"           # Dữ liệu thô
MEASUREMENT_PROCESSED = "sensor_processed"   # Dữ liệu đã xử lý

# --- Cấu hình Retention Policy (Yêu cầu 3.2) ---
# Thời gian lưu trữ dữ liệu thô: 7 ngày (tự động xóa sau 7 ngày)
RETENTION_DAYS = 7