#!/bin/bash
# MP 4.3 end-to-end demo: multi-sensor operation, retained message (late joiner), new topic without code change, LWT.
cd "$(dirname "$0")"; LOG=../logs; export PYTHONUNBUFFERED=1; OUT=$LOG/C_sample_log.txt
say(){ echo "" | tee -a $OUT; echo "######## $1" | tee -a $OUT; }
: > $OUT
python3 aggregator.py --csv $LOG/C_readings_log.csv --summary 9 >> $OUT 2>&1 & AGG=$!
sleep 1.5
say "PHASE 1: three publishers on plant1/lineA/temperature, plant1/lineA/vibration, plant1/lineB/temperature (QoS 1, retained)"
python3 sensor_node.py --topic plant1/lineA/temperature --lo 60 --hi 95 --interval 2   --status-topic plant1/lineA/status --seed 4  > $LOG/C_pub_lineA_temp.log 2>&1 & P1=$!
python3 sensor_node.py --topic plant1/lineA/vibration   --lo 1  --hi 9  --interval 1.5 --seed 5                                   > $LOG/C_pub_lineA_vib.log  2>&1 & P2=$!
python3 sensor_node.py --topic plant1/lineB/temperature --lo 55 --hi 90 --interval 3   --status-topic plant1/lineB/status --seed 6  > $LOG/C_pub_lineB_temp.log 2>&1 & P3=$!
sleep 12
say "PHASE 2: late-joining subscriber (retained messages delivered immediately)"
python3 late_subscriber.py --seconds 1.5 >> $OUT 2>&1
sleep 1
say "PHASE 3: NEW sensor plant1/lineC/temperature started at run time (aggregator code NOT touched)"
python3 sensor_node.py --topic plant1/lineC/temperature --lo 60 --hi 100 --interval 2 --status-topic plant1/lineC/status --seed 9 > $LOG/C_pub_lineC_temp.log 2>&1 & P4=$!
sleep 7
say "PHASE 4: ungraceful termination (kill -9) of plant1/lineA/temperature publisher -> broker publishes LWT"
echo "[$(date +%H:%M:%S.%3N)] kill -9 lineA temperature publisher (pid $P1)" | tee -a $OUT; kill -9 $P1
sleep 11
kill $P2 $P3 $P4 2>/dev/null; sleep 0.5; kill $AGG; sleep 1
echo "demo finished"
