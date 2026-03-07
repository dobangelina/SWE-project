import random

class Runway:
    def __init__(self, runway_id, runway_mode) -> None:
        self.id = runway_id
        self.mode = runway_mode              # capability 
        self.status = "AVAILABLE"
        self.occupancy = "FREE"
        self.currentOperation = None         # "LANDING" or "TAKEOFF"
        self.occupiedUntil = 0
        self.currentAircraft = None
        self.length = random.randint(2000,4000)
        self.bearing = random.randint(1,36)

    def isAvailable(self):
        return self.occupancy == "FREE" and self.status == "AVAILABLE"

    def assign(self, aircraft, operationMode="LANDING", time: int = 0, duration: int = 1) -> None:
        self.currentAircraft = aircraft
        self.currentOperation = operationMode
        self.occupiedUntil = time + duration
        self.occupancy = "OCCUPIED"

    # Checks if a runway is available for a plane to land on it.
    def canLand(self) -> bool:
        # Fixed typo: self.Mode -> self.mode
        return self.currentAircraft == None and ((self.mode == "MIXED") or (self.mode == "LANDING"))

    # Checks if a runway is available for a plane to take off from it.
    def canTakeOff(self) -> bool:
        # Fixed typo: self.Mode -> self.mode
        return self.currentAircraft == None and ((self.mode == "MIXED") or (self.mode == "TAKEOFF"))

    #turns bearing into a string with the correct bearing format for UI output.
    def getBearingString(self) -> str: # Fixed return type: bool -> str
        if self.bearing <= 9:
            return str("0" + str(self.bearing))
        else:
            return str(self.bearing)
