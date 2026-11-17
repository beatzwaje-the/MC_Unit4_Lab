#!/usr/bin/env python3
"""Lab Task 3 helper - numbered publisher that keeps running through a broker outage."""
import argparse, time
import paho.mqtt.client as mqtt
p = argparse.ArgumentParser(); p.add_argument("--qos", type=int, required=True)
p.add_argument("--count", type=int, default=100); p.add_argument("--interval", type=float, default=0.2)
a = p.parse_args()
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"seq-pub-q{a.qos}", clean_session=False, protocol=mqtt.MQTTv311)
c.reconnect_delay_set(1, 1)
c.connect_async("127.0.0.1", 1883, 60); c.loop_start(); time.sleep(1.0)
sent_ok = 0
for i in range(a.count):
    r = c.publish("factory/line3/seq", str(i), qos=a.qos)
    # rc != 0 (MQTT_ERR_NO_CONN) means paho refused the message because the socket is down
    # (QoS 0 is then dropped for good; QoS 1/2 are held in the outgoing queue and re-sent)
    if r.rc == 0: sent_ok += 1
    time.sleep(a.interval)
time.sleep(6)   # allow queued QoS1 messages to flush after reconnect
print(f"publisher qos={a.qos}: publish() calls={a.count}, accepted by client={sent_ok}")
