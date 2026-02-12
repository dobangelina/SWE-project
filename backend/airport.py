from typing import List

from Queues import HoldingQueue, TakeOffQueue
from runway import Runway
from SimulationEngine import SimTime


# Other classes are yet to be made but the airport class needs to inherit from them
class Airport:
    def __init__(self, runways: list[Runway], holding: HoldingQueue, takeoff: TakeOffQueue):
        self.runways = runways
        self.holding = holding
        self.takeoff = takeoff

    def handleInbound(self, aircraft, now):
        self.holding.enqueue(aircraft, now)

    def handleOutbound(self, aircraft, now):
        self.takeoff.enqueue(aircraft, now)

    def updateRunways(now):
        pass

    def assignLanding(now):
        pass

    def assignTakeOff(now):
        pass

    def assignLanding(self) -> None:
        return
    
    def assigntakeoff(self) -> None:
        return
    
    def getEligibleRunways(self, mode: str) -> List[Runway]:
        return
    
    def updateRunways(time: SimTime) -> None:
        return