from typing import List

#from .aircraft import aircraft
from .queues import HoldingQueue, TakeOffQueue
from .runway import Runway
from .SimulationEngine import SimTime


# Other classes are yet to be made but the airport class needs to inherit from them
class Airport:
    def __init__(self, runways: list[Runway], holding: HoldingQueue, takeoff: TakeOffQueue,stats):
        self.runways = runways
        self.holding = holding
        self.takeoff = takeoff
        self.stats = stats

    def handleInbound(self, aircraft, now: int):
        self.stats.record_holding_entry(aircraft, now)
        self.holding.enqueue(aircraft, now)

    def handleOutbound(self, aircraft, now: int):
        self.stats.record_takeoff_enqueue(aircraft, now)
        self.takeoff.enqueue(aircraft, now)

    def assignLanding(self, time: SimTime) -> None:
        plane_holding = self.holding.dequeue()
        if plane_holding is None:
            return

        for runway in self.runways:
            if runway.isAvailable() and runway.canLand():
                duration = 1  # minutes (or make this a parameter later)
                runway.assign(plane_holding, "LANDING", time, duration)
                runway.status = "OCCUPIED"

                # statistics hooks
                self.stats.record_landing(plane_holding, time)
                self.stats.record_runway_busy(runway, duration)
                return

    def assignTakeOff(self, time: SimTime) -> None:
        plane_takeoff = self.takeoff.dequeue()
        if plane_takeoff is None:
            return

        for runway in self.runways:
            if runway.isAvailable() and runway.canTakeOff():
                duration = 1
                runway.assign(plane_takeoff, "TAKEOFF", time, duration)
                runway.status = "OCCUPIED"

                # statistics hooks
                self.stats.record_takeoff(plane_takeoff, time)
                self.stats.record_runway_busy(runway, duration)
                return

    
    def getEligibleRunways(self, mode: str) -> List[Runway]:
        eligible_list = []
        for runway in self.runways:
            if runway.mode == mode:
                eligible_list.append(runway)
        return eligible_list
        
    #This method updates the runways so that the runways whose time has passed can be freed
    def updateRunways(self,time: SimTime) -> None:
        for runway in self.runways:
            if runway.occupiedUntil <= time:
                runway.status = "AVAILABLE"
                runway.occupiedUntil = 0
                runway.currentAircraft = None
                runway.currentOperation = None