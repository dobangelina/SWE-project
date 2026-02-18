import random

class Runway:
    def __init__(self, runway_id, runway_mode, runway_status) -> None:
        self.id = runway_id
        self.mode = runway_mode #either string MIXED, LANDING, or TAKEOFF
        self.status = runway_status #AVAILABLE or OCCUPIED
        self.occupiedUntil = 0
        self.currentAircraft = None
        self.length = random.randint(2000,4000)
        self.bearing = random.randint(1,36)

    def isAvailable(self) -> bool: 
        return (self.currentAircraft == None) and (self.status == "AVAILABLE")
    
    def assign(self, aircraft, operationMode, time: int) -> None:
        self.currentAircraft = aircraft
        self.mode = operationMode
        self.occupiedUntil = time

    #checks if a runway is available for a plane to land on it.
    def canLand(self) -> bool:
        # Fixed typo: self.Mode -> self.mode
        return self.currentAircraft == None and ((self.mode == "MIXED") or (self.mode == "LANDING"))

    #checks if a runway is available for a plane to take off from it.
    def canTakeOff(self) -> bool:
        # Fixed typo: self.Mode -> self.mode
        return self.currentAircraft == None and ((self.mode == "MIXED") or (self.mode == "TAKEOFF"))

    #turns bearing into a string with the correct bearing format for UI output.
    def getBearingString(self) -> str: # Fixed return type: bool -> str
        if self.bearing <= 9:
            return str("0" + str(self.bearing))
        else:
            return str(self.bearing)