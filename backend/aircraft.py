import random
import string



class EmergencyType:
    def __init__(self,mechanical_failure: bool, passenger_illness: bool, fuel_amt: int):
        self.mechanical_failure = mechanical_failure
        self.passenger_illness = passenger_illness
        self.fuel_amt = fuel_amt
    
    def getmechfailure(self) -> bool:
        return
    
    def getpassengerillness(self) -> bool:
        return
    
    def getfuelamt(self) -> int:
        return

# aircraft.py
import random
import string
from typing import Optional


class Aircraft:
    """
    SimTime = int minutes.
    EmergencyType is CREATED by SimulationEngine and injected here.
    """

    def __init__(self,aircraft_id: str,flight_type: str,scheduledTime: int, fuelRemaining: int,
                 *,emergency=None,altitude: int = 0,enteredHoldingAt: Optional[int] = None,
                 joinedTakeoffQueueAt: Optional[int] = None):
        self.id = aircraft_id
        self.type = flight_type
        self.scheduledTime = int(scheduledTime)
        self.fuelRemaining = int(fuelRemaining)
        self.altitude = altitude

        # Emergency object comes from SimulationEngine
        self.Emergency = emergency

        self.enteredHoldingAt = enteredHoldingAt
        self.joinedTakeoffQueueAt = joinedTakeoffQueueAt

        # Cosmetic / UI fields
        icao_code = [
            "Boeing", "Airbus", "RYANAIR", "Speedbird", "Emirates",
            "EASY", "Oceanic", "Virgin", "Delta", "United"
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

    # REQUIRED by HoldingQueue
    def isEmergency(self) -> bool:
        e = self.Emergency
        if e is None:
            return False
        return bool(
            getattr(e, "mechanical_failure", False) or
            getattr(e, "passenger_illness", False) or
            getattr(e, "fuel_emergency", False)
        )