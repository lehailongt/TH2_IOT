# bridge.py
# Nhận dữ liệu từ MQTT, validate dữ liệu đầu vào, ghi vào InfluxDB

import paho.mqtt.client as mqtt
import json
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from config import *

# Khởi tạo kết nối InfluxDB
write_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = write_client.write_api(write_options=SYNCHRONOUS)

# --- Hàm kiểm tra tính hợp lệ của dữ liệu (Validate) ---
def validate_payload(payload):
    """Kiểm tra dữ liệu đầu vào có đầy đủ và hợp lệ không."""
    required_fields = ["temperature", "humidity", "distance_cm", "rssi", "sequence"]
    for field in required_fields:
        if field not in payload:
            print(f"[VALIDATE] Thiếu trường: {field}")
            return False

    # Kiểm tra giá trị vật lý hợp lệ
    if not (-40 <= payload["temperature"] <= 80):
        print(f"[VALIDATE] Nhiệt độ bất thường: {payload['temperature']}")
        return False
    if not (0 <= payload["humidity"] <= 100):
        print(f"[VALIDATE] Độ ẩm bất thường: {payload['humidity']}")
        return False
    if payload["distance_cm"] < 0:
        print(f"[VALIDATE] Khoảng cách âm: {payload['distance_cm']}")
        return False
    return True

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[MQTT] Đã kết nối Broker. Subscribe: {MQTT_TOPIC}")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[MQTT] Kết nối thất bại, mã lỗi: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())

        # Validate dữ liệu trước khi ghi
        if not validate_payload(payload):
            print("[WARN] Dữ liệu không hợp lệ, bỏ qua.\n")
            return

        print(f"[MQTT] Nhận: {payload}")

        point = (
            Point(MEASUREMENT_RAW)
            .tag("device", "esp32_node_01")
            .field("temperature", float(payload["temperature"]))
            .field("humidity", float(payload["humidity"]))
            .field("distance_cm", float(payload["distance_cm"]))
            .field("rssi", int(payload["rssi"]))
            .field("sequence", int(payload["sequence"]))
            .time(datetime.utcnow())
        )

        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        print("  -> Đã ghi vào InfluxDB.\n")

    except Exception as e:
        print(f"[LỖI] {e}\n")

client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.on_connect = on_connect
client.on_message = on_message

print("=" * 50)
print("BRIDGE MQTT -> INFLUXDB (có VALIDATE)")
print("=" * 50)

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[INFO] Dừng bridge.")
    client.disconnect()
    write_client.close()