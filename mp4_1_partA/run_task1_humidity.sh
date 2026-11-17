#!/bin/bash
# Lab Task 1: second sensor on factory/line3/humidity; alert subscriber now uses factory/line3/+
cd "$(dirname "$0")"; LOG=../logs; export PYTHONUNBUFFERED=1
python3 alert_subscriber.py --topic "factory/line3/+" > $LOG/A_task1_alert.log 2>&1 & AL=$!
sleep 1.5
python3 sensor_publisher.py --seed 8 --interval 3 --count 5 > $LOG/A_task1_temp_pub.log 2>&1 &
python3 sensor_publisher.py --client-id line3-humidity-sensor --topic factory/line3/humidity \
        --status-topic factory/line3/humidity-status --min 30 --max 70 --seed 3 --interval 3 --count 5 \
        > $LOG/A_task1_hum_pub.log 2>&1 &
sleep 18; kill $AL
