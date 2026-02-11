from __future__ import annotations
#Our outer imports
import random
from dataclasses import dataclass
from typing import Optional

#Our inner imports
from SimulationParameters import SimulationParams
from airport import Airport
from aircraft import Aircraft
from statistics import Statistics

@dataclass
class SimulationEngine:
    def __init__(self, params, airport, stats):

        #innit of our objects
        self.params = params
        self.airport = airport
        self.stats = stats

        #basic attributes
        self.current_time_min = 0
        self.is_paused = False

        # rate-based accumulation
        self._inbound_acc = 0.0
        self._outbound_acc = 0.0

        self._pending_inbound = []
        self._pending_outbound = []

        self._rng = random.Random() # to discuss

    def tick(self):
        if self.is_paused:
            return

        now = self.current_time_min
        # increaser
        dt = self.params.tick_size_min


        # release runways that have finished
        self.airport.updateRunways(now)
        self._flush_pending(now)

        # generate new planes for this tick
        self.generate_arrivals(now, dt)
        self.generate_departures(now, dt)

        # update fuel
        self.update_constraints(now, dt)

        # schedule runway usage
        self.airport.assignLanding(now)
        self.airport.assignTakeoff(now)

        # record snapshot
        self.stats.snapshotQueues(
            holding_size=self.airport.holding.size(),
            takeoff_size=self.airport.takeoff.size(),
            time=now
        )

        # advance time
        self.current_time_min += dt


    # move the simulation forward
    def run_for(self, duration_min: int):
        end_time = self.current_time_min + duration_min
        while self.current_time_min < end_time:
            self.tick()

    #  generation
    def expected_per_tick(self, rate_per_hour: float, dt_min: int) -> float:
        return rate_per_hour * (dt_min / 60.0)

    def generate_arrivals(self, now: int, dt: int) -> None:
        self._inbound_acc += self.expected_per_tick(self.params.inbound_rate_per_hour, dt)

        while self._inbound_acc >= 1.0:
            self._inbound_acc -= 1.0

            a = self.make_inbound_aircraft(scheduled_time_min=now)

            # normal owned by Stats
            spawn_time = self.stats.sample_inbound_spawn_time(scheduled_time_min=now)
            self._pending_inbound.append((spawn_time, a))

    def generate_departures(self, now: int, dt: int) -> None:
        self._outbound_acc += self.expected_per_tick(self.params.outbound_rate_per_hour, dt)

        while self._outbound_acc >= 1.0:
            self._outbound_acc -= 1.0

            a = self.make_outbound_aircraft(scheduled_time_min=now)

            spawn_time = self.stats.sample_outbound_spawn_time(scheduled_time_min=now)
            self._pending_outbound.append((spawn_time, a))

    def _flush_pending(self, now: int) -> None:
        """
        Tick-based dispatch of aircraft into airport queues.
        Aircraft whose spawn_time <= now get injected.
        """
        if self._pending_inbound:
            due, future = [], []
            for t, a in self._pending_inbound:
                (due if t <= now else future).append((t, a))
            self._pending_inbound = future
            for _, a in due:
                self.airport.handleInbound(a, now)

        if self._pending_outbound:
            due, future = [], []
            for t, a in self._pending_outbound:
                (due if t <= now else future).append((t, a))
            self._pending_outbound = future
            for _, a in due:
                self.airport.handleOutbound(a, now)




    #  aircraft factory
    def make_inbound_aircraft(self, scheduled_time_min: int) -> Aircraft:

        a = Aircraft()  # replace

        # best-effort attribute assignment
        if hasattr(a, "type"):
            a.type = "INBOUND"
        if hasattr(a, "scheduled_time_min"):
            a.scheduled_time_min = scheduled_time_min
        if hasattr(a, "fuel_remaining_min"):
            a.fuel_remaining_min = self._rng.randint(self.params.fuel_initial_min_min, self.params.fuel_initial_max_min)

        return a

    def make_outbound_aircraft(self, scheduled_time_min: int) -> Aircraft:
        a = Aircraft()  # replace

        if hasattr(a, "type"):
            a.type = "OUTBOUND"
        if hasattr(a, "scheduled_time_min"):
            a.scheduled_time_min = scheduled_time_min

        return a