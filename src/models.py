from dataclasses import dataclass, field
from typing import List, Optional, Dict


# Time is in integer minutes from some reference (e.g. start of day)
Time = int
PadId = str
FlightId = str


@dataclass
class WeatherData:
    wind_speed: float  # m/s
    visibility: float  # km
    precipitation: float  # mm/h
    temperature: float  # Celsius
    timestamp: Time  # when data was fetched


@dataclass
class Flight:
    id: FlightId
    earliest_start: Time
    latest_start: Time
    duration: int  # minutes on pad
    battery_need: float  # 0.0–1.0, higher = more urgent to land
    is_vip: bool = False
    is_medevac: bool = False
    rigidity: float = 0.5  # 0.0 = very flexible, 1.0 = very rigid
    max_delay: int = 15  # how many minutes we’re allowed to delay beyond latest_start
    preferred_pads: Optional[List[PadId]] = None


@dataclass
class Pad:
    id: PadId


@dataclass(order=True)
class Assignment:
    sort_index: Time = field(init=False, repr=False)
    flight_id: FlightId
    pad_id: PadId
    start: Time
    end: Time

    def __post_init__(self):
        self.sort_index = self.start


@dataclass
class ScheduleResult:
    assignments: List[Assignment]
    unscheduled_flights: List[Flight]
