
---

## 1. Kiến trúc hệ thống

```
┌──────────────┐  JSON/MQTT   ┌───────────────┐  subscribe  ┌────────────────────┐
│ ESP32 + DHT22│ ───────────► │ Mosquitto     │ ──────────► │ collector.py       │
│ + LDR        │  publish     │ MQTT Broker   │             │ (validate + ghi DB)│
└──────────────┘              └───────────────┘             └─────────┬──────────┘
                                                                      │ write
                                                                      ▼
┌──────────────┐   đọc dữ liệu   ┌──────────────────────────────────────────────┐
│ preprocess.py│ ◄────────────── │ InfluxDB 2.x                                 │
│ (làm sạch,   │ ──────────────► │  - sensor_data       (dữ liệu thô)           │
│ resample...) │  ghi kết quả    │  - sensor_data_clean (dữ liệu đã tiền xử lý) │
└──────────────┘                 └───────────────────┬──────────────────────────┘
                                                     │ query
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │ Dashboard (Grafana/Streamlit)│
                                      └─────────────────────────────┘
```

## 2. Cấu trúc thư mục

```
.
├── firmware/
│   └── esp32_sensor/
│       ├── esp32_sensor.ino        # Firmware ESP32 (đọc cảm biến + publish MQTT)
│       └── config.h.example        # Mẫu cấu hình WiFi / MQTT
├── src/
│   ├── collector.py                # Subscribe MQTT, validate, ghi InfluxDB
│   ├── preprocess.py               # Tiền xử lý dữ liệu
│   ├── latency.py                  # Đo độ trễ end-to-end
│   ├── simulator.py                # Giả lập dữ liệu (khi chưa có phần cứng)
│   └── utils.py                    # Hàm dùng chung (đọc cấu hình, kết nối DB...)
├── app/
│   └── dashboard.py                # Ứng dụng Streamlit
├── config/
│   ├── mosquitto.conf              # Cấu hình Mosquitto
│   └── .env.example                # Mẫu biến môi trường
├── docs/
│   ├── architecture.png            # Sơ đồ kiến trúc
│   └── screenshots/                # Ảnh dashboard, kết quả thực nghiệm
├── requirements.txt
└── README.md
```

## 3. Yêu cầu

### Phần cứng
- ESP32 (hoặc Arduino) + cảm biến DHT22/BME280 + LDR (quang trở)
- Máy tính hoặc Raspberry Pi đóng vai trò gateway (chạy broker, database, script Python)

### Phần mềm

| Thành phần | Phiên bản khuyến nghị |
|---|---|
| Python | 3.9 trở lên |
| Mosquitto (MQTT Broker) | 2.x |
| InfluxDB | 2.x |
| Grafana (tùy chọn) | 10.x trở lên |
| Arduino IDE hoặc PlatformIO | Bản mới nhất |

---

## 4. Cài đặt

### 4.1. Cài MQTT Broker (Mosquitto)

**Ubuntu / Raspberry Pi OS:**
```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto
```

**Windows:** tải bản cài đặt tại <https://mosquitto.org/download/>, cài xong chạy Mosquitto như một service (hoặc chạy `mosquitto -v` trong thư mục cài đặt).

Mosquitto 2.x mặc định chỉ cho phép kết nối từ `localhost`. Để ESP32 kết nối được, sao chép file `config/mosquitto.conf` của repo vào thư mục cấu hình của Mosquitto rồi khởi động lại:

```conf
listener 1883
allow_anonymous true
```

```bash
# Ubuntu
sudo cp config/mosquitto.conf /etc/mosquitto/conf.d/lab2.conf
sudo systemctl restart mosquitto
```

> Lưu ý: `allow_anonymous true` chỉ dùng cho môi trường thực hành. Với triển khai thật, hãy cấu hình tài khoản/mật khẩu hoặc TLS.

Kiểm tra broker hoạt động:
```bash
# Terminal 1
mosquitto_sub -h localhost -t "test/#" -v
# Terminal 2
mosquitto_pub -h localhost -t "test/hello" -m "xin chao"
```

### 4.2. Cài InfluxDB 2.x

**Ubuntu / Raspberry Pi OS:** làm theo hướng dẫn chính thức tại <https://docs.influxdata.com/influxdb/v2/install/> (cài gói `influxdb2`), sau đó:
```bash
sudo systemctl enable --now influxdb
```

**Windows:** tải file zip tại trang chính thức, giải nén và chạy `influxd.exe`.

Mở trình duyệt tại <http://localhost:8086> và thực hiện thiết lập lần đầu:

1. Tạo **username / password**
2. **Organization:** `iot-lab`
3. **Bucket:** `iot_raw`
4. Sao chép **API Token** (hoặc tạo mới tại *Load Data → API Tokens*)

Tạo thêm bucket cho dữ liệu đã xử lý và cấu hình **retention policy**:

| Bucket | Nội dung | Retention |
|---|---|---|
| `iot_raw` | Dữ liệu thô từ cảm biến | 7 ngày |
| `iot_processed` | Dữ liệu sau tiền xử lý | 30 ngày |

Có thể tạo bằng giao diện web (*Load Data → Buckets → Create Bucket*) hoặc bằng CLI:
```bash
influx bucket create -n iot_raw -o iot-lab -r 168h
influx bucket create -n iot_processed -o iot-lab -r 720h
```

### 4.3. Cài môi trường Python

```bash
git clone https://github.com/<username>/<ten-repo>.git
cd <ten-repo>

python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

Nội dung `requirements.txt`:
```
paho-mqtt>=2.0
influxdb-client>=1.40
pandas
numpy
scikit-learn
python-dotenv
streamlit
plotly
```

### 4.4. Cấu hình biến môi trường

```bash
cp config/.env.example .env      # Windows: copy config\.env.example .env
```

Chỉnh sửa file `.env`:

```env
# MQTT
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_TOPIC=iot/lab2/+/telemetry

# InfluxDB
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=<dán token của bạn vào đây>
INFLUX_ORG=iot-lab
INFLUX_BUCKET_RAW=iot_raw
INFLUX_BUCKET_PROCESSED=iot_processed
```

> File `.env` chứa token nên **không được đẩy lên GitHub** (đã thêm vào `.gitignore`).

### 4.5. (Tùy chọn) Cài Grafana

Làm theo hướng dẫn tại <https://grafana.com/docs/grafana/latest/setup-grafana/installation/>. Sau khi chạy, truy cập <http://localhost:3000> (tài khoản mặc định `admin / admin`) và thêm data source **InfluxDB** với:

- Query language: **Flux**
- URL: `http://localhost:8086`
- Organization: `iot-lab`
- Token: token InfluxDB của bạn
- Default bucket: `iot_raw`

---

## 5. Nạp firmware cho ESP32

1. Mở `firmware/esp32_sensor/esp32_sensor.ino` bằng Arduino IDE.
2. Cài các thư viện qua Library Manager: **PubSubClient**, **ArduinoJson**, **DHT sensor library** (và **Adafruit Unified Sensor**).
3. Sao chép `config.h.example` thành `config.h` và điền thông tin:
   ```cpp
   #define WIFI_SSID     "ten_wifi"
   #define WIFI_PASSWORD "mat_khau_wifi"
   #define MQTT_SERVER   "192.168.1.100"   // IP máy chạy Mosquitto
   #define MQTT_PORT     1883
   #define DEVICE_ID     "esp32-01"
   ```
4. Chọn board **ESP32 Dev Module**, chọn đúng cổng COM rồi **Upload**.
5. Mở Serial Monitor (115200 baud) để kiểm tra thiết bị đã kết nối WiFi và MQTT.

**Sơ đồ nối dây (mặc định):**

| Cảm biến | Chân cảm biến | Chân ESP32 |
|---|---|---|
| DHT22 | VCC / DATA / GND | 3V3 / GPIO 4 / GND |
| LDR (chia áp) | Điểm giữa | GPIO 34 (ADC) |

### Định dạng topic và payload

- **Topic:** `iot/lab2/<device_id>/telemetry`
- **Payload (JSON):**

```json
{
  "device_id": "esp32-01",
  "ts": 1718000000000,
  "temperature": 28.5,
  "humidity": 70.2,
  "light": 512
}
```

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `device_id` | string | Mã thiết bị |
| `ts` | int | Thời điểm đo (Unix epoch, mili giây) |
| `temperature` | float | Nhiệt độ (°C) |
| `humidity` | float | Độ ẩm (%) |
| `light` | int | Giá trị ánh sáng (ADC 0-4095) |

> **Chưa có phần cứng?** Chạy bộ giả lập: `python src/simulator.py --devices 2 --interval 2` (có tùy chọn `--anomaly-rate 0.05` để chèn dữ liệu bất thường và `--drop-rate 0.1` để giả lập mất gói).

---

## 6. Hướng dẫn chạy

Mở **mỗi lệnh ở một terminal riêng** (đã kích hoạt môi trường `venv`).

### Bước 1: Đảm bảo dịch vụ đang chạy
```bash
# Ubuntu: kiểm tra Mosquitto và InfluxDB
sudo systemctl status mosquitto influxdb
```

### Bước 2: Chạy collector (thu thập và ghi dữ liệu)
```bash
python src/collector.py
```
Collector sẽ subscribe topic, kiểm tra dữ liệu (đủ trường, đúng kiểu, nằm trong khoảng hợp lệ), loại bản ghi trùng lặp rồi ghi vào bucket `iot_raw`. Bản ghi không hợp lệ được ghi vào file `logs/invalid_records.log`.

### Bước 3: Chạy thiết bị hoặc bộ giả lập
Cấp nguồn cho ESP32, hoặc:
```bash
python src/simulator.py --devices 2 --interval 2
```

### Bước 4: Chạy tiền xử lý
Để thu thập dữ liệu đủ lâu (khuyến nghị tối thiểu 30 phút) rồi chạy:
```bash
python src/preprocess.py --start -1h --window 1min --outlier iqr
```

| Tham số | Mặc định | Mô tả |
|---|---|---|
| `--start` | `-1h` | Thời điểm bắt đầu đọc dữ liệu (tương đối hoặc ISO 8601) |
| `--stop` | `now()` | Thời điểm kết thúc |
| `--window` | `1min` | Cửa sổ resampling |
| `--outlier` | `iqr` | Phương pháp phát hiện outlier: `iqr` hoặc `zscore` |
| `--fill` | `interpolate` | Xử lý giá trị thiếu: `interpolate`, `ffill`, `mean` |
| `--scale` | `minmax` | Chuẩn hóa: `minmax` hoặc `standard` |

Các bước xử lý theo thứ tự: đọc dữ liệu → xử lý giá trị thiếu → phát hiện/xử lý outlier → resampling → tạo đặc trưng (rolling mean, delta) → chuẩn hóa → ghi vào bucket `iot_processed`.

### Bước 5: Chạy dashboard

**Streamlit (app ứng dụng):**
```bash
streamlit run app/dashboard.py
```
Truy cập <http://localhost:8501>.

**Grafana (tùy chọn):** mở <http://localhost:3000>, tạo dashboard với 2 nhóm panel: dữ liệu thô (`iot_raw`) và dữ liệu đã xử lý (`iot_processed`).

### Bước 6: Đo độ trễ end-to-end
```bash
python src/latency.py --duration 300
```
Script so sánh thời điểm đo (`ts` trong payload) với thời điểm bản ghi được ghi thành công vào database, sau đó xuất độ trễ trung bình, trung vị, P95, P99 và lưu biểu đồ vào `docs/screenshots/`.

---

## 7. Thiết kế schema InfluxDB

### Bucket `iot_raw` - measurement `sensor_data`

| Loại | Tên | Kiểu | Mô tả |
|---|---|---|---|
| Tag | `device_id` | string | Mã thiết bị |
| Tag | `location` | string | Vị trí đặt thiết bị |
| Field | `temperature` | float | Nhiệt độ (°C) |
| Field | `humidity` | float | Độ ẩm (%) |
| Field | `light` | int | Ánh sáng (ADC) |
| Timestamp | `_time` | ns | Thời điểm đo |

### Bucket `iot_processed` - measurement `sensor_data_clean`

| Loại | Tên | Mô tả |
|---|---|---|
| Tag | `device_id`, `location` | Giống bucket thô |
| Field | `temperature`, `humidity`, `light` | Giá trị sau làm sạch và resampling |
| Field | `temperature_roll_mean` | Trung bình trượt của nhiệt độ |
| Field | `temperature_delta` | Chênh lệch nhiệt độ giữa 2 cửa sổ liên tiếp |
| Field | `temperature_norm`, `humidity_norm`, `light_norm` | Giá trị sau chuẩn hóa |
| Field | `is_outlier` | Cờ đánh dấu bản ghi từng là outlier (0/1) |

**Xử lý trùng lặp:** InfluxDB coi các điểm có cùng measurement, tag set và timestamp là một điểm, ghi lại sẽ ghi đè. Vì vậy collector dùng timestamp từ thiết bị (`ts`) thay vì thời điểm nhận, nhờ đó gói MQTT gửi lại (QoS 1) không tạo bản ghi trùng.

**Xử lý mất mát:** MQTT dùng QoS 1, `clean_session=False` và client ID cố định để broker lưu lại tin nhắn khi collector tạm ngắt kết nối. Collector có cơ chế ghi theo lô (batch) kèm retry khi database không phản hồi.

---

## 8. Một số lỗi thường gặp

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| ESP32 không kết nối được MQTT | Kiểm tra IP broker, tường lửa (mở cổng 1883) và `listener` trong `mosquitto.conf` |
| `Connection refused` khi chạy collector | Mosquitto chưa chạy hoặc sai `MQTT_HOST`/`MQTT_PORT` |
| `401 Unauthorized` từ InfluxDB | Token sai hoặc không có quyền ghi vào bucket |
| Dashboard trống | Chưa có dữ liệu trong khoảng thời gian chọn, hoặc sai tên bucket/measurement |
| Giá trị DHT22 là `NaN` | Kiểm tra dây nối và điện trở kéo lên 10kΩ cho chân DATA |
| Lỗi `paho-mqtt` về `CallbackAPIVersion` | Dùng `paho-mqtt>=2.0`: khởi tạo `mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)` |

---

## 9. Kết quả thực nghiệm

> Phần này điền sau khi chạy thực nghiệm.

- Ảnh dashboard: xem thư mục [`docs/screenshots/`](docs/screenshots/)
- Độ trễ end-to-end: trung bình `... ms`, P95 `... ms`
- Số bản ghi thu thập: `...` (hợp lệ `...`, bị loại `...`)
- Số outlier phát hiện được: `...`

## 10. Mở rộng (nếu có thực hiện)

- [ ] Edge processing trên ESP32 (lọc nhiễu, gửi theo ngưỡng)
- [ ] Bảo mật MQTT bằng TLS / xác thực username-password
- [ ] So sánh hiệu năng InfluxDB và MongoDB Time-Series

## 11. Tài liệu tham khảo

- Eclipse Mosquitto: <https://mosquitto.org/documentation/>
- InfluxDB 2.x: <https://docs.influxdata.com/influxdb/v2/>
- paho-mqtt: <https://eclipse.dev/paho/files/paho.mqtt.python/html/>
- influxdb-client (Python): <https://github.com/influxdata/influxdb-client-python>
- Streamlit: <https://docs.streamlit.io/>

## 12. Giấy phép

Dự án phục vụ mục đích học tập trong học phần IoT và Ứng dụng.
