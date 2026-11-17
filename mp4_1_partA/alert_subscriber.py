#!/usr/bin/env python3
"""MP 4.1 Part A - alert subscriber: wildcard subscription + threshold logic."""
import argparse, datetime
import paho.mqtt.client as mqtt

p = argparse.ArgumentParser()
p.add_argument("--host", default="127.0.0.1")
p.add_argument("--port", type=int, default=1883)
p.add_argument("--client-id", default="alert-monitor")
p.add_argument("--topic", default="factory/+/temperature",
               help='Lab Task 1: change to "factory/line3/+" to also receive humidity')
p.add_argument("--threshold", type=float, default=90.0)
a = p.parse_args()

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

def on_connect(c, u, flags, rc, props):
    print(f"[{ts()}] ALERT-SUB connected rc={rc}; subscribing {a.topic} (qos 1), threshold={a.threshold}", flush=True)
    c.subscribe(a.topic, qos=1)

def on_message(c, u, msg):
    try:
        value = float(msg.payload.decode())
    except ValueError:
        return                       # non-numeric payloads (e.g. "online"/"offline" status) are ignored
    # threshold logic is unchanged whichever topic delivered the reading
    if value > a.threshold:
        print(f"[{ts()}] ALERT !!! {msg.topic} = {value} exceeds {a.threshold}", flush=True)
    else:
        print(f"[{ts()}] ok         {msg.topic} = {value}", flush=True)

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=a.client_id)
c.on_connect, c.on_message = on_connect, on_message
c.connect(a.host, a.port, 60)
c.loop_forever()
