from .models import Flight


def compute_priority(flight: Flight) -> float:
    """
    Priority score combining:
    - VIP / medevac
    - battery need
    - rigidity (tight time window)
    - closeness of latest_start (earlier deadlines more urgent)
    """

    score = 0.0

    # 1) Hard priority categories
    if flight.is_medevac:
        score += 1000.0
    if flight.is_vip:
        score += 500.0

    # 2) Battery need (0–1) scaled
    score += 200.0 * flight.battery_need

    # 3) Time window tightness (rigidity: 0–1)
    # If rigidity is high, we add more
    score += 150.0 * flight.rigidity

    # 4) Deadline sooner = higher priority
    # We invert latest_start relative to a reference.
    # For now assume “smaller latest_start” is more urgent,
    # so subtract proportional to latest_start.
    score += max(0.0, 5000.0 / (1.0 + flight.latest_start))

    return score
