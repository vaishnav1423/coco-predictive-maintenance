"""
Synthetic predictive-maintenance data: IoT sensors + ERP parts + maintenance records + OEE log.
Run:  uv run python generate_pdm_data.py     (needs numpy and pandas; pdm_docs.py must be beside it)
Output: ./data_pdm/*.csv.  ALL DATA IS FAKE.
Keep ground_truth_failures.csv OUT of Snowflake; use it only to check your model.
"""
import os
import numpy as np
import pandas as pd
from pdm_docs import build_docs

rng = np.random.default_rng(7)
START, DAYS, STEP = pd.Timestamp("2026-06-01"), 120, 30          # 30-minute readings
SPD = 24 * 60 // STEP                                             # steps per day (48)
N = DAYS * SPD
IDX = pd.date_range(START, periods=N, freq=f"{STEP}min")
OUT = "data_pdm"
os.makedirs(OUT, exist_ok=True)

# ---------------- reference data ----------------
PLANTS = {"Pune": "PUN", "Chennai": "CHE", "Aurangabad": "AUR"}
TYPES = {  # n assets, rated rpm, baseline vibration (mm/s), temp (C), current (A), ideal cycle (s), runs 24x7?
    "CNC_MACHINE": dict(n=6, rpm=3000, vib=1.8, temp=55, cur=22, cycle=45, cont=False),
    "PUMP":        dict(n=6, rpm=1450, vib=2.2, temp=48, cur=15, cycle=5,  cont=True),
    "COMPRESSOR":  dict(n=5, rpm=1800, vib=2.8, temp=70, cur=40, cycle=10, cont=True),
    "MOTOR":       dict(n=7, rpm=1500, vib=1.5, temp=60, cur=28, cycle=8,  cont=True),
    "CONVEYOR":    dict(n=6, rpm=900,  vib=1.2, temp=40, cur=10, cycle=6,  cont=False),
}
MODES = {"BEARING_WEAR": ("B", 2.0, (24, 48)), "IMBALANCE_MISALIGNMENT": ("I", 1.5, (8, 16)),
         "OVERHEATING": ("H", 2.0, (12, 24)), "LUBRICATION_LOSS": ("L", 1.5, (6, 12)),
         "MOTOR_ELECTRICAL": ("E", 2.0, (24, 72))}           # key, curve shape, repair hours
MODE_W = {"CNC_MACHINE": [.30, .10, .20, .25, .15], "PUMP": [.35, .25, .10, .10, .20],
          "COMPRESSOR": [.20, .10, .30, .25, .15], "MOTOR": [.30, .15, .15, .05, .35],
          "CONVEYOR": [.30, .30, .10, .10, .20]}
MODE_NAMES = list(MODES)
DOWN_COST = {"A": 120000, "B": 60000, "C": 25000}
RESP_H = {"A": (0.5, 1.5), "B": (1, 3), "C": (2, 6)}
TECHS = ["R. Patil", "S. Iyer", "A. Khan", "M. Deshmukh", "K. Nair", "V. Joshi", "P. Reddy", "D. Kulkarni"]
MAKERS = ["Siemens", "ABB", "Kirloskar", "Atlas Copco", "Bosch Rexroth", "Crompton", "Haas", "Grundfos"]

PARTS = [  # name, failure mode, compatible types, unit cost INR
    ("Deep groove bearing 6208", "BEARING_WEAR", ["MOTOR", "PUMP", "CONVEYOR", "COMPRESSOR"], 3800),
    ("Spindle bearing set", "BEARING_WEAR", ["CNC_MACHINE"], 42000),
    ("Flexible coupling element", "IMBALANCE_MISALIGNMENT", ["MOTOR", "PUMP", "COMPRESSOR", "CONVEYOR"], 6500),
    ("Balancing weight kit", "IMBALANCE_MISALIGNMENT", list(TYPES), 2200),
    ("Cooling fan assembly", "OVERHEATING", list(TYPES), 5200),
    ("Thermostat valve", "OVERHEATING", ["COMPRESSOR", "PUMP", "CNC_MACHINE"], 3100),
    ("Heat exchanger gasket set", "OVERHEATING", ["COMPRESSOR"], 8800),
    ("Lubrication pump", "LUBRICATION_LOSS", ["CNC_MACHINE", "COMPRESSOR"], 14500),
    ("Grease cartridge pack", "LUBRICATION_LOSS", list(TYPES), 1200),
    ("Oil filter", "LUBRICATION_LOSS", ["COMPRESSOR", "PUMP"], 1800),
    ("Motor winding rewind kit", "MOTOR_ELECTRICAL", ["MOTOR", "PUMP", "COMPRESSOR", "CONVEYOR"], 38000),
    ("Contactor 40A", "MOTOR_ELECTRICAL", list(TYPES), 4200),
    ("VFD control board", "MOTOR_ELECTRICAL", ["CNC_MACHINE", "CONVEYOR", "MOTOR"], 26000),
]
NOTES = {
    "BEARING_WEAR": ["Drive-end bearing found worn with metal particles in the grease. Replaced bearing, re-greased and checked alignment. Vibration after restart {v} mm/s.",
                     "Noise and high vibration reported before the stop. Bearing race scoring found. Bearing replaced, run test OK at {v} mm/s."],
    "IMBALANCE_MISALIGNMENT": ["Coupling bolts loose and slight shaft misalignment found. Re-aligned, tightened foundation bolts and balanced the rotor. Vibration back to {v} mm/s.",
                               "Worn coupling element caused imbalance. Element replaced and shaft re-aligned. Vibration {v} mm/s after restart."],
    "OVERHEATING": ["Cooling fan failure caused a high temperature trip. Fan assembly replaced and heat sink cleaned. Running temperature {t} C after restart.",
                    "Blocked filter and stuck thermostat caused overheating. Cleaned filter, replaced thermostat. Temperature steady at {t} C."],
    "LUBRICATION_LOSS": ["Lubrication line blocked, bearing ran dry and temperature rose. Cleaned line, replaced filter and grease, restored lube schedule. Temperature {t} C.",
                         "Reservoir was empty and grease degraded. Refilled with correct grade and reset the lubrication schedule. Vibration {v} mm/s."],
    "MOTOR_ELECTRICAL": ["Motor tripped on over-current. Winding insulation weak and contactor contacts pitted. Replaced contactor and rewound motor. Current normal at {c} A.",
                         "Drive board fault caused current spikes. Board replaced and terminals tightened. Current {c} A after restart."],
}
EARLY = {"BEARING_WEAR": "unusual noise near the bearing", "IMBALANCE_MISALIGNMENT": "slight shaking at the base",
         "OVERHEATING": "casing warmer than usual", "LUBRICATION_LOSS": "grease looking dry",
         "MOTOR_ELECTRICAL": "current slightly higher than usual"}

# ---------------- assets ----------------
rows, k = [], 0
for t, c in TYPES.items():
    for i in range(c["n"]):
        k += 1
        plant = list(PLANTS)[k % 3]
        crit = rng.choice(["A", "B", "C"], p=[.3, .45, .25])
        vib = round(c["vib"] * rng.uniform(.9, 1.1), 2)
        tmp = round(c["temp"] * rng.uniform(.95, 1.05), 1)
        rows.append(dict(asset_id=f"AST-{k:03d}", asset_name=f"{t.replace('_', ' ').title()} {i + 1:02d}",
                         asset_type=t, plant=plant, line=f"Line-{rng.integers(1, 4)}", manufacturer=rng.choice(MAKERS),
                         install_date=str((START - pd.Timedelta(days=int(rng.integers(300, 3000)))).date()),
                         criticality=crit, rated_rpm=c["rpm"], baseline_vibration_mm_s=vib,
                         vib_alert_mm_s=round(vib * 2.2, 2), vib_alarm_mm_s=round(vib * 3.0, 2),
                         baseline_temp_c=tmp, temp_alert_c=round(tmp + 15, 1), temp_alarm_c=round(tmp + 25, 1),
                         baseline_current_a=round(c["cur"] * rng.uniform(.9, 1.1), 1),
                         ideal_cycle_seconds=round(c["cycle"] * rng.uniform(.9, 1.1), 1), cont=c["cont"],
                         downtime_cost_per_hour_inr=DOWN_COST[crit]))
assets = pd.DataFrame(rows)
A = assets.set_index("asset_id")

# ---------------- spare parts (ERP) ----------------
prow = []
for pi, (name, mode, types, cost) in enumerate(PARTS, start=1):
    for plant, code in PLANTS.items():
        prow.append(dict(part_id=f"SP-{pi:03d}-{code}", part_name=name, used_for_failure_mode=mode,
                         compatible_asset_types=",".join(types), plant=plant,
                         unit_cost_inr=round(cost * rng.uniform(.92, 1.08)),
                         on_hand_qty=int(0 if rng.random() < .2 else rng.integers(1, 9)), reorder_point=2,
                         lead_time_days=int(rng.integers(5, 31)), supplier_name=f"Supplier {rng.integers(1, 9)}"))
parts = pd.DataFrame(prow)

# ---------------- failure events ----------------
def pick_mode(t):
    return rng.choice(MODE_NAMES, p=MODE_W[t])

events, occupied = [], {a: [] for a in A.index}
for aid, a in A.iterrows():
    for _ in range(rng.choice([0, 1, 2, 3], p=[.2, .4, .3, .1])):
        for _try in range(40):
            mode, D = pick_mode(a.asset_type), int(rng.integers(5, 13))
            cand = parts[(parts.used_for_failure_mode == mode) & (parts.plant == a.plant) &
                         parts.compatible_asset_types.str.contains(a.asset_type)]
            part = cand.iloc[int(rng.integers(len(cand)))]
            resp = rng.uniform(*RESP_H[a.criticality])
            rep = rng.uniform(*MODES[mode][2])
            delay = float(rng.integers(24, 97)) if part.on_hand_qty == 0 else 0.0
            dur = int(np.ceil((resp + rep + delay) * 60 / STEP))
            lo_t, hi_t = (D + 2) * SPD, N - 8 * SPD - dur
            if hi_t <= lo_t:
                continue
            tf = int(rng.integers(lo_t, hi_t))
            lo, hi = tf - D * SPD - 2 * SPD, tf + dur + 3 * SPD
            if any(lo < o_hi and hi > o_lo for o_lo, o_hi in occupied[aid]):
                continue
            occupied[aid].append((lo, hi))
            events.append(dict(asset_id=aid, mode=mode, tf=tf, deg_steps=D * SPD, dur_steps=dur, resp_h=resp,
                               rep_h=rep, delay_h=delay, part=part))
            break

free = [a for a in A.index if all(h < N - 14 * SPD for _, h in occupied[a])]
rng.shuffle(free)
degrading_now = {a: dict(mode=pick_mode(A.loc[a].asset_type), deg_steps=int(rng.integers(6, 10)) * SPD,
                         start=N - int(rng.integers(2, 6)) * SPD) for a in free[:5]}
spikes = {}
for a in free[5:11]:
    spikes[a] = [int(rng.integers(5 * SPD, N - 5 * SPD)) for _ in range(rng.integers(1, 3))]

# ---------------- simulate one asset ----------------
hour = IDX.hour.values + IDX.minute.values / 60
dow = IDX.dayofweek.values
SCHED = ((dow < 5) & (hour >= 6) & (hour < 22)) | ((dow == 5) & (hour >= 6) & (hour < 14))
AMB = 29 + 4 * np.sin(2 * np.pi * (hour - 8) / 24)

def simulate(aid):
    a = A.loc[aid]
    sched = np.ones(N, bool) if a.cont else SCHED.copy()
    prog = {m: np.zeros(N) for m in MODE_NAMES}
    fail_down, pm_down = np.zeros(N, bool), np.zeros(N, bool)
    for ev in (e for e in events if e["asset_id"] == aid):
        s = ev["tf"] - ev["deg_steps"]
        prog[ev["mode"]][s:ev["tf"]] = ((np.arange(s, ev["tf"]) - s) / ev["deg_steps"]) ** MODES[ev["mode"]][1]
        fail_down[ev["tf"]:ev["tf"] + ev["dur_steps"]] = True
    if aid in degrading_now:
        d = degrading_now[aid]
        prog[d["mode"]][d["start"]:] = ((np.arange(d["start"], N) - d["start"]) / d["deg_steps"]) ** MODES[d["mode"]][1]
    pm_days = list(range(int(rng.integers(3, 28)), DAYS, 30))
    for d in pm_days:
        pm_down[d * SPD + 20:d * SPD + 24] = True
    down = fail_down | pm_down
    running = sched & ~down
    p = {MODES[m][0]: prog[m] for m in MODE_NAMES}
    vib_mult = 1 + 2.5 * p["B"] + 1.8 * p["I"] + .10 * p["H"] + 1.2 * p["L"] + .15 * p["E"]
    temp_add = 12 * p["B"] + 3 * p["I"] + 28 * p["H"] + 15 * p["L"] + 8 * p["E"]
    cur_mult = 1 + .10 * p["B"] + .06 * p["I"] + .12 * p["H"] + .08 * p["L"] + .35 * p["E"]
    for s0 in spikes.get(aid, []):                                   # harmless load spikes (false alarms)
        ln = int(rng.integers(4, 11))
        vib_mult[s0:s0 + ln] *= 1.8
        temp_add[s0:s0 + ln] += 5
    eps, lf = rng.normal(0, .02, N), np.ones(N)
    for i in range(1, N):
        lf[i] = .95 * lf[i - 1] + .05 + eps[i]
    vib = a.baseline_vibration_mm_s * (.92 + .16 * lf) * (1 + rng.normal(0, .05, N)) * vib_mult
    cur = a.baseline_current_a * lf * (1 + rng.normal(0, .03, N)) * cur_mult
    spike = (p["E"] > .3) & (rng.random(N) < .06)
    cur = np.where(spike, cur * 1.25, cur)
    rpm = a.rated_rpm * (1 + rng.normal(0, 1, N) * (.004 + .016 * p["I"])) * (1 - .04 * p["E"])
    target = np.where(running, AMB + (a.baseline_temp_c - 30) * (.6 + .4 * lf) + temp_add, AMB)
    temp = pd.Series(target).ewm(alpha=.35).mean().values + rng.normal(0, .3, N)
    vib = np.where(running, vib, .08 + np.abs(rng.normal(0, .02, N)))
    cur, rpm = np.where(running, cur, 0.0), np.where(running, rpm, 0.0)
    df = pd.DataFrame({"reading_ts": IDX.strftime("%Y-%m-%d %H:%M:%S"), "asset_id": aid,
                       "vibration_mm_s": vib.round(3), "temperature_c": temp.round(2),
                       "rpm": rpm.round(1), "motor_current_a": cur.round(2)})
    for c in ["vibration_mm_s", "temperature_c", "rpm", "motor_current_a"]:   # sensor dropouts
        df.loc[rng.random(N) < .004, c] = np.nan
    return df, dict(sched=sched, fail=fail_down, pm=pm_down, ptot=np.maximum.reduce(list(prog.values())), pm_days=pm_days)

readings, prod, pm_info = [], [], {}
shift_ts = IDX - pd.Timedelta(hours=6)
shift_date, shift_no = shift_ts.normalize().values, (shift_ts.hour // 8).values
for aid, a in A.iterrows():
    df, m = simulate(aid)
    readings.append(df)
    pm_info[aid] = m["pm_days"]
    g = pd.DataFrame({"d": shift_date, "s": shift_no, "sched": m["sched"], "fail": m["sched"] & m["fail"],
                      "pm": m["sched"] & m["pm"] & ~m["fail"], "p": m["ptot"]})
    for (d, s), x in g.groupby(["d", "s"]):
        if len(x) != 16 or not x.sched.any():
            continue
        planned, bd, pmm = int(x.sched.sum()) * STEP, int(x.fail.sum()) * STEP, int(x.pm.sum()) * STEP
        small = int(min(rng.exponential(14), 40))
        run = max(planned - bd - pmm - small, 0)
        perf = float(np.clip(.84 + rng.normal(0, .03) - .15 * x.p.mean(), .55, 1))
        qual = float(np.clip(.985 + rng.normal(0, .005) - .06 * x.p.mean(), .85, 1))
        total = int(run * 60 / a.ideal_cycle_seconds * perf)
        prod.append(dict(shift_date=str(pd.Timestamp(d).date()), shift="ABC"[int(s)], asset_id=aid,
                         planned_minutes=planned, breakdown_minutes=bd, planned_maintenance_minutes=pmm,
                         small_stop_minutes=small, ideal_cycle_seconds=a.ideal_cycle_seconds,
                         total_units=total, good_units=int(total * qual)))

# ---------------- work orders ----------------
wos, n = [], 0
def add_wo(aid, typ, prio, created, started, done, cause, desc, part=None, labor=None, delay=0.0):
    global n
    n += 1
    labor = round(labor if labor is not None else 2.0, 1)
    pc = int(part.unit_cost_inr) if part is not None else 0
    wos.append(dict(wo_id=f"WO-{n:05d}", asset_id=aid, wo_type=typ, priority=prio, status="COMPLETED",
                    created_ts=created, started_ts=started, completed_ts=done, cause_code=cause,
                    part_id=None if part is None else part.part_id, part_qty=0 if part is None else 1,
                    labor_hours=labor, parts_cost_inr=pc, total_cost_inr=int(pc + labor * 850),
                    waiting_for_parts_hours=delay, technician=rng.choice(TECHS), description=desc))
PRIO = {"A": "HIGH", "B": "MEDIUM", "C": "LOW"}
for ev in events:
    a, mode, ts = A.loc[ev["asset_id"]], ev["mode"], IDX[ev["tf"]]
    note = rng.choice(NOTES[mode]).format(v=round(a.baseline_vibration_mm_s * rng.uniform(.95, 1.1), 1),
                                          t=int(a.baseline_temp_c + rng.uniform(-2, 3)),
                                          c=round(a.baseline_current_a * rng.uniform(.97, 1.05), 1))
    if ev["delay_h"]:
        note += f" Repair delayed {int(ev['delay_h'])} h waiting for spare part {ev['part'].part_name}."
    add_wo(ev["asset_id"], "CORRECTIVE", PRIO[a.criticality], ts, ts + pd.Timedelta(hours=ev["resp_h"]),
           ts + pd.Timedelta(minutes=ev["dur_steps"] * STEP), mode, note, ev["part"],
           rng.uniform(2, 16), ev["delay_h"])
    if rng.random() < .4:                                            # early-warning inspection note
        t0 = IDX[ev["tf"] - ev["deg_steps"] // 2]
        add_wo(ev["asset_id"], "INSPECTION", "MEDIUM", t0, t0, t0 + pd.Timedelta(hours=1.5), None,
               f"Operator reported {EARLY[mode]}. Readings slightly above normal. Advised to monitor and re-check within 3 days.",
               labor=1.5)
for aid, days in pm_info.items():
    for d in days:
        t0 = IDX[d * SPD + 20]
        add_wo(aid, "PREVENTIVE", "LOW", t0, t0, t0 + pd.Timedelta(hours=2), None,
               rng.choice(["Routine inspection done. Lubrication checked, fasteners tightened, no abnormality found.",
                           "Monthly preventive check completed. Filters cleaned and readings recorded within normal range.",
                           "Scheduled service completed. Belts and couplings inspected, no action needed."]), labor=2.0)
work_orders = pd.DataFrame(wos).sort_values("created_ts").reset_index(drop=True)
for c in ["created_ts", "started_ts", "completed_ts"]:
    work_orders[c] = pd.to_datetime(work_orders[c]).dt.strftime("%Y-%m-%d %H:%M:%S")

# ---------------- ground truth (do NOT load into Snowflake) ----------------
gt = [dict(asset_id=e["asset_id"], event_type="FAILURE", failure_mode=e["mode"],
           degradation_start_ts=IDX[e["tf"] - e["deg_steps"]], failure_ts=IDX[e["tf"]],
           downtime_hours=round(e["dur_steps"] * STEP / 60, 1)) for e in events]
gt += [dict(asset_id=a, event_type="DEGRADING_NOW", failure_mode=d["mode"], degradation_start_ts=IDX[d["start"]],
            failure_ts=None, downtime_hours=None) for a, d in degrading_now.items()]
gt += [dict(asset_id=a, event_type="FALSE_ALARM", failure_mode=None, degradation_start_ts=IDX[s], failure_ts=None,
            downtime_hours=None) for a, ss in spikes.items() for s in ss]

# ---------------- save ----------------
assets.drop(columns="cont").to_csv(f"{OUT}/assets.csv", index=False)
pd.concat(readings).to_csv(f"{OUT}/sensor_readings.csv", index=False)
parts.to_csv(f"{OUT}/spare_parts.csv", index=False)
work_orders.to_csv(f"{OUT}/work_orders.csv", index=False)
pd.DataFrame(prod).to_csv(f"{OUT}/production_log.csv", index=False)
build_docs().to_csv(f"{OUT}/maintenance_docs.csv", index=False)
pd.DataFrame(gt).to_csv(f"{OUT}/ground_truth_failures.csv", index=False)

print(f"assets={len(assets)} readings={N * len(assets)} parts={len(parts)} work_orders={len(work_orders)} "
      f"production_rows={len(prod)} docs={len(build_docs())}")
print("failures by mode:\n", work_orders[work_orders.wo_type == 'CORRECTIVE'].cause_code.value_counts().to_string())
print("currently degrading (hidden):", {a: str(d["mode"]) for a, d in degrading_now.items()})