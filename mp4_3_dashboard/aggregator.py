#!/usr/bin/env python3
"""MP 4.3 - aggregator / logger / per-topic alerting subscriber.

* ONE wildcard subscription ("plant1/+/+", QoS 1) covers every sensor, present and future.
* Every message is timestamped and appended to a CSV log.
* A periodic summary prints the latest value + count/min/mean/max per topic.
* Thresholds are keyed by MEASUREMENT TYPE (last topic level), so a brand-new topic such as plant1/lineC/temperature
  is picked up and alerted on with no code change.  Temperature and vibration thresholds differ.
* "status" topics carry online/offline (birth + Last Will) and are logged as STATUS events.
"""
import argparse, csv, datetime, signal, sys, threading, time
import paho.mqtt.client as mqtt

THRESHOLDS = {"temperature": 85.0, "vibration": 7.0}     # per measurement type; others: log only
p = argparse.ArgumentParser()
p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=1883)
p.add_argument("--filter", default="plant1/+/+")
p.add_argument("--csv", default="readings_log.csv")
p.add_argument("--summary", type=float, default=10.0, help="seconds between summaries")
a = p.parse_args()
ts = lambda: datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
lock = threading.Lock()
stats = {}                      # topic -> dict(last, n, min, max, sum)
status = {}
fh = open(a.csv, "w", newline=""); w = csv.writer(fh); w.writerow(["timestamp", "topic", "payload", "retained", "alert"]); fh.flush()

def on_connect(c, u, f, rc, pr):
    print(f"[{ts()}] AGGREGATOR connected rc={rc}; single subscription: {a.filter} (qos 1)", flush=True)
    c.subscribe(a.filter, qos=1)

def on_message(c, u, m):
    payload = m.payload.decode(); kind = m.topic.rsplit("/", 1)[-1]; alert = ""
    with lock:
        if kind == "status":
            status[m.topic] = payload
            print(f"[{ts()}] STATUS   {m.topic:<28} {payload}{'  (retained)' if m.retain else ''}", flush=True)
        else:
            try: v = float(payload)
            except ValueError: return
            s = stats.setdefault(m.topic, dict(last=v, n=0, min=v, max=v, sum=0.0, new=True))
            if s["n"] == 0:
                print(f"[{ts()}] NEW TOPIC discovered by wildcard: {m.topic}", flush=True)
            s.update(last=v, n=s["n"] + 1, min=min(s["min"], v), max=max(s["max"], v), sum=s["sum"] + v)
            thr = THRESHOLDS.get(kind)
            if thr is not None and v > thr:
                alert = f"ALERT {kind} {v} > {thr}"
                print(f"[{ts()}] ALERT    {m.topic:<28} {v} exceeds {kind} threshold {thr}", flush=True)
            else:
                print(f"[{ts()}] reading  {m.topic:<28} {v}{'  (retained)' if m.retain else ''}", flush=True)
        w.writerow([datetime.datetime.now().isoformat(timespec="milliseconds"), m.topic, payload, int(m.retain), alert]); fh.flush()

def summarise():
    with lock:
        print(f"[{ts()}] ---- SUMMARY (latest per topic) ----", flush=True)
        for t in sorted(stats):
            s = stats[t]
            print(f"           {t:<28} last={s['last']:<7} n={s['n']:<3} min={s['min']:<7} mean={s['sum']/s['n']:<7.2f} max={s['max']}", flush=True)
        for t in sorted(status): print(f"           {t:<28} status={status[t]}", flush=True)

def loop_summary():
    while True: time.sleep(a.summary); summarise()

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="plant1-aggregator")
c.on_connect, c.on_message = on_connect, on_message
c.connect(a.host, a.port, 60)
threading.Thread(target=loop_summary, daemon=True).start()
signal.signal(signal.SIGTERM, lambda *_: (summarise(), fh.close(), sys.exit(0)))
try: c.loop_forever()
except KeyboardInterrupt: summarise(); fh.close()
