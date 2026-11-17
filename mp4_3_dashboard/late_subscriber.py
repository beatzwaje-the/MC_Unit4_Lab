#!/usr/bin/env python3
"""MP 4.3 - late-joining probe: subscribes to plant1/# for a few seconds and prints what arrives immediately."""
import argparse, datetime, time
import paho.mqtt.client as mqtt
p = argparse.ArgumentParser(); p.add_argument("--seconds", type=float, default=2.0); a = p.parse_args()
ts = lambda: datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
def on_connect(c, u, f, rc, pr): print(f"[{ts()}] LATE-JOINER connected, subscribing plant1/#", flush=True); c.subscribe("plant1/#", qos=1)
def on_message(c, u, m): print(f"[{ts()}] LATE-JOINER got {m.topic:<28} {m.payload.decode():<8} retain-flag={m.retain}", flush=True)
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="late-joiner"); c.on_connect, c.on_message = on_connect, on_message
c.connect("127.0.0.1", 1883, 60); c.loop_start(); time.sleep(a.seconds); c.disconnect()
