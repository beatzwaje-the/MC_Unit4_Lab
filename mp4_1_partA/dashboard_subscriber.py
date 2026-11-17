#!/usr/bin/env python3
"""MP 4.1 Part A - live operator dashboard: temperature + status, QoS 1."""
import argparse, datetime
import paho.mqtt.client as mqtt

p = argparse.ArgumentParser()
p.add_argument("--host", default="127.0.0.1")
p.add_argument("--port", type=int, default=1883)
p.add_argument("--client-id", default="dashboard")
a = p.parse_args()

TOPICS = [("factory/line3/temperature", 1), ("factory/line3/status", 1)]

def ts():
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

def on_connect(c, u, flags, rc, props):
    print(f"[{ts()}] DASHBOARD connected rc={rc}; subscribing {[t for t,_ in TOPICS]}", flush=True)
    c.subscribe(TOPICS)

def on_message(c, u, msg):
    tag = "RETAINED" if msg.retain else "live    "
    print(f"[{ts()}] DASHBOARD {tag} {msg.topic:<28} {msg.payload.decode():<8} (qos={msg.qos})", flush=True)

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=a.client_id)
c.on_connect, c.on_message = on_connect, on_message
c.connect(a.host, a.port, 60)
c.loop_forever()
