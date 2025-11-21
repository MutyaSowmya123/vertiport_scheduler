from .models import Flight, Pad
from .scheduler import schedule_flights


def sample_flights():
    return [
        Flight(
            id="F1",
            earliest_start=0,
            latest_start=10,
            duration=5,
            battery_need=0.9,
            is_medevac=True,
            rigidity=0.9,
            max_delay=10,
            preferred_pads=["P1"],
        ),
        Flight(
            id="F2",
            earliest_start=3,
            latest_start=20,
            duration=7,
            battery_need=0.6,
            is_vip=True,
            rigidity=0.7,
            max_delay=15,
        ),
        Flight(
            id="F3",
            earliest_start=5,
            latest_start=15,
            duration=5,
            battery_need=0.3,
            rigidity=0.2,
            max_delay=20,
        ),
        Flight(
            id="F4",
            earliest_start=8,
            latest_start=12,
            duration=4,
            battery_need=0.8,
            rigidity=0.8,
            max_delay=5,
        ),
    ]


def sample_pads():
    return [
        Pad(id="P1"),
        Pad(id="P2"),
    ]


def main():
    flights = sample_flights()
    pads = sample_pads()

    result = schedule_flights(flights, pads, time_step=1)

    print("=== ASSIGNMENTS ===")
    for a in result.assignments:
        print(f"Flight {a.flight_id} -> Pad {a.pad_id} from {a.start} to {a.end}")

    if result.unscheduled_flights:
        print("\n=== UNSCHEDULED ===")
        for f in result.unscheduled_flights:
            print(f"Flight {f.id}")


if __name__ == "__main__":
    main()
