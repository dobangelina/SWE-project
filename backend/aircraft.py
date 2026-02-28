import random
import string
from dataclasses import dataclass
from typing import Optional
from .SimulationEngine import EmergencyType
# Defined here to avoid circular import from SimulationEngine


class Aircraft:
    """
    SimTime = int minutes.
    EmergencyType is CREATED by SimulationEngine and injected here.
    """

    def __init__(self, aircraft_id: str, flight_type: str, scheduledTime: int, fuelRemaining: int,*, emergency: Optional[EmergencyType] = None, altitude: int = 0, enteredHoldingAt: Optional[int] = None, joinedTakeoffQueueAt: Optional[int] = None):
        
        self.id = aircraft_id
        self.type = flight_type #a string that will either be INBOUND or OUTBOUND
        self.scheduledTime = int(scheduledTime)
        self.fuelRemaining = int(fuelRemaining)
        self.altitude = altitude
        self.emergency = emergency #this variable is of type EmergencyType
        
        self.enteredHoldingAt = enteredHoldingAt
        self.joinedTakeoffQueueAt = joinedTakeoffQueueAt

        # Cosmetic / UI fields
        icao_code = [
            "Boeing ", "Airbus ", "RYANAIR ", "Speedbird ", "Emirates ",
            "EASY ", "Oceanic ", "Virgin ", "Delta ", "United "
        ]
        self.callsign = f"{random.choice(icao_code)}{random.randint(100, 999)}"
        self.operator = random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)
        self.ground_speed = random.randint(300, 600)

        if self.type == "INBOUND":
            self.origin = self._rand_airport()
            self.destination = "SIMULATED_AIRPORT"
        else:
            self.origin = "SIMULATED_AIRPORT"
            self.destination = self._rand_airport()

    @staticmethod
    def _rand_airport() -> str:
        return "".join(random.choice(string.ascii_uppercase) for _ in range(3))

    def isEmergency(self) -> bool:
        e = self.emergency
        if e is None:
            return False
        return e.mechanical_failure or e.passenger_illness or e.fuel_emergency

    def consumeFuel(self, amount: int) -> None:
        self.fuelRemaining = max(0, self.fuelRemaining - int(amount))

    def priority(self, time: int) -> int:
        """
        Lower value = higher priority.
        Emergency aircraft must always come first.
        But change if you want spectrum
        Vadim
        """
        return 0 if self.isEmergency() else 1

    def getFuel(self) -> int:
        return self.fuelRemaining