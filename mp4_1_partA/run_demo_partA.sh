#!/bin/bash
# Reproduces the three Part A demonstrations (normal operation, retained message for a late
# subscriber, LWT on ungraceful termination). Broker must already be listening on 127.0.0.1:1883.
cd "$(dirname "$0")"; LOG=../logs; export PYTHONUNBUFFERED=1
mark(){ for f in $LOG/A_*.log; do echo "------ $1 ------" >> $f; done; }
rm -f $LOG/A_*.log; touch $LOG/A_publisher.log $LOG/A_dashboard.log $LOG/A_dashboard_late.log $LOG/A_alert.log
python3 dashboard_subscriber.py  >> $LOG/A_dashboard.log 2>&1 & DASH=$!
python3 alert_subscriber.py      >> $LOG/A_alert.log    2>&1 & ALERT=$!
sleep 1.5
mark "PHASE 1: normal operation (publisher QoS1, 5 s interval)"
python3 sensor_publisher.py --seed 8 >> $LOG/A_publisher.log 2>&1 & PUB=$!
sleep 17
mark "PHASE 2: dashboard killed and restarted mid-run (retained-message test)"
kill $DASH; sleep 1.5
python3 dashboard_subscriber.py --client-id dashboard-late >> $LOG/A_dashboard_late.log 2>&1 & DASH2=$!
sleep 6
mark "PHASE 3: publisher hard-killed with SIGKILL (LWT test)"
echo "[$(date +%H:%M:%S.%3N)] kill -9 publisher (pid $PUB)" | tee -a $LOG/A_publisher.log
kill -9 $PUB
sleep 4
kill $DASH2 $ALERT 2>/dev/null
echo "demo finished"
