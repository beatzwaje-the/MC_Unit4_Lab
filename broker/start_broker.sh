#!/bin/sh
# Local MQTT broker for the lab (pure-Python amqtt, stands in for Mosquitto).
# If you have Mosquitto installed, simply run:  mosquitto -p 1883
pip install amqtt >/dev/null 2>&1
amqtt -c "$(dirname "$0")/broker_config.yaml"
