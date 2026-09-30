#!/usr/bin/env python3
"""
TLDD-01  —  Test Lab Dummy Device (virtual)
Publishes multi-signal telemetry over MQTT every second, exactly like a real
lab/field device would, so Atosu StreamPipes can ingest + visualise it.
No real device / no Orbit data is used — everything here is synthetic.

Every ~120 s the device enters a 20 s FAULT burst (vibration + temperature +
current spike) so the dashboard shows a clear, repeatable event.
"""
import os, time, json, math, random, socket

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC     = os.getenv("MQTT_TOPIC", "atosu/tldd/telemetry")
DEVICE_ID = os.getenv("DEVICE_ID", "TLDD-01")
PERIOD_S  = float(os.getenv("PERIOD_S", "1.0"))

import paho.mqtt.client as mqtt

def connect():
    c = mqtt.Client(client_id=f"{DEVICE_ID}-sim")
    while True:
        try:
            c.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
            c.loop_start()
            print(f"[TLDD] connected to {MQTT_HOST}:{MQTT_PORT}, publishing to '{TOPIC}'", flush=True)
            return c
        except (socket.error, OSError) as e:
            print(f"[TLDD] broker not ready ({e}); retrying in 3s", flush=True)
            time.sleep(3)

def main():
    client = connect()
    t = 0
    # baselines for a small motor/pump-like asset
    while True:
        # fault burst: 20 s out of every 120 s
        in_fault = (t % 120) >= 100
        phase = t * 0.15

        temperature = 62 + 6*math.sin(phase*0.3) + random.gauss(0, 0.4)
        vibration   = 2.1 + 0.4*math.sin(phase)   + random.gauss(0, 0.15)
        current     = 11.5 + 0.8*math.sin(phase*0.5) + random.gauss(0, 0.2)
        pressure    = 4.3 + 0.2*math.sin(phase*0.7) + random.gauss(0, 0.05)
        rpm         = 1480 + 8*math.sin(phase*0.4) + random.gauss(0, 3)
        humidity    = 46 + 3*math.sin(phase*0.05) + random.gauss(0, 0.3)
        state       = "RUNNING"

        if in_fault:
            # bearing-fault-like signature: vibration + temp + current climb
            k = ((t % 120) - 100) / 20.0        # 0..1 through the burst
            vibration   += 3.5 + 4.0*k
            temperature += 4.0 + 8.0*k
            current     += 1.0 + 1.5*k
            rpm         -= 15*k
            state        = "FAULT"

        payload = {
            "timestamp":      int(time.time() * 1000),
            "deviceId":       DEVICE_ID,
            "temperature_c":  round(temperature, 2),
            "vibration_mm_s": round(max(0, vibration), 3),
            "current_a":      round(current, 2),
            "pressure_bar":   round(pressure, 3),
            "rpm":            round(rpm, 1),
            "humidity_pct":   round(humidity, 1),
            "machine_state":  state,
        }
        try:
            client.publish(TOPIC, json.dumps(payload), qos=0)
            if t % 10 == 0:
                print(f"[TLDD] t={t}s {state} vib={payload['vibration_mm_s']} temp={payload['temperature_c']}", flush=True)
        except Exception as e:
            print(f"[TLDD] publish failed ({e}); reconnecting", flush=True)
            try: client.loop_stop()
            except Exception: pass
            client = connect()
        t += 1
        time.sleep(PERIOD_S)

if __name__ == "__main__":
    main()
