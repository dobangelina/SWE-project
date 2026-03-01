from typing import List

#from .aircraft import aircraft
from .queues import HoldingQueue, TakeOffQueue
from .runway import Runway
from .SimulationEngine import SimTime
from .statistics import Statistics


# Other classes are yet to be made but the airport class needs to inherit from them
class Airport:
    def __init__(self, runways: list[Runway], holding: HoldingQueue, takeoff: TakeOffQueue, stats: Statistics):
        self.runways = runways
        self.holding = holding
        self.takeoff = takeoff
        self.stats = stats
        self.landing_in_progress = []
        self.takeoff_in_progress = []

    def _runways_for_landing(self):
        # LANDING-only first, then MIXED
        return sorted(self.runways, key=lambda r: 0 if r.mode == "LANDING" else (1 if r.mode == "MIXED" else 2))

    def _runways_for_takeoff(self):
        # TAKEOFF-only first, then MIXED
        return sorted(self.runways, key=lambda r: 0 if r.mode == "TAKEOFF" else (1 if r.mode == "MIXED" else 2))

    def handleInbound(self, aircraft, now: int):
        self.stats.record_holding_entry(aircraft, now)
        self.holding.enqueue(aircraft, now)

    def handleOutbound(self, aircraft, now: int):
        self.stats.record_takeoff_enqueue(aircraft, now)
        self.takeoff.enqueue(aircraft, now)

    def assignLanding(self, time: SimTime) -> None:
        """
        Assign as many inbound aircraft as possible to eligible available runways.
        """
        for runway in self.runways:
            if not (runway.isAvailable() and runway.canLand()):
                continue

            plane = self.holding.dequeue()
            if plane is None:
                return  # no more inbound aircraft

            duration = 1  # or param later
            plane.opType = "LANDING"
            plane.opStart = time
            plane.opEnd = time + duration
            self.landing_in_progress.append(plane)

            runway.assign(plane, "LANDING", time, duration)
            runway.status = "OCCUPIED"
            self.stats.record_runway_busy(runway, duration)

    def assignTakeOff(self, time: SimTime) -> None:
        """
        Assign as many outbound aircraft as possible to eligible available runways.
        """
        for runway in self.runways:
            if not (runway.isAvailable() and runway.canTakeOff()):
                continue

            plane = self.takeoff.dequeue()
            if plane is None:
                return  # no more outbound aircraft

            duration = 1  # or param later
            plane.opType = "LANDING"
            plane.opStart = time
            plane.opEnd = time + duration
            self.landing_in_progress.append(plane)

            runway.assign(plane, "LANDING", time, duration)
            runway.status = "OCCUPIED"
            self.stats.record_runway_busy(runway, duration)

    def getEligibleRunways(self, op: str) -> List[Runway]:
        if op == "LANDING":
            return [r for r in self.runways if r.mode in ("LANDING", "MIXED")]
        if op == "TAKEOFF":
            return [r for r in self.runways if r.mode in ("TAKEOFF", "MIXED")]
        return []
        
    #This method updates the runways so that the runways whose time has passed can be freed
    def updateRunways(self,time: SimTime) -> None:
        for runway in self.runways:
            if runway.occupiedUntil <= time and runway.currentAircraft is not None:
                finished = runway.currentAircraft
                op = runway.currentOperation

                # record at completion time (matches progress bar completion)
                if op == "LANDING":
                    self.stats.record_landing(finished, time)
                    if finished in self.landing_in_progress:
                        self.landing_in_progress.remove(finished)
                elif op == "TAKEOFF":
                    self.stats.record_takeoff(finished, time)
                    if finished in self.takeoff_in_progress:
                        self.takeoff_in_progress.remove(finished)

            # then clear runway state
            if runway.occupiedUntil <= time:
                runway.status = "AVAILABLE"
                runway.occupiedUntil = 0
                runway.currentAircraft = None
                runway.currentOperation = None

    def holding_display(self):
        # show in-progress (for progress bars), then waiting queue
        return list(self.landing_in_progress) + self.holding.to_list()

    def takeoff_display(self):
        return list(self.takeoff_in_progress) + self.takeoff.to_list()