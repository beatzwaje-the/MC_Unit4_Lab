#!/usr/bin/env python3
"""Lab Task 3 helper - counts unique sequence numbers received; survives broker restarts."""
import argparse, sys, time
import paho.mqtt.client as mqtt
p = argparse.ArgumentParser(); p.add_argument("--topic", default="factory/line3/seq"); p.add_argument("--out", required=True)
a = p.parse_args(); seen = set()
def on_connect(c, u, f, rc, pr): c.subscribe(a.topic, qos=1)
def on_message(c, u, m): seen.add(int(m.payload.decode()))
def dump():
    open(a.out, "w").write(",".join(map(str, sorted(seen))))
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="seq-counter")
c.on_connect, c.on_message = on_connect, on_message
c.reconnect_delay_set(1, 1)
c.connect_async("127.0.0.1", 1883, 60); c.loop_start()
try:
    while True: time.sleep(0.5); dump()
except KeyboardInterrupt: dump()
