from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import random

SimTime = int

# Tracks simulation metrics and handles random timing jitter for aircraft spawns
@dataclass
class Statistics:
    # Configuration (set via configure_from_params)
    _arrival_stddev_min: int = 0
    _departure_stddev_min: int = 0
    _tick_size_min: int = 1
    _rng: random.Random = field(default_factory=random.Random, repr=False)

    # Queue Sizes
    max_holding_size: int = 0
    max_takeoff_size: int = 0
    max_takeoff_wait = 0
    holding_size_sum: int = 0
    takeoff_size_sum: int = 0
    snapshots: int = 0

    # Holding / Landing Metrics
    holding_time_sum: int = 0
    holding_count: int = 0

    # Takeoff Metrics
    takeoff_wait_sum: int = 0
    takeoff_count: int = 0

    # Arrival / Delay Metrics
    arrival_delay_sum: int = 0
    arrival_count: int = 0
    max_arrival_delay: SimTime = 0

    # Exceptions
    diversions: int = 0
    cancellations: int = 0

    # Runway Usage
    runway_busy_time: Dict[Any, int] = field(default_factory=dict)

    # Pulls statistical parameters and seeds the RNG from the main simulation config
    def configure_from_params(self, params: Any, seed: Optional[int] = None) -> None:
        self._arrival_stddev_min = int(getattr(params, "arrival_stddev_min", 0))
        self._departure_stddev_min = int(getattr(params, "departure_stddev_min", 0))
        self._tick_size_min = int(getattr(params, "tick_size_min", 1)) or 1

        if seed is not None:
            self._rng.seed(int(seed))

    # Helper to snap randomised times to the nearest discrete tick duration
    def _round_to_tick(self, minutes: float) -> int:
        t = int(self._tick_size_min) or 1
        return int(round(minutes / t) * t)

    # Applies normal-distributed jitter to an inbound flight's scheduled time
    def sample_inbound_spawn_time(self, scheduled_time_min: int) -> int:
        sigma = float(self._arrival_stddev_min)
        jitter = self._rng.gauss(0.0, sigma) if sigma > 0 else 0.0
        spawn = int(round(int(scheduled_time_min) + jitter))
        return max(0, spawn)

    # Applies normal-distributed jitter to an outbound flight's scheduled time
    def sample_outbound_spawn_time(self, scheduled_time_min: int) -> int:
        sigma = float(self._departure_stddev_min)
        jitter = self._rng.gauss(0.0, sigma) if sigma > 0 else 0.0
        spawn = int(round(int(scheduled_time_min) + jitter))
        return max(0, spawn)

    # Records queue sizes at the current tick for calculating maximums and averages
    def snapshot_queues(self, holding_size: int, takeoff_size: int, time: int) -> None:
        self.snapshots += 1
        self.max_holding_size = max(self.max_holding_size, int(holding_size))
        self.max_takeoff_size = max(self.max_takeoff_size, int(takeoff_size))
        self.holding_size_sum += int(holding_size)
        self.takeoff_size_sum += int(takeoff_size)

    # Logs the exact time an aircraft enters the holding pattern
    def record_holding_entry(self, aircraft: Any, time: SimTime) -> None:
        # Always set; no need to guard with hasattr
        setattr(aircraft, "enteredHoldingAt", int(time))

    # Computes and stores delay and holding durations when an aircraft successfully lands
    def record_landing(self, aircraft: Any, time: SimTime) -> None:
        t = int(time)

        entered = getattr(aircraft, "enteredHoldingAt", None)
        if entered is not None:
            ht = max(0, t - int(entered))
            self.holding_time_sum += ht
            self.holding_count += 1

        sched = getattr(aircraft, "scheduledTime", None)
        if sched is not None:
            delay = max(0, t - int(sched))
            self.arrival_delay_sum += delay
            self.arrival_count += 1
            self.max_arrival_delay = max(self.max_arrival_delay, delay)

    # Logs the exact time an aircraft enters the takeoff queue
    def record_takeoff_enqueue(self, aircraft: Any, time: SimTime) -> None:
        setattr(aircraft, "joinedTakeoffQueueAt", int(time))

    # Computes and stores the wait duration when an aircraft successfully takes off
    def record_takeoff(self, aircraft: Any, time: SimTime) -> None:
        joined = getattr(aircraft, "joinedTakeoffQueueAt", None)
        if joined is None:
            return

        wait = max(0, int(time) - int(joined))
        self.takeoff_wait_sum += wait
        self.takeoff_count += 1


        self.max_takeoff_wait = max(self.max_takeoff_wait, wait)

    # Increments the diversion counter 
    def record_diversion(self, aircraft: Any = None, time: SimTime = 0) -> None:
        self.diversions += 1

    # Increments the cancellation counter 
    def record_cancellation(self, aircraft: Any = None, time: SimTime = 0) -> None:
        self.cancellations += 1

    # Accumulates active usage time for a specific runway
    def record_runway_busy(self, runway: Any, duration_min: int) -> None:
        self.runway_busy_time[runway] = self.runway_busy_time.get(runway, 0) + int(duration_min)

    # Calculates averages and bundles all metrics into a dictionary for UI or reporting
    def report(self) -> Dict[str, float]:
        avg_holding_q = (self.holding_size_sum / self.snapshots) if self.snapshots else 0.0
        avg_takeoff_q = (self.takeoff_size_sum / self.snapshots) if self.snapshots else 0.0
        avg_hold_time = (self.holding_time_sum / self.holding_count) if self.holding_count else 0.0
        avg_takeoff_wait = (self.takeoff_wait_sum / self.takeoff_count) if self.takeoff_count else 0.0
        avg_arrival_delay = (self.arrival_delay_sum / self.arrival_count) if self.arrival_count else 0.0

        return {
            "maxHoldingQueue": float(self.max_holding_size),
            "avgHoldingQueue": float(avg_holding_q),
            "maxTakeoffQueue": float(self.max_takeoff_size),
            "avgTakeoffQueue": float(avg_takeoff_q),
            "avgHoldingTime": float(avg_hold_time),
            "avgTakeoffWait": float(avg_takeoff_wait),
            "maxTakeoffWait": float(self.max_takeoff_wait),
            "avgArrivalDelay": float(avg_arrival_delay),
            "maxArrivalDelay": float(self.max_arrival_delay),
            "diversions": float(self.diversions),
            "cancellations": float(self.cancellations),
        }