from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional, Any
from .aircraft import Aircraft, EmergencyType


SimTime = int  # for compatibility across backend modules

@dataclass
class SimulationEngine:
    """
        Core simulation engine controlling aircraft traffic at the airport.

        The engine is responsible for generating inbound and outbound aircraft,
        scheduling their arrivals and departures, applying operational constraints
        (fuel consumption, diversions, cancellations), and coordinating runway
        assignments through the Airport interface.

        The simulation advances in discrete time ticks measured in minutes.
        """
    params: Any
    airport: Any
    stats: Any
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        """
           Initialise the simulation engine after dataclass construction.

           This method validates parameters, configures statistics collection,
           initialises internal state variables, and pre-generates aircraft
           traffic for the initial scheduling window.
        """

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

        self._prime_scheduler(lookahead_window=15)


    def regenerate_schedule(self, lookahead_window: int = 15) -> None:
        """
           Rebuild the pending aircraft schedule.

           Clears all currently scheduled inbound and outbound aircraft and
           generates a new schedule using the current simulation parameters.
           A padding buffer is added to preserve the tail of the arrival
           distribution when sampling spawn times.
        """
        self._pending_inbound.clear()
        self._pending_outbound.clear()

        # Reset accumulators so we start the new flow fresh
        self._inbound_acc = 0.0
        self._outbound_acc = 0.0

        dt = int(self.params.tick_size_min)
        
        # Start from the next minute
        start_time = self.current_time + 1
        
        # Bugfix: extend the generation end time.
        # Since spawn times have an SD of ~5 mins, planes scheduled for 
        # 'lookahead + 15' might arrive within the 'lookahead' window.
        # Generating 20 extra minutes ensures the tail of the distribution is present.
        padding = 20
        end_time = self.current_time + lookahead_window + padding

        created_aircraft = []

        for t in range(start_time, end_time + 1):
            # Inbound planes
            self._inbound_acc += self.expected_per_tick(self.params.inbound_rate_per_hour, dt)
            while self._inbound_acc >= 1.0:
                self._inbound_acc -= 1.0
                a = self.make_inbound_aircraft(now=t)
                created_aircraft.append(a)
                # Sample the spawn time using the updated stats
                spawn_time = self.stats.sample_inbound_spawn_time(t)
                self._pending_inbound.append((spawn_time, a))

            # Outbound planes
            self._outbound_acc += self.expected_per_tick(self.params.outbound_rate_per_hour, dt)
            while self._outbound_acc >= 1.0:
                self._outbound_acc -= 1.0
                a = self.make_outbound_aircraft(now=t)
                created_aircraft.append(a)
                spawn_time = self.stats.sample_outbound_spawn_time(t)
                self._pending_outbound.append((spawn_time, a))
        
        # Apply emergencies to the new batch
        self._apply_emergencies_this_tick(created_aircraft)

    def tick(self) -> None:
        """
        Advance the simulation by one time step.

        Each tick performs the following operations:
            - Advances simulation time
            - Updates runway availability
            - Generates new inbound and outbound aircraft
            - Flushes scheduled aircraft into airport queues
            - Applies operational constraints
            - Assigns aircraft to runways
            - Updates statistics snapshots
        """
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
        """
           Run the simulation for a fixed duration.

           Parameters
           ----------
           duration_min : int
               Number of minutes the simulation should run.
        """
        end_time = self.current_time + int(duration_min)
        while self.current_time < end_time:
            self.tick()

    @staticmethod
    def expected_per_tick(rate_per_hour: float, dt_min: int) -> float:
        """
            Convert an hourly rate into expected events per simulation tick.

            Parameters
            ----------
            rate_per_hour : float
                Event rate expressed per hour.
            dt_min : int
                Tick size in minutes.

            Returns
            -------
            float
                Expected number of events per tick.
        """
        return rate_per_hour * (dt_min / 60.0)

    def update_constraints(self, now: int, dt: int) -> None:
        """
        Apply operational constraints to aircraft queues.

        This includes:
            - Fuel consumption for inbound aircraft
            - Fuel emergency detection
            - Aircraft diversion when fuel reaches critical levels
            - Takeoff cancellation if waiting time exceeds limits
        """


        temp_holding = []

        while self.airport.holding.size() > 0:
            item = self.airport.holding.dequeue_with_order()
            if item is not None:
                temp_holding.append(item)

        for _, order, aircraft in temp_holding:
            aircraft.consumeFuel(dt)

            if aircraft.fuelRemaining <= self.params.fuel_emergency_min:
                if aircraft.emergency is None:
                    aircraft.emergency = EmergencyType(fuel_emergency=True)
                else:
                    aircraft.emergency.fuel_emergency = True

            if aircraft.fuelRemaining <= self.params.fuel_min_min:
                self.stats.record_diversion(aircraft, now)
                continue

            self.airport.holding.enqueue_with_order(
                aircraft, aircraft.enteredHoldingAt, order
            )


        temp_takeoff = []

        while not self.airport.takeoff.isEmpty():
            temp_takeoff.append(self.airport.takeoff.dequeue())

        for aircraft in temp_takeoff:
            joined = aircraft.joinedTakeoffQueueAt
            wait_time = now - joined

            if wait_time > self.params.max_takeoff_wait_min:
                # CANCEL FLIGHT
                self.stats.record_cancellation(aircraft, now)
                continue

            # still valid → re-enqueue
            self.airport.takeoff.enqueue(aircraft, joined)

    # Factory method to create a new arriving aircraft
    def make_inbound_aircraft(self, now: int):
        """
           Create a new inbound aircraft.

           Parameters
           ----------
           now : int
               Scheduled arrival time.

           Returns
           -------
           Aircraft
               Newly created inbound aircraft instance.
        """
        # Generate a unique ID for the inbound flight and increment the counter
        aircraft_id = f"I{self._next_in_id}"
        self._next_in_id += 1

        # Assigns  random initial fuel amount within the configured limits
        fuel = self._rng.randint(
            self.params.fuel_initial_min_min,
            self.params.fuel_initial_max_min,
        )

        # Creates and returns the Aircraft object
        return Aircraft(
            aircraft_id=aircraft_id,
            flight_type="INBOUND",
            scheduledTime=now,
            fuelRemaining=fuel,
            emergency=None,
        )

    # Factory method to create a new departing aircraft
    def make_outbound_aircraft(self, now: int):
        """
            Create a new outbound aircraft.

            Parameters
            ----------
            now : int
                Scheduled departure time.

            Returns
            -------
            Aircraft
                Newly created outbound aircraft instance.
        """
        # Generates a unique ID for the outbound flight and increment the counter
        aircraft_id = f"O{self._next_out_id}"
        self._next_out_id += 1

        # Creates and returns the Aircraft object (fuel is 0 as it is not tracked for departures)
        return Aircraft(
            aircraft_id=aircraft_id,
            flight_type="OUTBOUND",
            scheduledTime=now,
            fuelRemaining=0,
            emergency=None,
        )

    """
    HELPER FUNCTIONS
    """

    def _prime_scheduler(self, lookahead_window: int) -> None:
        """
        Pre-generate aircraft traffic for the initial simulation window.

        Aircraft arrivals and departures are scheduled for the first
        ``lookahead_window`` minutes so the simulation begins with traffic
        already in the system.

        Parameters
        ----------
        lookahead_window : int
            Number of minutes ahead of the simulation start to generate traffic.
        """
        # Iterate 1 minute at a time to fill the backlog
        dt = 1
        created_aircraft = []

        for t in range(lookahead_window):
            # Handles the Inbound Backlog
            self._inbound_acc += self.expected_per_tick(self.params.inbound_rate_per_hour, dt)
            while self._inbound_acc >= 1.0:
                self._inbound_acc -= 1.0
                # Schedule for time 't' (e.g., 0, 1, 2... 14)
                a = self.make_inbound_aircraft(now=t)
                created_aircraft.append(a)

                # Jitter might make spawn_time negative (e.g. -2),
                # which ensures they appear immediately at tick 0.
                spawn_time = self.stats.sample_inbound_spawn_time(t)
                self._pending_inbound.append((spawn_time, a))

            # Handles the Outbound Backlog
            self._outbound_acc += self.expected_per_tick(self.params.outbound_rate_per_hour, dt)
            while self._outbound_acc >= 1.0:
                self._outbound_acc -= 1.0
                a = self.make_outbound_aircraft(now=t)
                created_aircraft.append(a)

                spawn_time = self.stats.sample_outbound_spawn_time(t)
                self._pending_outbound.append((spawn_time, a))

        # Apply emergency rolls to these pre-generated planes
        self._apply_emergencies_this_tick(created_aircraft)

    def _create_emergency(self) -> Optional[EmergencyType]:
        """
           Randomly generate an emergency event for an aircraft.

           The probability of each emergency type is determined by simulation
           parameters. Only mechanical failures and passenger illnesses are
           generated here; fuel emergencies are handled dynamically during
           constraint updates.

           Returns
           -------
           Optional[EmergencyType]
               Generated emergency or None if no emergency occurs.
        """
        r = self._rng.random()
        p_mech = self.params.p_mechanical_failure
        p_ill = self.params.p_passenger_illness

        # If r < 0.05, mechanical. If 0.05 < r < 0.10, illness. 
        # If r > 0.10, no emergency.
        if r < p_mech:
            return EmergencyType(mechanical_failure=True)
        elif r < p_mech + p_ill:
            return EmergencyType(passenger_illness=True)
        
        # Fuel emergencies are handled dynamically in update_constraints, 
        # so we should have returned None here if the roll didn't hit a spawn emergency.
        return None

    def _apply_emergencies_this_tick(self, aircraft_created: List[Any]) -> None:
        """
            Apply randomly generated emergencies to newly created aircraft.

            Emergencies are only assigned to inbound aircraft since they are
            the ones entering the holding queue.

            Parameters
            ----------
            aircraft_created : List[Any]
                Aircraft objects generated during the current tick.
        """
        if not aircraft_created:
            return

        # Emergencies only apply to inbound aircraft (holding queue), not outbound.
        for a in aircraft_created:
            if getattr(a, "type", None) != "INBOUND":
                continue

            emerg = self._create_emergency()
            if emerg is not None:
                setattr(a, "emergency", emerg)

    def _generate_arrivals(self, now: int, dt: int) -> None:
        """
            Generate inbound aircraft arrivals.

            Aircraft are scheduled with jitter around their target arrival time
            and stored in the pending inbound list until their spawn time occurs.

            Parameters
            ----------
            now : int
                Current simulation time.
            dt : int
                Tick duration in minutes.
        """
        # We look ahead by 15 minutes to allow for "early" jittered arrivals
        lookahead_window = now + 15
        self._inbound_acc += self.expected_per_tick(self.params.inbound_rate_per_hour, dt)
        created: List[Any] = []

        while self._inbound_acc >= 1.0:
            self._inbound_acc -= 1.0
            
            # The 'target_time' is the uniform schedule time
            target_time = lookahead_window 
            a = self.make_inbound_aircraft(target_time)
            created.append(a)

            # Jitter the actual spawn time around the target time
            spawn_time = self.stats.sample_inbound_spawn_time(target_time)
            self._pending_inbound.append((spawn_time, a))

        self._apply_emergencies_this_tick(created)

    def _generate_departures(self, now: int, dt: int) -> None:
        """
        Generate outbound aircraft departures.

        Aircraft are scheduled with jitter around their target departure
        time and added to the pending outbound list.

        Parameters
        ----------
        now : int
            Current simulation time.
        dt : int
            Tick duration in minutes.
        """
        lookahead_window = now + 15
        self._outbound_acc += self.expected_per_tick(self.params.outbound_rate_per_hour, dt)
        created: List[Any] = []

        while self._outbound_acc >= 1.0:
            self._outbound_acc -= 1.0
            
            target_time = lookahead_window
            a = self.make_outbound_aircraft(target_time)
            created.append(a)

            spawn_time = self.stats.sample_outbound_spawn_time(target_time)
            self._pending_outbound.append((spawn_time, a))

        self._apply_emergencies_this_tick(created)

    def _flush_pending(self, now: int) -> None:
        """
           Move aircraft whose spawn time has been reached into airport queues.

           Pending inbound aircraft are transferred to the holding queue,
           while outbound aircraft are transferred to the takeoff queue.
        """
        # Sort both lists by the spawn_time (the first element of the tuple)
        self._pending_inbound.sort(key=lambda x: x[0])
        self._pending_outbound.sort(key=lambda x: x[0])

        # Inbound: Flush all aircraft whose spawn_time has passed or is now
        due_inbound = [a for t, a in self._pending_inbound if t <= now]
        self._pending_inbound = [(t, a) for t, a in self._pending_inbound if t > now]
        for a in due_inbound:
            # We use the original sampled spawn_time for the handleInbound call
            # to ensure the airport knows exactly when it "hit" the airspace.
            self.airport.handleInbound(a, now)

        # Outbound: Flush all aircraft whose spawn_time has passed or is now
        due_outbound = [a for t, a in self._pending_outbound if t <= now]
        self._pending_outbound = [(t, a) for t, a in self._pending_outbound if t > now]
        for a in due_outbound:
            self.airport.handleOutbound(a, now)

    """
    ACCESSORS
    """
    def get_time(self) -> int:
        """Return the current simulation time in minutes."""
        return self.current_time  # SimTime in minutes

    def get_report(self) -> dict:
        """Return the statistics report for the simulation."""
        return self.stats.report()

    def get_holding_queue(self):
        """Return the holding queue for the simulation."""
        return self.airport.holding.to_list()

    def get_takeoff_queue(self):
        """Return the take-off queue for the simulation."""
        return self.airport.takeoff.to_list()

    def get_runways(self):
        """Return the runway for the simulation."""
        return self.airport.runways
