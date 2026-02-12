# simulation_params.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationParams:

    # Define data types:
    num_runways: int
    inbound_rate_per_hour: float
    outbound_rate_per_hour: float

    # Stochastic assumptions (minutes):
    arrival_stddev_min: int = 5
    departure_stddev_min: int = 5

    # Constraints (minutes)
    max_takeoff_wait_min: int = 30
    fuel_min_min: int = 10
    fuel_initial_min_min: int = 20
    fuel_initial_max_min: int = 60
    # Emergency events per tick (counts, not probabilities)
    emergencies_per_tick: int = 0

    # distribution of emergency types (weights)
    p_mechanical_failure: float = 0.4
    p_passenger_illness: float = 0.4
    p_fuel_emergency: float = 0.2

    # Engine timing
    tick_size_min: int = 1                  # 1-minute discrete tick

    def validate(self) -> None:
        if not (1 <= self.num_runways <= 10):
            raise ValueError("num_runways must be in [1, 10].")

        if self.inbound_rate_per_hour < 0:
            raise ValueError("inbound_rate_per_hour must be >= 0.")
        if self.outbound_rate_per_hour < 0:
            raise ValueError("outbound_rate_per_hour must be >= 0.")

        if self.tick_size_min <= 0:
            raise ValueError("tick_size_min must be > 0.")

        if self.arrival_stddev_min <= 0 or self.departure_stddev_min <= 0:
            raise ValueError("stddev minutes must be > 0.")

        if self.max_takeoff_wait_min <= 0:
            raise ValueError("max_takeoff_wait_min must be > 0.")

        if self.fuel_initial_min_min < 0 or self.fuel_initial_max_min < 0:
            raise ValueError("fuel initial bounds must be non-negative.")
        if self.fuel_initial_min_min > self.fuel_initial_max_min:
            raise ValueError("fuel_initial_min_min must be <= fuel_initial_max_min.")
        if self.fuel_min_min >= self.fuel_initial_min_min:
            raise ValueError("fuel_min_min must be < fuel_initial_min_min.")
        if self.emergencies_per_tick < 0:
            raise ValueError("emergencies_per_tick must be >= 0.")
        s = self.p_mechanical_failure + self.p_passenger_illness + self.p_fuel_emergency
        if abs(s - 1.0) > 1e-9:
            raise ValueError("Emergency probabilities must sum to 1.0.")

