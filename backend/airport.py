from typing import List

from aircraft import Aircraft
from Queues import HoldingQueue, TakeOffQueue
from runway import Runway
from SimulationEngine import SimTime


# Other classes are yet to be made but the airport class needs to inherit from them
class Airport:
    def __init__(self, runways: list[Runway], holding: HoldingQueue, takeoff: TakeOffQueue):
        self.runways = runways
        self.holding = holding
        self.takeoff = takeoff

    def handleInbound(self, aircraft, now: int):
        self.holding.enqueue(aircraft, now)

    def handleOutbound(self, aircraft, now: int):
        self.takeoff.enqueue(aircraft, now)

    def assignLanding(time: SimTime, self) -> None:
        plane_holding : Aircraft = self.holding.dequeue()
        #found = False
        for runway in self.runways:
            if runway.isAvailable() and runway.canLand():
                runway.assign(plane_holding, "LANDING", time)    
                runway.status = "OCCUPIED"
                break
        # if not found:
        #     print("Not assigned for this tick")
    
    def assignTakeOff(time: SimTime, self) -> None:
        plane_takeoff : Aircraft = self.takeoff.dequeue()
        # found = False
        for runway in self.runways:
            if runway.isAvailable() and runway.canTakeoff():
                runway.assign(plane_takeoff, "TAKEOFF", time)
                runway.status = "OCCUPIED"
                break
        # if not found:
        #     print("Not assigned for this tick")
    
    def getEligibleRunways(self, mode: str) -> List[Runway]:
        eligible_list = []
        for runway in self.runways:
            if runway.mode == mode:
                eligible_list.append(runway)
        return eligible_list
        
    #This method updates the runways so that the runways whose time has passed can be freed
    def updateRunways(self,time: SimTime) -> None:
        for runway in self.runways:
            if runway.occupiedUntil < time:
                runway.status = "AVAILABLE"
                runway.occupiedUntil = 0
                runway.currentAircraft = None