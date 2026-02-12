import random
import string

from SimulationEngine import SimTime


class EmergencyType:
    def __init__(self,mechanical_failure: bool, passenger_illness: bool): #removed fuel_amt 
        self.mechanical_failure = mechanical_failure
        self.passenger_illness = passenger_illness
    
    

class Aircraft:
    def __init__(self, aircraft_id, flight_type, scheduledTime, actualTime, fuelRemaining, altitude, emergency, enteredHoldingAt, joinedTakeoffQueueAt):
        self.id = aircraft_id
        self.type = flight_type #a string that will either be INBOUND or OUTBOUND
        self.scheduledTime = scheduledTime
        self.actualTime = actualTime #this is of type SimTime
        self.fuelRemaining = fuelRemaining
        self.altitude = altitude
        self.emergency = emergency #this variable is of type EmergencyType
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
            self.origin = "SIMULATED AIRPORT"
            self.destination = random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)

    def isEmergency(self) -> bool:
        return
    
    def priority(self,time: SimTime) -> int: #What is this for? Is this when we want to assign the priority for the aircraft before pushing it into the queue?
        return
    
    def consumeFuel(self,data: SimTime) -> None:
        return

