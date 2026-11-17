#!/bin/bash
# Lab Task 3: kill + restart the broker mid-run, publisher at QoS 0 vs QoS 1 (100 numbered readings, 5/s)
cd "$(dirname "$0")"; LOG=../logs; export PYTHONUNBUFFERED=1
start_broker(){ (cd ../broker && nohup amqtt -c broker_config.yaml >/dev/null 2>&1 & echo $! > /tmp/brk.pid); sleep 3; }
for Q in 0 1; do
  pkill -f "amqtt -c" ; sleep 1; start_broker
  python3 count_subscriber.py --out /tmp/seq_q$Q.txt & CNT=$!
  sleep 1.5
  python3 qos_loss_test.py --qos $Q --count 100 --interval 0.2 > $LOG/A_task3_pub_q$Q.log 2>&1 & PUB=$!
  sleep 6;  echo "[qos $Q] t=6s  broker KILLED";   pkill -f "amqtt -c"
  sleep 4;  echo "[qos $Q] t=10s broker RESTARTED"; start_broker
  wait $PUB; sleep 2; kill -INT $CNT; sleep 1
  python3 - <<PY | tee -a $LOG/A_task3_summary.log
s=open("/tmp/seq_q$Q.txt").read().strip(); got={int(x) for x in s.split(",")} if s else set()
miss=sorted(set(range(100))-got)
print(f"QoS $Q: received {len(got)}/100, lost {len(miss)}", ("(first lost #%d, last lost #%d)"%(miss[0],miss[-1])) if miss else "")
PY
done
