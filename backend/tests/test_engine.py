import pytest

from backend.SimulationEngine import SimulationEngine
from backend.queues import HoldingQueue, TakeOffQueue

class TempParams:
    def __init__(self):
        self.fuel_emergency_min = 15
        self.fuel_min_min = 10
        self.max_takeoff_wait_min = 30
        self.tick_size_min = 1

class TempStats:
    def __init__(self):
        self.diversions = 0
        self.cancellations = 0

    def record_diversion(self, aircraft, time):
        self.diversions += 1

    def record_cancellation(self, aircraft, time):
        self.cancellations += 1

class TempAirport:
    def __init__(self):
        self.holding = HoldingQueue()
        self.takeoff = TakeOffQueue()

class TempAircraft:
    def __init__(self, callsign: str, fuelRemaining: int = 100, joined_time: int = 0):
        self.callsign = callsign
        self.fuelRemaining = fuelRemaining
        self.emergency = None
        self.enteredHoldingAt = joined_time
        self.joinedTakeoffQueueAt = joined_time

    def isEmergency(self) -> bool:
        return self.emergency is not None

    def consumeFuel(self, dt: int) -> None:
        self.fuelRemaining -= dt


# Tests 

def test_update_constraints_diverts_low_fuel_aircraft():
    params = TempParams()
    airport = TempAirport()
    stats = TempStats()
    engine = SimulationEngine(params=params, airport=airport, stats=stats)

    # Aircraft starts with 12 fuel. Simulation ticks forward by 2 minutes.
    a1 = TempAircraft("A1", fuelRemaining=12, joined_time=0)
    airport.holding.enqueue(a1, time=0)

    # After this tick, fuel drops to 10. The absolute minimum is 10.
    # It should trigger a diversion and leave the queue.
    engine.update_constraints(now=2, dt=2)

    assert stats.diversions == 1
    assert airport.holding.size() == 0  # Plane is successfully removed from queue


def test_update_constraints_cancels_long_wait_takeoff():
    params = TempParams()
    airport = TempAirport()
    stats = TempStats()
    engine = SimulationEngine(params=params, airport=airport, stats=stats)

    # Aircraft joins takeoff queue at time 0
    a1 = TempAircraft("A1", fuelRemaining=100, joined_time=0)
    airport.takeoff.enqueue(a1, time=0)

    # At time 30, wait_time is 30. Max wait is 30. 
    # Condition is wait_time > max, so it should NOT cancel yet.
    engine.update_constraints(now=30, dt=1)
    
    assert stats.cancellations == 0
    assert airport.takeoff.size() == 1

    # At time 31, wait_time is 31. This exceeds the 30 min limit.
    # It should trigger a cancellation and leave the queue.
    engine.update_constraints(now=31, dt=1)
    
    assert stats.cancellations == 1
    assert airport.takeoff.size() == 0  # Plane successfully removed from queue