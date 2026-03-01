import pytest

from backend.queues import HoldingQueue, TakeOffQueue

class TempEmergency:
    def __init__(self, fuel_emergency: bool = False):
        self.fuel_emergency = fuel_emergency


class TempFuelAircraft:
    def __init__(self, callsign: str, fuelRemaining: int):
        self.callsign = callsign
        self.fuelRemaining = fuelRemaining
        self.emergency = TempEmergency(fuel_emergency=True) #to match queue
        self.enteredHoldingAt = None
        self.joinedTakeoffQueueAt = None

    def isEmergency(self) -> bool:
        return self.emergency


class TempAircraft:
    def __init__(self, callsign: str, emergency: bool = False):
        self.callsign = callsign
        self.emergency = emergency
        self.enteredHoldingAt = None
        self.joinedTakeoffQueueAt = None

    def isEmergency(self) -> bool:
        return self.emergency


#HoldingQueue tests

def test_holding_queue_starts_empty():
    hq = HoldingQueue()
    assert hq.size() == 0
    assert hq.peek() is None
    assert hq.dequeue() is None


def test_holding_queue_enqueue_sets_entered_time():
    hq = HoldingQueue()
    a = TempAircraft("A1", emergency=False)

    hq.enqueue(a, time=123)

    assert hq.size() == 1
    assert a.enteredHoldingAt == 123


def test_holding_queue_non_emergency_fifo():
    hq = HoldingQueue()
    a1 = TempAircraft("A1", emergency=False)
    a2 = TempAircraft("A2", emergency=False)

    hq.enqueue(a1, time=1)
    hq.enqueue(a2, time=2)

    assert hq.dequeue().callsign == "A1"
    assert hq.dequeue().callsign == "A2"
    assert hq.dequeue() is None


def test_holding_queue_emergency_goes_first():
    hq = HoldingQueue()
    normal = TempAircraft("N1", emergency=False)
    emerg = TempAircraft("E1", emergency=True)

    # normal arrives first but emergency should jump ahead
    hq.enqueue(normal, time=10)
    hq.enqueue(emerg, time=11)

    assert hq.dequeue().callsign == "E1"
    assert hq.dequeue().callsign == "N1"


def test_holding_queue_emergency_fifo_tiebreak():
    hq = HoldingQueue()
    e1 = TempAircraft("E1", emergency=True)
    e2 = TempAircraft("E2", emergency=True)

    hq.enqueue(e1, time=1)
    hq.enqueue(e2, time=2)

    assert hq.dequeue().callsign == "E1"
    assert hq.dequeue().callsign == "E2"


def test_holding_queue_peek_does_not_remove():
    hq = HoldingQueue()
    a1 = TempAircraft("A1", emergency=False)
    a2 = TempAircraft("A2", emergency=False)

    hq.enqueue(a1, time=1)
    hq.enqueue(a2, time=2)

    assert hq.size() == 2
    top = hq.peek()
    assert top.callsign == "A1"
    assert hq.size() == 2  #peek should not change size
    assert hq.dequeue().callsign == "A1"  #dequeue should match what peek returned


def test_holding_queue_dequeue_with_order_returns_tuple():
    hq = HoldingQueue()
    a = TempAircraft("A1", emergency=False)

    hq.enqueue(a, time=5)

    item = hq.dequeue_with_order()
    assert item is not None
    assert item[3].callsign == "A1"

def test_holding_queue_enqueue_with_order_follows_set_order():
    hq = HoldingQueue()
    a1 = TempAircraft("A1", emergency=False)
    a2 = TempAircraft("A2", emergency=False)

    hq.enqueue_with_order(a1, time=1, order=5)
    hq.enqueue_with_order(a2, time=2, order =1)

    assert hq.dequeue().callsign == "A2"
    assert hq.dequeue().callsign == "A1"


#HoldingQueue FuelEmergency test
def test_holding_queue_fuel_emergency_lower_fuel_goes_first():
    hq = HoldingQueue()
    #fuelEmergency will be set true for any TempFuelAircraft
    f1 = TempFuelAircraft("F1", fuelRemaining=30) 
    f2 = TempFuelAircraft("F2", fuelRemaining=10)

    hq.enqueue(f1, time=1)
    hq.enqueue(f2, time=2)

    assert hq.dequeue().callsign == "F2"
    assert hq.dequeue().callsign == "F1"

#To check FuelEmergency = Other Emergencies in priority
def test_holding_queue_fuel_emergency_equal_to_other_emergency():
    hq = HoldingQueue()
    e1 = TempAircraft("E1", emergency=True)
    f1 = TempFuelAircraft("F1", fuelRemaining=5)

    hq.enqueue(e1, time=1)
    hq.enqueue(f1, time=2)

    assert hq.dequeue().callsign == "E1"
    assert hq.dequeue().callsign == "F1"



#TakeOffQueue tests

def test_takeoff_queue_starts_empty():
    tq = TakeOffQueue()
    assert tq.size() == 0
    assert tq.isEmpty() is True
    assert tq.peek() is None
    assert tq.dequeue() is None


def test_takeoff_queue_enqueue_sets_joined_time():
    tq = TakeOffQueue()
    a = TempAircraft("T1", emergency=False)

    tq.enqueue(a, time=77)

    assert tq.size() == 1
    assert a.joinedTakeoffQueueAt == 77


def test_takeoff_queue_fifo_order():
    tq = TakeOffQueue()
    a1 = TempAircraft("T1")
    a2 = TempAircraft("T2")

    tq.enqueue(a1, time=1)
    tq.enqueue(a2, time=2)

    assert tq.peek().callsign == "T1"
    assert tq.dequeue().callsign == "T1"
    assert tq.dequeue().callsign == "T2"
    assert tq.dequeue() is None
    assert tq.isEmpty() is True
