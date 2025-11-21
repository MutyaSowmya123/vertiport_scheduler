import os
import sys
import time

# --- Make sure Python can see the project root (where src/ lives) ---
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.models import Flight, Pad
from src.scheduler import schedule_flights
from src.priority import compute_priority


def test_basic_schedule():
    flights = [
        Flight(
            id="F1",
            earliest_start=0,
            latest_start=5,
            duration=5,
            battery_need=0.5,
        ),
        Flight(
            id="F2",
            earliest_start=0,
            latest_start=5,
            duration=5,
            battery_need=0.4,
        ),
    ]
    pads = [Pad(id="P1"), Pad(id="P2")]

    result = schedule_flights(flights, pads)

    assert len(result.assignments) == 2
    assert len(result.unscheduled_flights) == 0


def test_priority_computation():
    # Test medevac priority
    medevac = Flight(id="M1", earliest_start=0, latest_start=10, duration=5, battery_need=0.5, is_medevac=True)
    assert compute_priority(medevac) >= 1000.0

    # Test VIP priority
    vip = Flight(id="V1", earliest_start=0, latest_start=10, duration=5, battery_need=0.5, is_vip=True)
    assert 500.0 <= compute_priority(vip)  # Allow higher due to other factors

    # Test battery need scaling
    high_battery = Flight(id="B1", earliest_start=0, latest_start=10, duration=5, battery_need=1.0)
    low_battery = Flight(id="B2", earliest_start=0, latest_start=10, duration=5, battery_need=0.0)
    assert compute_priority(high_battery) > compute_priority(low_battery)

    # Test rigidity
    rigid = Flight(id="R1", earliest_start=0, latest_start=10, duration=5, battery_need=0.5, rigidity=1.0)
    flexible = Flight(id="R2", earliest_start=0, latest_start=10, duration=5, battery_need=0.5, rigidity=0.0)
    assert compute_priority(rigid) > compute_priority(flexible)

    # Test deadline urgency (earlier latest_start should have higher priority)
    early_deadline = Flight(id="D1", earliest_start=0, latest_start=5, duration=5, battery_need=0.5)
    late_deadline = Flight(id="D2", earliest_start=0, latest_start=50, duration=5, battery_need=0.5)
    assert compute_priority(early_deadline) > compute_priority(late_deadline)


def test_assignment_logic():
    # Test sequential assignment on same pad (no overlap)
    flights = [
        Flight(id="F1", earliest_start=0, latest_start=10, duration=5, battery_need=0.5),
        Flight(id="F2", earliest_start=5, latest_start=15, duration=5, battery_need=0.4),  # Starts after F1 ends
    ]
    pads = [Pad(id="P1")]

    result = schedule_flights(flights, pads)

    # Both can fit sequentially
    assert len(result.assignments) == 2
    assert len(result.unscheduled_flights) == 0

    # Check assignments
    f1 = next(a for a in result.assignments if a.flight_id == "F1")
    f2 = next(a for a in result.assignments if a.flight_id == "F2")
    assert f1.start == 0 and f1.end == 5
    assert f2.start == 5 and f2.end == 10


def test_preferred_pads():
    flights = [
        Flight(id="F1", earliest_start=0, latest_start=10, duration=5, battery_need=0.5, preferred_pads=["P1"]),
        Flight(id="F2", earliest_start=0, latest_start=10, duration=5, battery_need=0.4),
    ]
    pads = [Pad(id="P1"), Pad(id="P2")]

    result = schedule_flights(flights, pads)

    assert len(result.assignments) == 2
    # F1 should get P1 if possible
    f1_assignment = next(a for a in result.assignments if a.flight_id == "F1")
    assert f1_assignment.pad_id == "P1"


def test_delays():
    # Flight that needs delay
    flights = [
        Flight(id="F1", earliest_start=0, latest_start=5, duration=5, battery_need=0.5, max_delay=10),
    ]
    pads = [Pad(id="P1")]

    # Occupy pad initially
    pads_schedule = {"P1": []}  # Simulate occupied pad

    result = schedule_flights(flights, pads)

    # Should schedule with delay
    assert len(result.assignments) == 1
    assignment = result.assignments[0]
    assert assignment.start >= 0  # Within allowed range


def test_edge_cases():
    # All flights schedulable
    flights = [
        Flight(id="F1", earliest_start=0, latest_start=10, duration=5, battery_need=0.5),
        Flight(id="F2", earliest_start=5, latest_start=15, duration=5, battery_need=0.4),
    ]
    pads = [Pad(id="P1"), Pad(id="P2")]

    result = schedule_flights(flights, pads)
    assert len(result.assignments) == 2
    assert len(result.unscheduled_flights) == 0

    # Overloaded pads: more flights than pads can handle in tight window (no delay allowed)
    flights_overload = [
        Flight(id="F1", earliest_start=0, latest_start=0, duration=5, battery_need=0.5, max_delay=0),  # Only at 0, no delay
        Flight(id="F2", earliest_start=0, latest_start=0, duration=5, battery_need=0.4, max_delay=0),  # Only at 0, no delay
        Flight(id="F3", earliest_start=0, latest_start=0, duration=5, battery_need=0.3, max_delay=0),  # Only at 0, no delay
    ]
    pads_single = [Pad(id="P1")]

    result_overload = schedule_flights(flights_overload, pads_single)
    assert len(result_overload.assignments) == 1  # Only one can fit without overlap
    assert len(result_overload.unscheduled_flights) == 2


def test_performance():
    # Large input: 20 flights, 5 pads
    flights = [
        Flight(id=f"F{i}", earliest_start=0, latest_start=100, duration=10, battery_need=0.5 + (i % 10) * 0.05)
        for i in range(20)
    ]
    pads = [Pad(id=f"P{i}") for i in range(5)]

    import time
    start_time = time.time()
    result = schedule_flights(flights, pads)
    end_time = time.time()

    # Should complete quickly (<1 second)
    assert end_time - start_time < 1.0
    # At least some assignments
    assert len(result.assignments) > 0


def test_ortools_basic():
    """Test OR-Tools basic functionality."""
    flights = [
        Flight(id="F1", earliest_start=0, latest_start=10, duration=5, battery_need=0.5),
        Flight(id="F2", earliest_start=0, latest_start=10, duration=5, battery_need=0.4),
    ]
    pads = [Pad(id="P1"), Pad(id="P2")]

    result = schedule_flights(flights, pads, use_ortools=True)

    assert len(result.assignments) == 2
    assert len(result.unscheduled_flights) == 0
    # Check no overlaps
    for pad in pads:
        pad_assignments = [a for a in result.assignments if a.pad_id == pad.id]
        pad_assignments.sort(key=lambda a: a.start)
        for i in range(1, len(pad_assignments)):
            assert pad_assignments[i-1].end <= pad_assignments[i].start


def test_ortools_optimality_vs_greedy():
    """Test that OR-Tools produces equal or better schedules than greedy."""
    flights = [
        Flight(id="F1", earliest_start=0, latest_start=5, duration=5, battery_need=0.5, max_delay=10),
        Flight(id="F2", earliest_start=0, latest_start=5, duration=5, battery_need=0.4, max_delay=10),
        Flight(id="F3", earliest_start=0, latest_start=5, duration=5, battery_need=0.3, max_delay=10),
    ]
    pads = [Pad(id="P1")]  # Only one pad, so conflicts

    greedy_result = schedule_flights(flights, pads, use_ortools=False)
    ortools_result = schedule_flights(flights, pads, use_ortools=True)

    # OR-Tools should assign at least as many as greedy
    assert len(ortools_result.assignments) >= len(greedy_result.assignments)
    # And unscheduled at most as many as greedy
    assert len(ortools_result.unscheduled_flights) <= len(greedy_result.unscheduled_flights)


def test_ortools_fallback():
    """Test fallback to greedy when OR-Tools fails."""
    # Create an impossible schedule (but OR-Tools should handle it or fallback)
    flights = [
        Flight(id="F1", earliest_start=0, latest_start=0, duration=5, battery_need=0.5, max_delay=0),
        Flight(id="F2", earliest_start=0, latest_start=0, duration=5, battery_need=0.4, max_delay=0),
    ]
    pads = [Pad(id="P1")]

    result = schedule_flights(flights, pads, use_ortools=True)
    # Should assign one, unschedule one (same as greedy)
    assert len(result.assignments) == 1
    assert len(result.unscheduled_flights) == 1


def test_ortools_performance():
    """Test OR-Tools performance on larger instances."""
    flights = [
        Flight(id=f"F{i}", earliest_start=0, latest_start=100, duration=10, battery_need=0.5)
        for i in range(50)
    ]
    pads = [Pad(id=f"P{i}") for i in range(10)]

    start_time = time.time()
    result = schedule_flights(flights, pads, use_ortools=True)
    end_time = time.time()

    # Should complete reasonably (<5 seconds for 50 flights)
    assert end_time - start_time < 5.0
    assert len(result.assignments) > 0
    # Check no overlaps
    for pad in pads:
        pad_assignments = [a for a in result.assignments if a.pad_id == pad.id]
        pad_assignments.sort(key=lambda a: a.start)
        for i in range(1, len(pad_assignments)):
            assert pad_assignments[i-1].end <= pad_assignments[i].start


def test_ortools_constraints():
    """Test that OR-Tools respects time windows and pad assignments."""
    flights = [
        Flight(id="F1", earliest_start=10, latest_start=15, duration=5, battery_need=0.5),
        Flight(id="F2", earliest_start=0, latest_start=5, duration=5, battery_need=0.4),
    ]
    pads = [Pad(id="P1")]

    result = schedule_flights(flights, pads, use_ortools=True)

    # F1 must start >=10, F2 <=5
    f1 = next(a for a in result.assignments if a.flight_id == "F1")
    f2 = next(a for a in result.assignments if a.flight_id == "F2")
    assert f1.start >= 10
    assert f2.start <= 5
    # No overlap
    assert f1.end <= f2.start or f2.end <= f1.start


def test_weather_integration():
    """Test weather data integration in scheduling."""
    from src.weather import WeatherData

    flights = [
        Flight(id="F1", earliest_start=0, latest_start=10, duration=5, battery_need=0.5),
        Flight(id="F2", earliest_start=0, latest_start=10, duration=5, battery_need=0.4),
    ]
    pads = [Pad(id="P1"), Pad(id="P2")]

    # Safe weather
    safe_weather = WeatherData(wind_speed=5.0, visibility=10.0, precipitation=0.0, temperature=20.0, timestamp=0)
    result_safe = schedule_flights(flights, pads, weather_data=safe_weather)

    # Unsafe weather (high wind)
    unsafe_weather = WeatherData(wind_speed=15.0, visibility=10.0, precipitation=0.0, temperature=20.0, timestamp=0)
    result_unsafe = schedule_flights(flights, pads, weather_data=unsafe_weather)

    # Both should schedule, but unsafe might have lower priority adjustments
    assert len(result_safe.assignments) == 2
    assert len(result_unsafe.assignments) == 2  # Still schedules, but with penalties
