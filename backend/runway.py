import random

class Runway:
    def __init__(self, runway_id, runway_mode, runway_status):
        self.id = runway_id
        self.mode = runway_mode #either MIXED, LANDING, or TAKEOFF
        self.status = runway_status
        self.occupiedUntil = 0 #SimTime
        self.currentAircraft = None
        self.length = random.randint(2000,4000)
        self.bearing = random.randint(1,36)

    def isAvailable(self): #requires SimTime
        pass

    #checks if a runway is available for a plane to land on it.
    def canLand(self):
        return self.occupiedUntil == None and ((self.Mode == "MIXED") or (self.Mode == "LANDING"))

    #checks if a runway is available for a plane to take off from it.
    def canTakeOff(self):
        return self.occupiedUntil == None and ((self.Mode == "MIXED") or (self.Mode == "TAKEOFF"))

    #turns bearing into a string with the correct bearing format for UI output.
    def getBearingString(self):
        if self.bearing <= 9:
            return str("0" + str(self.bearing))
        else:
            return str(self.bearing)