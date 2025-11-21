import time
from src.models import Flight, Pad
from src.scheduler import schedule_flights

# More challenging data: 30 flights with varying priorities, 5 pads, tight windows
flights = []
for i in range(30):
    battery = 0.3 + (i % 5) * 0.1  # Vary battery needs
    is_vip = i % 10 == 0  # Some VIPs
    is_medevac = i % 20 == 0  # Rare medevacs
    earliest = max(0, i * 2 - 10)  # Stagger starts
    latest = earliest + 20  # Tight windows
    flights.append(Flight(id=f'F{i}', earliest_start=earliest, latest_start=latest, duration=10, battery_need=battery, is_vip=is_vip, is_medevac=is_medevac, max_delay=5))
pads = [Pad(id=f'P{i}') for i in range(5)]

print('Challenging Scenario Comparison (30 flights, tight windows):')
print('=' * 60)

# Greedy
start = time.time()
greedy_result = schedule_flights(flights, pads, use_ortools=False)
greedy_time = time.time() - start
greedy_assigned = len(greedy_result.assignments)
greedy_unscheduled = len(greedy_result.unscheduled_flights)

# OR-Tools
start = time.time()
ortools_result = schedule_flights(flights, pads, use_ortools=True)
ortools_time = time.time() - start
ortools_assigned = len(ortools_result.assignments)
ortools_unscheduled = len(ortools_result.unscheduled_flights)

print(f'Greedy:   Time={greedy_time:.3f}s, Assigned={greedy_assigned}, Unscheduled={greedy_unscheduled}')
print(f'OR-Tools: Time={ortools_time:.3f}s, Assigned={ortools_assigned}, Unscheduled={ortools_unscheduled}')
print()
print('Key Metrics:')
print(f'Assignment Rate Greedy:   {greedy_assigned / len(flights) * 100:.1f}%')
print(f'Assignment Rate OR-Tools: {ortools_assigned / len(flights) * 100:.1f}%')
print()
if ortools_assigned > greedy_assigned:
    print('OR-Tools: Better at fitting flights into tight schedules')
elif ortools_assigned == greedy_assigned:
    print('Both similar; OR-Tools ensures global optimality')
else:
    print('Greedy better (rare, due to sequential assignment)')
