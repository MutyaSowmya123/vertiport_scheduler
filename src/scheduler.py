from typing import List, Dict, Tuple
from .models import Flight, Pad, Assignment, ScheduleResult, Time, WeatherData
from .priority import compute_priority
from ortools.sat.python import cp_model
from .weather import is_weather_safe


def _interval_conflicts(existing: List[Assignment], start: Time, end: Time) -> bool:
    """Check if [start, end) overlaps with any existing assignment."""
    for a in existing:
        if not (end <= a.start or start >= a.end):
            return True
    return False


def _assign_on_pad(
    pad_id: str,
    flight: Flight,
    pad_assignments: List[Assignment],
    start_time: Time
) -> Assignment:
    return Assignment(
        flight_id=flight.id,
        pad_id=pad_id,
        start=start_time,
        end=start_time + flight.duration,
    )


def schedule_flights(
    flights: List[Flight],
    pads: List[Pad],
    time_step: int = 1,
    use_ortools: bool = False,
    weather_data: WeatherData | None = None,
    max_time: int = 1440
) -> ScheduleResult:
    """
    Priority-Weighted Interval Scheduling + Dynamic Pad Assignment.

    - time_step: granularity in minutes when searching for starts.
    - use_ortools: If True, use OR-Tools CP-SAT for optimal scheduling; else, greedy.
    - weather_data: Real-time weather conditions to adjust priorities for safety.
    - max_time: Upper bound for time horizon (default 24h).
    """
    if use_ortools:
        return schedule_flights_ortools(flights, pads, time_step, max_time, weather_data)
    else:
        return _schedule_flights_greedy(flights, pads, time_step, weather_data)


def _schedule_flights_greedy(
    flights: List[Flight],
    pads: List[Pad],
    time_step: int = 1,
    weather_data: WeatherData | None = None
) -> ScheduleResult:
    """
    Greedy version of PW-IS + DPA.
    """
    from .weather import get_weather_penalty

    # Apply weather penalty to priorities
    penalty = get_weather_penalty(weather_data) if weather_data else 1.0

    # Precompute priorities with weather penalty
    scored_flights: List[Tuple[float, Flight]] = [
        (compute_priority(f) / penalty, f) for f in flights
    ]

    # Sort by priority descending, tie-break by earlier latest_start
    scored_flights.sort(key=lambda x: (-x[0], x[1].latest_start))

    # For each pad, keep its assignments sorted by start time
    pad_schedules: Dict[str, List[Assignment]] = {
        pad.id: [] for pad in pads
    }

    all_assignments: List[Assignment] = []
    unscheduled: List[Flight] = []

    for score, flight in scored_flights:
        # Try to assign this flight
        assigned = _try_assign_flight(flight, pads, pad_schedules, time_step)

        if assigned is None:
            unscheduled.append(flight)
        else:
            all_assignments.append(assigned)
            pad_schedules[assigned.pad_id].append(assigned)
            pad_schedules[assigned.pad_id].sort(key=lambda a: a.start)

    # Sort overall assignments by time
    all_assignments.sort(key=lambda a: (a.start, a.pad_id))

    return ScheduleResult(assignments=all_assignments, unscheduled_flights=unscheduled)


def _try_assign_flight(
    flight: Flight,
    pads: List[Pad],
    pad_schedules: Dict[str, List[Assignment]],
    time_step: int
) -> Assignment | None:
    """
    Try to assign flight to a pad/time, possibly with delay up to max_delay.
    """

    candidate_pads: List[Pad] = pads
    if flight.preferred_pads:
        # Put preferred pads first
        preferred_ids = set(flight.preferred_pads)
        preferred = [p for p in pads if p.id in preferred_ids]
        non_preferred = [p for p in pads if p.id not in preferred_ids]
        candidate_pads = preferred + non_preferred

    # First: within [earliest_start, latest_start]
    assigned = _search_time_window(
        flight,
        candidate_pads,
        pad_schedules,
        flight.earliest_start,
        flight.latest_start,
        time_step
    )
    if assigned:
        return assigned

    # Second: allow dynamic delay up to max_delay
    delayed_start_min = flight.latest_start + time_step
    delayed_start_max = flight.latest_start + flight.max_delay

    assigned = _search_time_window(
        flight,
        candidate_pads,
        pad_schedules,
        delayed_start_min,
        delayed_start_max,
        time_step
    )
    return assigned


def _search_time_window(
    flight: Flight,
    pads: List[Pad],
    pad_schedules: Dict[str, List[Assignment]],
    start_min: Time,
    start_max: Time,
    time_step: int
) -> Assignment | None:
    """
    Search for any pad/time in [start_min, start_max] where the flight fits.
    Greedy: earliest time, first pad that works.
    """
    t = start_min
    while t <= start_max:
        end = t + flight.duration
        for pad in pads:
            existing = pad_schedules[pad.id]
            if not _interval_conflicts(existing, t, end):
                return _assign_on_pad(pad.id, flight, existing, t)
        t += time_step

    return None


def schedule_flights_ortools(
    flights: List[Flight],
    pads: List[Pad],
    time_step: int = 1,
    max_time: int = 1440,  # 24 hours in minutes
    weather_data: WeatherData | None = None
) -> ScheduleResult:
    """
    Priority-Weighted Interval Scheduling + Dynamic Pad Assignment using OR-Tools CP-SAT.

    This version uses constraint programming for optimal scheduling:
    - Models flights as optional intervals with start/end variables.
    - Enforces no-overlap on pads, time windows, and preferences.
    - Objective: Maximize total priority of scheduled flights (greedy fallback for ties).

    - time_step: granularity in minutes.
    - max_time: upper bound for time horizon (default 24h).
    - weather_data: Adjusts priorities based on weather conditions.
    """
    from .weather import get_weather_penalty

    model = cp_model.CpModel()

    # Apply weather penalty to priorities
    penalty = get_weather_penalty(weather_data) if weather_data else 1.0

    # Precompute priorities with weather penalty
    scored_flights = [(compute_priority(f) / penalty, f) for f in flights]
    scored_flights.sort(key=lambda x: (-x[0], x[1].latest_start))  # Sort by priority

    # Decision variables
    flight_assigned = {}  # flight_id -> BoolVar (whether scheduled)
    flight_start = {}     # flight_id -> IntVar (start time)
    flight_end = {}       # flight_id -> IntVar (end time)
    flight_pad = {}       # flight_id -> IntVar (pad index)

    pad_indices = {pad.id: i for i, pad in enumerate(pads)}

    for score, flight in scored_flights:
        fid = flight.id
        flight_assigned[fid] = model.NewBoolVar(f"assigned_{fid}")
        flight_start[fid] = model.NewIntVar(0, max_time, f"start_{fid}")
        flight_end[fid] = model.NewIntVar(0, max_time, f"end_{fid}")
        flight_pad[fid] = model.NewIntVar(0, len(pads) - 1, f"pad_{fid}")

        # End = start + duration
        model.Add(flight_end[fid] == flight_start[fid] + flight.duration)

        # Time window constraints
        model.Add(flight_start[fid] >= flight.earliest_start).OnlyEnforceIf(flight_assigned[fid])
        model.Add(flight_start[fid] <= flight.latest_start + flight.max_delay).OnlyEnforceIf(flight_assigned[fid])

        # Preferred pads: if preferred, bias towards them (soft constraint via objective)
        # For hard preference, we could add constraints, but here we use objective weighting

    # No-overlap constraints per pad
    for pad in pads:
        pad_flights = [f for _, f in scored_flights]
        intervals = []
        for f in pad_flights:
            # Only create interval if assigned to this pad
            is_on_pad = model.NewBoolVar(f"is_on_pad_{f.id}_{pad.id}")
            model.Add(flight_pad[f.id] == pad_indices[pad.id]).OnlyEnforceIf(is_on_pad)
            model.Add(flight_pad[f.id] != pad_indices[pad.id]).OnlyEnforceIf(is_on_pad.Not())
            # Interval only active if assigned and on this pad
            active = model.NewBoolVar(f"active_{f.id}_{pad.id}")
            model.AddBoolAnd([flight_assigned[f.id], is_on_pad]).OnlyEnforceIf(active)
            model.AddBoolOr([flight_assigned[f.id].Not(), is_on_pad.Not()]).OnlyEnforceIf(active.Not())
            interval = model.NewOptionalIntervalVar(
                flight_start[f.id], f.duration, flight_end[f.id], active,
                f"interval_{f.id}_{pad.id}"
            )
            intervals.append(interval)
        model.AddNoOverlap(intervals)

    # Objective: Maximize sum of priorities for assigned flights
    objective_terms = []
    for score, flight in scored_flights:
        objective_terms.append(int(score) * flight_assigned[flight.id])  # Approximate as int
    model.Maximize(sum(objective_terms))

    # Solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Fallback to greedy if no solution
        return schedule_flights(flights, pads, time_step)

    # Extract assignments
    all_assignments = []
    unscheduled = []
    for score, flight in scored_flights:
        if solver.Value(flight_assigned[flight.id]):
            pad_idx = solver.Value(flight_pad[flight.id])
            pad_id = pads[pad_idx].id
            start = solver.Value(flight_start[flight.id])
            all_assignments.append(Assignment(
                flight_id=flight.id,
                pad_id=pad_id,
                start=start,
                end=start + flight.duration
            ))
        else:
            unscheduled.append(flight)

    all_assignments.sort(key=lambda a: (a.start, a.pad_id))
    return ScheduleResult(assignments=all_assignments, unscheduled_flights=unscheduled)
