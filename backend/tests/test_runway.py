import pytest

from backend.runway import Runway

class TempAircraft:
    def __init__(self, callsign: str):
        self.callsign = callsign
    
#Tests

def test_runway_created():
    
    r = Runway("R1", "MIXED")

    assert r.id == "R1"
    assert r.mode == "MIXED"
    assert r.status == "AVAILABLE"
    assert r.occupancy == "FREE"
    assert r.currentOperation is None
    assert r.currentAircraft is None
    assert r.occupiedUntil == 0

    #check if valid ranges
    assert 2000 <= r.length <= 4000
    assert 1 <= r.bearing <= 36


#isAvailable()
def test_isAvailable_unoccupied_available():
    #unoccupied = currentAircraft is None
    r = Runway("R1", "MIXED")

    assert r.isAvailable() is True

def test_isAvailable_occupied_available():
    #occupied = currentAircraft is not None
    r = Runway("R1", "MIXED")
    r.currentAircraft = TempAircraft("A1")

    assert r.isAvailable() is False

def test_isAvailable_unoccupied_unavailable():
    r = Runway("R1", "MIXED")
    r.status = "Runway Inspection"

    assert r.isAvailable() is False



#canLand()
def test_canLand_unoccupied_landing():
    r = Runway("R1", "LANDING")
    r.currentAircraft = None
    assert r.canLand() is True

def test_canLand_unoccupied_mixed():
    r = Runway("R1", "MIXED")
    r.currentAircraft = None
    assert r.canLand() is True

def test_canLand_unoccupied_takeoff():
    r = Runway("R1", "TAKEOFF")
    r.currentAircraft = None
    assert r.canLand() is False

def test_canLand_occupied_blocks():
    r = Runway("R1", "LANDING")
    r.currentAircraft = TempAircraft("A1")
    assert r.canLand() is False



#canTakeOff()
def test_canTakeOff_unoccupied_takeoff():
    r = Runway("R1", "TAKEOFF")
    r.currentAircraft = None
    assert r.canTakeOff() is True

def test_canTakeOff_unoccupied_mixed():
    r = Runway("R1", "MIXED")
    r.currentAircraft = None
    assert r.canTakeOff() is True

def test_canTakeOff_unoccupied_landing():
    r = Runway("R1", "LANDING")
    r.currentAircraft = None
    assert r.canTakeOff() is False

def test_canTakeOff_occupied_blocks():
    r = Runway("R1", "TAKEOFF")
    r.currentAircraft = TempAircraft("A1")
    assert r.canTakeOff() is False



#assign()
def test_assign_sets_aircraft_mode_and_occupied_until():
    a = TempAircraft("A1")
    rMode = "TAKEOFF"   # operationMode passed into assign()
    rTime = 10

    r = Runway("R1", "MIXED")
    r.assign(a, rMode, rTime)

    assert r.currentAircraft is a
    assert r.currentOperation == "TAKEOFF"
    assert r.mode == "MIXED"
    assert r.occupiedUntil == 11


def test_assign_sets_occupied_until_duration():
    a = TempAircraft("A1")
    r = Runway("R1", "MIXED")

    r.assign(a, "LANDING", time=5, duration=3)

    assert r.currentAircraft is a
    assert r.currentOperation == "LANDING"
    assert r.occupiedUntil == 8



#getBearingString()
def test_getBearingString_formats_single_digit_with_leading_zero():
    r = Runway("R1", "MIXED")
    r.bearing = 7
    assert r.getBearingString() == "07"

def test_getBearingString_formats_two_digits_without_leading_zero():
    r = Runway("R1", "MIXED")
    r.bearing = 27
    assert r.getBearingString() == "27"

