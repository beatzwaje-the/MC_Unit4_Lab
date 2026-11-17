# Mobile Communications - Unit 4 Mini Projects (source code)

| Folder | Content |
|---|---|
| `broker/` | `broker_config.yaml`, `start_broker.sh` - local MQTT broker on 127.0.0.1:1883 (pure-Python *amqtt*; a stand-in for Mosquitto - `mosquitto -p 1883` works equally well) |
| `mp4_1_partA/` | `sensor_publisher.py`, `dashboard_subscriber.py`, `alert_subscriber.py` + demo/lab-task scripts (`run_demo_partA.sh`, `run_task1_humidity.sh`, `qos_crash_test.py`, `run_task3_unreliable_network.sh`) |
| `mp4_1_partB/` | `link_budget_compare.py` (NB-IoT / LTE-M / LoRaWAN / 5G RedCap link budget + battery life, Lab Tasks 4-6) |
| `mp4_2_selector/` | `iot_selector.py` - rule-based connectivity technology selector (+ `--interactive`) |
| `mp4_3_dashboard/` | `sensor_node.py`, `aggregator.py`, `late_subscriber.py`, `run_demo_4_3.sh`, `sample_log.txt`, `sample_readings_log.csv` |
| `logs/` | Real console output captured while running everything |

## Quick start
```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
./broker/start_broker.sh &                       # or: mosquitto -p 1883
./mp4_1_partA/run_demo_partA.sh                  # Part A: normal / retained / LWT
python3 mp4_1_partB/link_budget_compare.py       # Part B
python3 mp4_2_selector/iot_selector.py           # MP 4.2 (add --interactive for your own scenario)
./mp4_3_dashboard/run_demo_4_3.sh                # MP 4.3
```
