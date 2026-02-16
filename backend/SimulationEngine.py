from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional, Any

SimTime = int  # for compatibility across backend modules


@dataclass
class EmergencyType:
    mechanical_failure: bool = False
    passenger_illness: bool = False
    fuel_emergency: bool = False


@dataclass
class SimulationEngine:
    params: Any
    airport: Any
    stats: Any
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if hasattr(self.params, "validate"):
            self.params.validate()

        if hasattr(self.stats, "configure_from_params"):
            self.stats.configure_from_params(self.params, seed=self.seed)

        self.current_time: int = 0
        self.is_paused: bool = False

        self._inbound_acc: float = 0.0
        self._outbound_acc: float = 0.0

        self._pending_inbound: List[Tuple[int, Any]] = []
        self._pending_outbound: List[Tuple[int, Any]] = []

        self._rng = random.Random(self.seed)

        self._next_in_id: int = 1
        self._next_out_id: int = 1

    def tick(self) -> None:
        if self.is_paused:
            return

        dt: int = int(self.params.tick_size_min)
        self.current_time += dt
        now = self.current_time

        # update runway completion / availability
        if hasattr(self.airport, "updateRunways"):
            self.airport.updateRunways(now)

        # generate arrivals/departures (adds to pending with jitter)
        self._generate_arrivals(now, dt)
        self._generate_departures(now, dt)

        # flush pending due
        self._flush_pending(now)

        # apply constraints
        self.update_constraints(now, dt)

        # attempt assignments
        if hasattr(self.airport, "assignLanding"):
            self.airport.assignLanding(now)
        if hasattr(self.airport, "assignTakeOff"):
            self.airport.assignTakeOff(now)

        # stats snapshot
        if hasattr(self.stats, "snapshot_queues"):
            self.stats.snapshot_queues(
                holding_size=self.airport.holding.size(),
                takeoff_size=self.airport.takeoff.size(),
                time=now,
            )

    def run_for(self, duration_min: int) -> None:
        end_time = self.current_time + int(duration_min)
        while self.current_time < end_time:
            self.tick()

    @staticmethod
    def expected_per_tick(rate_per_hour: float, dt_min: int) -> float:
        return rate_per_hour * (dt_min / 60.0)

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

    def _apply_emergencies_this_tick(self, aircraft_created: List[Any]) -> None:
        n = int(self.params.emergencies_per_tick)
        if n <= 0 or not aircraft_created:
            return

        k = min(n, len(aircraft_created))
        for a in self._rng.sample(aircraft_created, k):
            setattr(a, "emergency", self._create_emergency())

    def _generate_arrivals(self, now: int, dt: int) -> None:
        self._inbound_acc += self.expected_per_tick(self.params.inbound_rate_per_hour, dt)
        created: List[Any] = []

        while self._inbound_acc >= 1.0:
            self._inbound_acc -= 1.0

            a = self.make_inbound_aircraft(now)
            created.append(a)

            spawn_time = self.stats.sample_inbound_spawn_time(now)
            self._pending_inbound.append((spawn_time, a))

        self._apply_emergencies_this_tick(created)

    def _generate_departures(self, now: int, dt: int) -> None:
        self._outbound_acc += self.expected_per_tick(self.params.outbound_rate_per_hour, dt)
        created: List[Any] = []

        while self._outbound_acc >= 1.0:
            self._outbound_acc -= 1.0

            a = self.make_outbound_aircraft(now)
            created.append(a)

            spawn_time = self.stats.sample_outbound_spawn_time(now)
            self._pending_outbound.append((spawn_time, a))

        self._apply_emergencies_this_tick(created)

    def _flush_pending(self, now: int) -> None:
        # Inbound
        if self._pending_inbound:
            due, future = [], []
            for t, a in self._pending_inbound:
                (due if t <= now else future).append((t, a))
            self._pending_inbound = future

            for t, a in due:
                self.airport.handleInbound(a, t)

        # Outbound
        if self._pending_outbound:
            due, future = [], []
            for t, a in self._pending_outbound:
                (due if t <= now else future).append((t, a))
            self._pending_outbound = future

            for t, a in due:
                self.airport.handleOutbound(a, t)

    def update_constraints(self, now: int, dt: int) -> None:

        pass

    def make_inbound_aircraft(self, now: int):
        from aircraft import Aircraft  # everything is in backend

        aircraft_id = f"I{self._next_in_id}"
        self._next_in_id += 1

        fuel = self._rng.randint(
            self.params.fuel_initial_min_min,
            self.params.fuel_initial_max_min,
        )

        return Aircraft(
            aircraft_id=aircraft_id,
            flight_type="INBOUND",
            scheduledTime=now,
            fuelRemaining=fuel,
            emergency=None,
        )

    def make_outbound_aircraft(self, now: int):
        from aircraft import Aircraft

        aircraft_id = f"O{self._next_out_id}"
        self._next_out_id += 1

        return Aircraft(
            aircraft_id=aircraft_id,
            flight_type="OUTBOUND",
            scheduledTime=now,
            fuelRemaining=0,
            emergency=None,
        )
