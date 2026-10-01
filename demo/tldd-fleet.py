#!/usr/bin/env python3
"""
Atosu demo fleet — STANDBY virtual devices (publishing, not yet connected).
Lets the presenter 'Add a device' live in the Connect wizard and get instant data.

  TLDD-02  (second LV motor)  -> topic atosu/tldd-02/telemetry
  PMP-07   (centrifugal pump) -> topic atosu/pmp-07/telemetry   (different signal set)

Each has a periodic FAULT burst so a freshly-added device also shows an event.
No real device / no Orbit data.
"""
import os, time, json, math, random, socket, threading
import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "mosquitto")
PORT = int(os.getenv("MQTT_PORT", "1883"))

def connect(cid):
    c = mqtt.Client(client_id=cid)
    while True:
        try:
            c.connect(HOST, PORT, keepalive=30); c.loop_start()
            print(f"[{cid}] connected to {HOST}:{PORT}", flush=True); return c
        except (socket.error, OSError) as e:
            print(f"[{cid}] broker not ready ({e}); retry 3s", flush=True); time.sleep(3)

def run_motor(device_id, topic):
    c = connect(f"{device_id}-sim"); t = 0
    while True:
        fault = (t % 150) >= 130; ph = t*0.15
        vib = 2.0 + 0.4*math.sin(ph) + random.gauss(0,0.15)
        temp = 60 + 5*math.sin(ph*0.3) + random.gauss(0,0.4)
        cur = 11.0 + 0.8*math.sin(ph*0.5) + random.gauss(0,0.2)
        rpm = 1485 + 8*math.sin(ph*0.4) + random.gauss(0,3)
        state = "RUNNING"
        if fault:
            k = ((t%150)-130)/20.0
            vib += 3.0+4.0*k; temp += 4+8*k; cur += 1+1.5*k; rpm -= 15*k; state="FAULT"
        c.publish(topic, json.dumps({
            "timestamp": int(time.time()*1000), "deviceId": device_id,
            "temperature_c": round(temp,2), "vibration_mm_s": round(max(0,vib),3),
            "current_a": round(cur,2), "rpm": round(rpm,1), "machine_state": state}))
        t += 1; time.sleep(1)

def run_pump(device_id, topic):
    c = connect(f"{device_id}-sim"); t = 0
    while True:
        fault = (t % 180) >= 160; ph = t*0.12
        flow = 42 + 3*math.sin(ph*0.4) + random.gauss(0,0.5)
        suction = 1.8 + 0.1*math.sin(ph*0.6) + random.gauss(0,0.03)
        discharge = 6.4 + 0.2*math.sin(ph*0.5) + random.gauss(0,0.05)
        vib = 1.6 + 0.3*math.sin(ph) + random.gauss(0,0.12)
        temp = 55 + 4*math.sin(ph*0.3) + random.gauss(0,0.3)
        state = "RUNNING"
        if fault:  # cavitation-like: flow down, vibration up, discharge erratic
            k = ((t%180)-160)/20.0
            flow -= 8*k; vib += 2.5+3*k; discharge -= 1.0*k; state="CAVITATION"
        c.publish(topic, json.dumps({
            "timestamp": int(time.time()*1000), "deviceId": device_id,
            "flow_m3h": round(flow,2), "suction_pressure_bar": round(suction,3),
            "discharge_pressure_bar": round(discharge,3), "vibration_mm_s": round(max(0,vib),3),
            "temperature_c": round(temp,2), "pump_state": state}))
        t += 1; time.sleep(1)

threading.Thread(target=run_motor, args=("TLDD-02","atosu/tldd-02/telemetry"), daemon=True).start()
threading.Thread(target=run_pump,  args=("PMP-07","atosu/pmp-07/telemetry"), daemon=True).start()
print("[fleet] TLDD-02 + PMP-07 publishing (standby for live add-device demo)", flush=True)
while True: time.sleep(60)
