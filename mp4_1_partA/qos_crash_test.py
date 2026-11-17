#!/usr/bin/env python3
"""Lab Task 2 - ungraceful disconnect at QoS 0 / 1 / 2.

For every trial a child process connects (persistent session), publishes ONE final reading and
then dies with os._exit() (no DISCONNECT, no flush) `delay_ms` milliseconds after publish().
A separate subscriber (QoS 2) counts how many copies reached it.
usage: qos_crash_test.py [--trials 10]
"""
import argparse, subprocess, sys, time, uuid
import paho.mqtt.client as mqtt

CHILD = r'''
import os, sys, time, paho.mqtt.client as mqtt
qos, delay, payload = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="crash-pub-"+payload, clean_session=False, protocol=mqtt.MQTTv311)
c.connect("127.0.0.1", 1883, 60); c.loop_start(); time.sleep(0.3)
c.publish("factory/line3/crashtest", payload, qos=qos)
time.sleep(delay/1000.0)
os._exit(1)          # hard crash: no loop_stop(), no disconnect()
'''
ap = argparse.ArgumentParser(); ap.add_argument("--trials", type=int, default=10); a = ap.parse_args()
got = {}
def on_msg(c, u, m): got[m.payload.decode()] = got.get(m.payload.decode(), 0) + 1
sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="crash-collector")
sub.on_message = on_msg
sub.connect("127.0.0.1", 1883, 60); sub.subscribe("factory/line3/crashtest", qos=2); sub.loop_start(); time.sleep(0.5)
print(f"{'QoS':<4}{'crash delay':<13}{'trials':<8}{'received':<10}{'lost':<6}{'duplicates'}")
for delay in (0, 30):
    for qos in (0, 1, 2):
        tags = []
        for i in range(a.trials):
            tag = f"q{qos}d{delay}-{uuid.uuid4().hex[:6]}"; tags.append(tag)
            subprocess.run([sys.executable, "-c", CHILD, str(qos), str(delay), tag])
        time.sleep(1.5)
        rec = sum(1 for t in tags if got.get(t, 0) >= 1)
        dup = sum(max(0, got.get(t, 0) - 1) for t in tags)
        print(f"{qos:<4}{str(delay)+' ms':<13}{a.trials:<8}{rec:<10}{a.trials-rec:<6}{dup}")
