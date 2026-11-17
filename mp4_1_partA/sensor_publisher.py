#!/usr/bin/env python3
"""MP 4.1 Part A - simulated sensor publisher (MQTT).

Defaults reproduce the lab manual exactly:
  client id  line3-temp-sensor
  topic      factory/line3/temperature   (QoS 1, every 5 s, value 60..95)
  LWT        factory/line3/status = "offline" (QoS 1, retained), registered BEFORE connect
  birth      "online" (retained) published immediately after connect

Command-line options let the same script act as the humidity sensor (Lab Task 1)
and run the QoS 0 / QoS 2 experiments (Lab Tasks 2 and 3).
"""
import argparse, random, time, datetime
import paho.mqtt.client as mqtt

p = argparse.ArgumentParser()
p.add_argument("--host", default="127.0.0.1")
p.add_argument("--port", type=int, default=1883)
p.add_argument("--client-id", default="line3-temp-sensor")
p.add_argument("--topic", default="factory/line3/temperature")
p.add_argument("--status-topic", default="factory/line3/status")
p.add_argument("--qos", type=int, default=1, choices=[0, 1, 2])
p.add_argument("--interval", type=float, default=5.0)
p.add_argument("--min", type=float, default=60.0)
p.add_argument("--max", type=float, default=95.0)
p.add_argument("--keepalive", type=int, default=5, help="short keep-alive so the LWT demo is quick")
p.add_argument("--count", type=int, default=0, help="stop after N readings (0 = run forever)")
p.add_argument("--seed", type=int, default=None)
p.add_argument("--no-retain", action="store_true", help="do not retain readings (Lab Task 3 baseline)")
p.add_argument("--clean-exit", action="store_true", help="send a proper DISCONNECT at the end (LWT NOT fired)")
a = p.parse_args()
if a.seed is not None:
    random.seed(a.seed)

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=a.client_id)
# 1) LWT must be registered BEFORE connecting
client.will_set(a.status_topic, payload="offline", qos=1, retain=True)

def on_connect(c, userdata, flags, rc, props):
    print(f"[{ts()}] CONNECTED to {a.host}:{a.port} rc={rc} client_id={a.client_id}", flush=True)
    # 2) birth message right after connecting
    c.publish(a.status_topic, "online", qos=1, retain=True)
    print(f"[{ts()}] STATUS  {a.status_topic} <- online (retain)", flush=True)

client.on_connect = on_connect
client.connect(a.host, a.port, keepalive=a.keepalive)
client.loop_start()
time.sleep(0.5)

n = 0
try:
    while True:
        n += 1
        value = round(random.uniform(a.min, a.max), 1)
        # Retain every reading so the broker always holds the LATEST value for late joiners
        info = client.publish(a.topic, str(value), qos=a.qos, retain=not a.no_retain)
        print(f"[{ts()}] PUBLISH #{n:<3} {a.topic} = {value} (qos={a.qos}, retain={not a.no_retain}, mid={info.mid})", flush=True)
        if a.count and n >= a.count:
            break
        time.sleep(a.interval)
finally:
    if a.clean_exit:
        client.publish(a.status_topic, "offline (clean)", qos=1, retain=True).wait_for_publish()
        client.disconnect()
        print(f"[{ts()}] clean DISCONNECT sent (broker will NOT publish the LWT)", flush=True)
    client.loop_stop()
