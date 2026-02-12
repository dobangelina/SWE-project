from backend.Queues import HoldingQueue, TakeOffQueue
from backend.runway import Runway

class SimTime:
    def __init__(self, time: SimTime) -> None:
        self.time = time


class RunwayMode:
    def __init__(self, mode):
        if mode not in ["L","T"]:
            raise ValueError("Mode must be L or T")
        self.mode = mode
    
    def setMode(self, newMode: str) -> None:
        self.mode = newMode
    
    def getMode(self) -> str:
        return self.mode

# Other classes are yet to be made but the airport class needs to inherit from them
class Airport:
    def __init__(self, runways: list[Runway], holding: HoldingQueue, takeoff: TakeOffQueue):
        self.runways = runways
        self.holding = holding
        self.takeoff = takeoff

    def assignLanding(self) -> None:
        return
    
    def assigntakeoff(self) -> None:
        return
    
    def getEligibleRunways(self,mode: RunwayMode) -> List[Runway]:
        return
    
    def updateRunways(time: SimTime) -> None:
        return