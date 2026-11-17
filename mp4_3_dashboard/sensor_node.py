#!/usr/bin/env python3
"""MP 4.3 - generic simulated sensor publisher (one process per sensor).

  python3 sensor_node.py --topic plant1/lineA/temperature --lo 50 --hi 100 --interval 2 --status-topic plant1/lineA/status
Every reading is QoS 1 and RETAINED (so late joiners see the latest value).  If --status-topic is given the node
registers a Last Will ("offline", retained, QoS 1) before connecting and publishes "online" after connecting.
"""
import argparse, datetime, random, time
import paho.mqtt.client as mqtt

p = argparse.ArgumentParser()
p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=1883)
p.add_argument("--topic", required=True)
p.add_argument("--lo", type=float, required=True); p.add_argument("--hi", type=float, required=True)
p.add_argument("--interval", type=float, default=2.0)
p.add_argument("--qos", type=int, default=1)
p.add_argument("--status-topic", default="", help="enables LWT + birth message on this topic")
p.add_argument("--keepalive", type=int, default=5)
p.add_argument("--seed", type=int, default=None)
a = p.parse_args()
if a.seed is not None: random.seed(a.seed)
ts = lambda: datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
cid = "node-" + a.topic.replace("/", "-")
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
if a.status_topic:
    c.will_set(a.status_topic, "offline", qos=1, retain=True)          # LWT registered BEFORE connect
def on_connect(cl, u, f, rc, pr):
    print(f"[{ts()}] {cid} connected rc={rc}" + (f" (LWT on {a.status_topic})" if a.status_topic else ""), flush=True)
    if a.status_topic: cl.publish(a.status_topic, "online", qos=1, retain=True)
c.on_connect = on_connect
c.connect(a.host, a.port, a.keepalive); c.loop_start(); time.sleep(0.4)
while True:
    v = round(random.uniform(a.lo, a.hi), 2)
    c.publish(a.topic, str(v), qos=a.qos, retain=True)
    print(f"[{ts()}] {a.topic} = {v}", flush=True)
    time.sleep(a.interval)
