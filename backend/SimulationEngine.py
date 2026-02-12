from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

from SimulationParameters import SimulationParams
from airport import Airport
from aircraft import Aircraft
from statistics import Statistics


# SimTime

@dataclass(frozen=True, order=True)
class SimTime:
    minutes: int = 0

    def __int__(self) -> int:
        return self.minutes

    def advance(self, delta: int) -> "SimTime":
        return SimTime(self.minutes + int(delta))



# Emergency type (defined INSIDE engine)
@dataclass
class EmergencyType:
    mechanical_failure: bool = False
    passenger_illness: bool = False
    fuel_emergency: bool = False



# Simulation Engine
@dataclass
class SimulationEngine:
    params: SimulationParams
    airport: Airport
    stats: Statistics
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        # Validate parameters
        self.params.validate()

        # Configure statistics (jitter RNG etc.)
        if hasattr(self.stats, "configure_from_params"):
            self.stats.configure_from_params(self.params, seed=self.seed)

        # Simulation time
        self.current_time: SimTime = SimTime(0)
        self.is_paused: bool = False

        # Rate accumulators
        self._inbound_acc: float = 0.0
        self._outbound_acc: float = 0.0

        # Pending spawns (spawn_time, aircraft)
        self._pending_inbound: List[Tuple[SimTime, Aircraft]] = []
        self._pending_outbound: List[Tuple[SimTime, Aircraft]] = []

        # RNG (non-normal randomness only)
        self._rng = random.Random(self.seed)

        # ID counters
        self._next_in_id: int = 1
        self._next_out_id: int = 1

    # Tick loop
    def tick(self) -> None:
        if self.is_paused:
            return

        now: SimTime = self.current_time
        dt: int = int(self.params.tick_size_min)

        # Release runways
        self.airport.updateRunways(int(now))

        # Inject pending aircraft
        self._flush_pending(now)

        # Generate new demand
        self._generate_arrivals(now, dt)
        self._generate_departures(now, dt)

        # Constraints (left empty intentionally)
        self.update_constraints(int(now), dt)

        # Assign runways
        self.airport.assignLanding(int(now))
        self.airport.assignTakeoff(int(now))

        # Snapshot statistics
        self.stats.snapshotQueues(
            holding_size=self.airport.holding.size(),
            takeoff_size=self.airport.takeoff.size(),
            time=int(now),
        )

        # Advance time
        self.current_time = self.current_time.advance(dt)

    def run_for(self, duration_min: int) -> None:
        end_time = self.current_time.minutes + int(duration_min)
        while self.current_time.minutes < end_time:
            self.tick()


    # Demand helpers
    @staticmethod
    def expected_per_tick(rate_per_hour: float, dt_min: int) -> float:
        return rate_per_hour * (dt_min / 60.0)

    # Emergency generation
    def _create_emergency(self) -> EmergencyType:
        r = self._rng.random()
        p_mech = self.params.p_mechanical_failure
        p_ill = self.params.p_passenger_illness

        if r < p_mech:
            return EmergencyType(mechanical_failure=True)
        elif r < p_mech + p_ill:
            return EmergencyType(passenger_illness=True)
        else:
            return EmergencyType(fuel_emergency=True)

    def _apply_emergencies_this_tick(self, aircraft_created: List[Aircraft]) -> None:
        n = int(self.params.emergencies_per_tick)
        if n <= 0 or not aircraft_created:
            return

        k = min(n, len(aircraft_created))
        chosen = self._rng.sample(aircraft_created, k)

        for a in chosen:
            a.Emergency = self._create_emergency()


    # Arrival / departure generation
    def _generate_arrivals(self, now: SimTime, dt: int) -> None:
        self._inbound_acc += self.expected_per_tick(self.params.inbound_rate_per_hour, dt)
        created: List[Aircraft] = []

        while self._inbound_acc >= 1.0:
            self._inbound_acc -= 1.0

            a = self.make_inbound_aircraft(now)
            created.append(a)

            spawn_raw = self.stats.sample_inbound_spawn_time(int(now))
            self._pending_inbound.append((SimTime(int(spawn_raw)), a))

        self._apply_emergencies_this_tick(created)

    def _generate_departures(self, now: SimTime, dt: int) -> None:
        self._outbound_acc += self.expected_per_tick(self.params.outbound_rate_per_hour, dt)
        created: List[Aircraft] = []

        while self._outbound_acc >= 1.0:
            self._outbound_acc -= 1.0

            a = self.make_outbound_aircraft(now)
            created.append(a)

            spawn_raw = self.stats.sample_outbound_spawn_time(int(now))
            self._pending_outbound.append((SimTime(int(spawn_raw)), a))

        # apply emergencies to outbound as well
        self._apply_emergencies_this_tick(created)

    # Pending flush
    def _flush_pending(self, now: SimTime) -> None:
        if self._pending_inbound:
            due, future = [], []
            for t, a in self._pending_inbound:
                (due if t <= now else future).append((t, a))
            self._pending_inbound = future
            for _, a in due:
                self.airport.handleInbound(a, int(now))

        if self._pending_outbound:
            due, future = [], []
            for t, a in self._pending_outbound:
                (due if t <= now else future).append((t, a))
            self._pending_outbound = future
            for _, a in due:
                self.airport.handleOutbound(a, int(now))


    # Constraints (intentionally empty for now)

    def update_constraints(self, now: int, dt: int) -> None:
        """
               Placeholder:

               Typical responsibilities later:
                 - burn fuel for holding aircraft; divert if below threshold
                 - cancel takeoffs waiting too long
               """
        return


    # Aircraft factories
    def make_inbound_aircraft(self, now: SimTime) -> Aircraft:
        aircraft_id = f"I{self._next_in_id}"
        self._next_in_id += 1

        fuel = self._rng.randint(
            self.params.fuel_initial_min_min,
            self.params.fuel_initial_max_min,
        )

        return Aircraft(
            aircraft_id,
            "INBOUND",
            int(now),
            int(fuel),
            emergency=None,
        )

    def make_outbound_aircraft(self, now: SimTime) -> Aircraft:
        aircraft_id = f"O{self._next_out_id}"
        self._next_out_id += 1

        return Aircraft(
            aircraft_id,
            "OUTBOUND",
            int(now),
            0,              #  fixed outbound fuel
            emergency=None,
        )

