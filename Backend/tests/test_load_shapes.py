from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "load"))
from load_test import SCENARIOS, arrival_offsets


def test_required_load_scenarios_have_deterministic_arrivals():
    assert {"steady", "burst", "sustained_overload", "rpm_halved", "daily_budget_exhausted"} <= set(SCENARIOS)
    assert len(arrival_offsets(SCENARIOS["steady"])) == 12
    assert set(arrival_offsets(SCENARIOS["burst"])) == {0.0}
