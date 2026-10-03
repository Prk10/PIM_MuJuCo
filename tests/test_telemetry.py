import pytest
from src.telemetry.telemetry_parser import TelemetryParser
import json
import os

def test_telemetry_metrics():
    # Setup dummy coeffs
    coeffs = {
        "RD": 10.0,
        "WR": 10.0,
        "ACT": 5.0,
        "PRE": 5.0,
        "PIM_MAC": 2.0
    }
    with open("test_coeffs.json", "w") as f:
        json.dump(coeffs, f)

    parser = TelemetryParser("test_coeffs.json")

    gem5_stats = {"sim_ticks": 1000000} # 1us
    ramulator_stats = {
        "RD": 10,
        "WR": 10,
        "ACT": 10,
        "PRE": 10,
        "PIM_MAC": 1000
    }
    mujoco_stats = {"physical_energy_joules": 0.1}

    metrics = parser.calculate_metrics(gem5_stats, ramulator_stats, mujoco_stats)

    # Assert total cycles
    assert metrics["total_cycles"] == 1000000

    # Assert latency
    assert metrics["latency_s"] == 1e-6

    # Assert energy
    # pim_pj = 10*10 + 10*10 + 10*5 + 10*5 + 1000*2 = 100 + 100 + 50 + 50 + 2000 = 2300 pJ
    # pim_j = 2300e-12 J
    # total_sys_j = 0.01 + 2300e-12
    assert abs(metrics["total_system_energy_j"] - (0.01 + 2300e-12)) < 1e-15

    # Assert tops
    # macs = 1000
    # ops = 2000
    # ops / time = 2000 / 1e-6 = 2e9 ops/s
    # tops = 2e9 / 1e12 = 0.002
    assert metrics["tops"] == 0.002

    os.remove("test_coeffs.json")
