import random
import string

class EmergencyType:
    def __init__(self,mechanical_failure: bool, passenger_illness: bool, fuel_amt: int):
        self.mechanical_failure = mechanical_failure
        self.passenger_illness = passenger_illness
        self.fuel_amt = fuel_amt
    
    def getmechfailure() -> bool:
        return
    
    def getpassengerillness() -> bool:
        return
    
    def getfuelamt() -> int:
        return

class Aircraft:
    def __init__(self, aircraft_id, flight_type, scheduledTime: SimTime, state, altitude, Emergency: EmergencyType, enteredHoldingAt: SimTime, joinedTakeoffQueueAt: SimTime):
        self.id = aircraft_id
        self.type = flight_type #a string that will either be INBOUND or OUTBOUND
        self.scheduledTime = scheduledTime
        self.actualTime = random.normal(self.scheduledTime, 5) #normal distribution around expected time, standard deviation of 5 mins
        self.state = state
        self.fuelRemaining = random.uniform(20,60) #fuel remaining is uniformly distributed between 20-60 minutes
        self.altitude = altitude
        self.Emergency = Emergency
        self.enteredHoldingAt = enteredHoldingAt
        self.joinedTakeoffQueueAt = joinedTakeoffQueueAt

        icao_code = ["Boeing ", "Airbus ", "RYANAIR ", "Speedbird ", "Emirates ", "EASY ", "Oceanic ", "Virgin ", "TOMJET ", "Delta ", "American ", "United "]
        self.callsign = icao_code[random.randint(0,len(icao_code)-1)] + str(random.randint(100,999))
        self.operator = random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)
        self.ground_speed = random.randint(300,600)
        if self.type == "INBOUND":
            self.origin = random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)
            self.destination = "SIMULATED AIRPORT" #placeholder for out airport name
        else:
            self.type = "SIMULATED AIRPORT" #placeholder for our airport name
            self.destination = random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)

    def isEmergency() -> bool:
        return
    
    def priority(time: SimTime) -> int: #What is this for? Is this when we want to assign the priority for the aircraft before pushing it into the queue?
        return
    
    def consumeFuel(data: SimTime) -> None:
        return

# TODO:
# Implement SimTime; very crucial for the system but idk what it is or how to implement it