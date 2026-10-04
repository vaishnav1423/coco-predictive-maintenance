"""
SYNTHETIC maintenance manuals, SOPs and OEE reference, one row per section (for Cortex Search).
Thresholds match the limits generated in generate_pdm_data.py.
Everything here is fictional; do not present it as real engineering guidance.
"""
import pandas as pd

GENERIC_LIMITS = ("Limits are set per asset from its baseline: ALERT when vibration is at least 2.2x baseline, "
                  "temperature is at least baseline + 15 C, or motor current is at least 1.25x baseline. "
                  "ALARM when vibration is at least 3.0x baseline or temperature is at least baseline + 25 C.")

DOCS = [
    {"doc_id": "MNT-001", "title": "Bearing Wear Guide", "doc_type": "MANUAL", "applies_to": "BEARING_WEAR",
     "version": "2.1", "effective_date": "2026-01-01", "owner": "Reliability Engineering",
     "sections": [
         ("Symptoms and Signals", "Bearing wear shows as a steady rise in vibration, usually over 5 to 12 days, followed by a smaller rise in temperature and motor current. Vibration climbs slowly at first and then quickly in the last days before failure. Audible grinding or whining noise is common."),
         ("Alert Thresholds", GENERIC_LIMITS + " For bearing wear, vibration is the earliest and most reliable signal."),
         ("Likely Causes", "Insufficient or contaminated grease, shaft misalignment, overload, normal end of life, or poor installation. Check the lubrication history before blaming the bearing alone."),
         ("Recommended Actions", "On ALERT, raise an inspection work order within the SOP-001 time limit and re-check vibration every shift. On ALARM, plan a bearing replacement at the next stop. Replace the bearing, re-grease, check alignment, and record vibration after restart."),
         ("Parts and Downtime", "Typical repair takes 24 to 48 hours. Parts: deep groove bearing or spindle bearing set, grease cartridge. Confirm stock at the plant before scheduling."),
     ]},
    {"doc_id": "MNT-002", "title": "Imbalance and Misalignment Guide", "doc_type": "MANUAL", "applies_to": "IMBALANCE_MISALIGNMENT",
     "version": "1.6", "effective_date": "2026-01-01", "owner": "Reliability Engineering",
     "sections": [
         ("Symptoms and Signals", "Imbalance and misalignment raise vibration and make the rotation speed (RPM) less steady. Temperature rises only slightly. Motor current rises a little."),
         ("Alert Thresholds", GENERIC_LIMITS + " An unusually jittery RPM reading together with rising vibration points to this fault."),
         ("Likely Causes", "Loose coupling or foundation bolts, worn coupling element, uneven material build-up on the rotor, or a recent re-installation."),
         ("Recommended Actions", "Inspect coupling and bolts, re-align the shaft with a dial gauge or laser tool, and balance the rotor if needed. Confirm vibration after restart is back near baseline."),
         ("Parts and Downtime", "Typical repair takes 8 to 16 hours. Parts: flexible coupling element, balancing weight kit."),
     ]},
    {"doc_id": "MNT-003", "title": "Overheating and Cooling Fault Guide", "doc_type": "MANUAL", "applies_to": "OVERHEATING",
     "version": "1.4", "effective_date": "2026-01-01", "owner": "Reliability Engineering",
     "sections": [
         ("Symptoms and Signals", "Overheating shows as a rapid temperature rise over several days, with a modest rise in motor current. Vibration changes very little, which separates this fault from bearing wear."),
         ("Alert Thresholds", GENERIC_LIMITS + " Temperature is the leading signal for this fault."),
         ("Likely Causes", "Failed cooling fan, blocked heat exchanger or filter, stuck thermostat valve, high ambient temperature, or low coolant flow."),
         ("Recommended Actions", "Check the cooling fan and airflow, clean the heat exchanger and filters, test the thermostat, and verify coolant flow. If temperature reaches ALARM, reduce load immediately and plan a stop."),
         ("Parts and Downtime", "Typical repair takes 12 to 24 hours. Parts: cooling fan assembly, thermostat valve, heat exchanger gasket set."),
     ]},
    {"doc_id": "MNT-004", "title": "Lubrication Loss Guide", "doc_type": "MANUAL", "applies_to": "LUBRICATION_LOSS",
     "version": "1.3", "effective_date": "2026-01-01", "owner": "Reliability Engineering",
     "sections": [
         ("Symptoms and Signals", "Lubrication loss raises temperature steadily, with a later rise in vibration. Both signals move together, which separates it from a pure cooling fault."),
         ("Alert Thresholds", GENERIC_LIMITS),
         ("Likely Causes", "Blocked lubrication line, empty reservoir, degraded grease, wrong grease grade, or a missed lubrication schedule."),
         ("Recommended Actions", "Check reservoir level and lines, replace filters, apply the correct grease, and restore the lubrication schedule. Re-check temperature and vibration for two shifts."),
         ("Parts and Downtime", "Typical repair takes 6 to 12 hours. Parts: grease cartridge pack, oil filter, lubrication pump."),
     ]},
    {"doc_id": "MNT-005", "title": "Motor and Electrical Fault Guide", "doc_type": "MANUAL", "applies_to": "MOTOR_ELECTRICAL",
     "version": "1.7", "effective_date": "2026-01-01", "owner": "Electrical Maintenance",
     "sections": [
         ("Symptoms and Signals", "Electrical faults show as rising and spiky motor current, a small drop in RPM and a mild temperature rise. Vibration barely changes. A current rise of 25 percent or more over baseline is an ALERT."),
         ("Alert Thresholds", GENERIC_LIMITS + " For electrical faults motor current is the main signal."),
         ("Likely Causes", "Winding insulation breakdown, pitted contactor contacts, loose terminals, drive board faults, or voltage imbalance."),
         ("Recommended Actions", "Measure insulation resistance, inspect the contactor and terminals, check the drive board, and plan a motor rewind if insulation is poor. Isolate power before any inspection."),
         ("Parts and Downtime", "Typical repair takes 24 to 72 hours. Parts: contactor 40A, motor winding rewind kit, VFD control board."),
     ]},
    {"doc_id": "SOP-001", "title": "Alert Triage and Escalation", "doc_type": "SOP", "applies_to": "ALL",
     "version": "3.0", "effective_date": "2026-01-01", "owner": "Maintenance Manager",
     "sections": [
         ("Severity Levels", "ALERT means an early warning: schedule an inspection. ALARM means act now: reduce load and plan a stop. A predicted failure with probability of 0.6 or higher within 7 days is treated as an ALERT even if sensors are below their limits."),
         ("Response Time Limits", "ALARM on criticality A assets: acknowledge within 15 minutes and inspect within 2 hours. Criticality B: 1 hour and 8 hours. Criticality C: 4 hours and 48 hours. ALERT on criticality A: acknowledge within 2 hours and inspect by the next planned stop. Criticality B: 8 hours and 3 days. Criticality C: 24 hours and 7 days."),
         ("Triage Steps", "Confirm the signal is real (not a sensor dropout or a short load spike), compare with the last work orders on the asset, check spare part stock, then decide: monitor, inspect, or plan repair. Record the decision and the reason."),
         ("Human Decision", "Predictions are decision aids. A planner or engineer must confirm before a work order is scheduled. Every decision must show the sensor evidence and the rule or manual section behind it."),
     ]},
    {"doc_id": "SOP-002", "title": "Work Order Creation and Approval", "doc_type": "SOP", "applies_to": "ALL",
     "version": "2.2", "effective_date": "2026-01-01", "owner": "Maintenance Planning",
     "sections": [
         ("Work Order Types", "PREVENTIVE for scheduled routine work (every 30 days per asset). INSPECTION for an alert that needs checking. CORRECTIVE for repair after a failure or a planned repair for a confirmed fault."),
         ("Approval Limits", "Estimated cost below INR 50,000: shift supervisor. INR 50,000 to INR 2,00,000: maintenance manager. Above INR 2,00,000: plant head."),
         ("Spare Parts Check", "Before scheduling, check the part stock at the plant. If stock is zero, raise an emergency purchase (typically 24 to 96 hours) and tell the planner, because it extends downtime."),
         ("Planning Rule", "For criticality A and B assets, plan the repair inside a scheduled stop where possible. Avoid unplanned stops during peak production shifts."),
     ]},
    {"doc_id": "REF-001", "title": "OEE Definitions", "doc_type": "REFERENCE", "applies_to": "ALL",
     "version": "1.1", "effective_date": "2026-01-01", "owner": "Plant Operations",
     "sections": [
         ("Formulas", "Availability = run time / planned production time. Performance = (ideal cycle time x total units) / run time. Quality = good units / total units. OEE = Availability x Performance x Quality."),
         ("Downtime Categories", "Breakdown: unplanned stops from failures. Planned maintenance: scheduled preventive work. Small stops: short stops under 30 minutes. Only breakdown and small stops are treated as losses to reduce."),
         ("Targets", "Internal OEE target is 75 percent. A commonly quoted world-class level is 85 percent. Report OEE per asset, line and plant using the same definitions so teams get the same answer."),
     ]},
]


def build_docs() -> pd.DataFrame:
    rows = []
    for d in DOCS:
        for n, (sec, text) in enumerate(d["sections"], start=1):
            rows.append({
                "doc_id": d["doc_id"], "section_id": f"{d['doc_id']}-S{n}", "title": d["title"],
                "section_title": sec, "doc_type": d["doc_type"], "applies_to": d["applies_to"],
                "version": d["version"], "effective_date": d["effective_date"], "owner": d["owner"],
                "text": f"{d['title']} ({d['doc_id']}) - {sec}: {text}",
            })
    return pd.DataFrame(rows)