# Vertiport Scheduler

A Python-based vertiport scheduling system implementing Priority-Weighted Interval Scheduling + Dynamic Pad Assignment (PW-IS+DPA) with OR-Tools optimization and real-time weather integration for Urban Air Mobility (UAM) operations.

## Features

- **Priority-Weighted Scheduling**: Assigns flights based on urgency (VIP, medevac), battery needs, time rigidity, and deadlines
- **Dynamic Pad Assignment**: Optimizes pad usage with conflict resolution and delay handling
- **OR-Tools Integration**: Constraint-based optimization for maximum assignment rates in complex scenarios
- **Real-Time Weather Safety**: Fetches live weather data from Open-Meteo API to ensure safe landings
- **Comprehensive Testing**: Unit tests and challenging scenario benchmarks comparing greedy vs. optimal algorithms

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd vertiport_scheduler
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Scheduling

Run the scheduler with sample flights:

```python
from src.scheduler import schedule_flights
from src.models import Flight, Pad

# Define pads
pads = [Pad(id="Pad1"), Pad(id="Pad2")]

# Define flights
flights = [
    Flight(id="F1", earliest_start=0, latest_start=10, duration=5, battery_need=0.8, is_vip=True),
    Flight(id="F2", earliest_start=5, latest_start=15, duration=3, battery_need=0.5)
]

# Schedule flights
result = schedule_flights(flights, pads, use_ortools=True)
print(f"Scheduled: {len(result.assignments)}, Unscheduled: {len(result.unscheduled_flights)}")
```

### Command Line Interface

Use the CLI for quick scheduling:

```bash
python -m src.cli --flights 10 --pads 3 --use-ortools
```

### Weather Integration

The scheduler automatically fetches real-time weather data. To test manually:

```python
from src.weather import fetch_weather_data
weather = fetch_weather_data()
print(f"Wind: {weather.wind_speed} m/s, Visibility: {weather.visibility} km")
```

## Testing

### Run Unit Tests

```bash
pytest tests/
```

### Run Challenging Scenario Benchmark

```bash
python test_challenging_scenario.py
```

This tests 30 flights on 5 pads, comparing greedy vs. OR-Tools performance.
We see the or-tools performance is more optimal compared to the greedy as or-tools is better at fitting into tight schedules.

## Dependencies

- Python 3.8+
- ortools: For constraint optimization
- requests: For weather API calls
- pytest: For testing

See `requirements.txt` for full list.

## Algorithm Overview

### PW-IS+DPA (Greedy)
- Computes priorities based on urgency, battery, rigidity, and deadlines
- Assigns flights greedily to earliest available slots
- Handles delays up to max_delay for conflict resolution

### OR-Tools (Optimal)
- Models flights as variables with time constraints
- Uses CP-SAT solver to maximize total assigned priority
- Incorporates weather penalties for safety

## References

- NASA UTM & FAA Requirements for UAM
- Cambridge Aeronautical Journal: Quality-of-Service-Aware Scheduling
- ArXiv: Multi-Directional Vertiport Scheduling
