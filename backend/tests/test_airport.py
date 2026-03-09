import pytest

#MagicMock helps isolate Airport logic and tests it
from unittest.mock import MagicMock

from backend.airport import Airport
from backend.runway import Runway
from backend.queues import HoldingQueue, TakeOffQueue


class TempAircraft:
    def __init__(self, id: str, emergency: bool = False):
        self.id = id
        self.emergency = emergency
        self.enteredHoldingAt = None
        self.joinedTakeoffQueueAt = None

    def isEmergency(self) -> bool:
        return self.emergency


class TestAirport:

    #pytest will run this setup method every time it runs a test
    def setup_method(self):
        self.holding = HoldingQueue()
        self.takeOff = TakeOffQueue()
        self.stats = MagicMock()


    #handleInbound / handleOutbound
    
    def test_handleInbound_enqueues_aircraft_and_records_stats(self):
        r = Runway("R1", "MIXED")
        airport = Airport([r], self.holding, self.takeOff, self.stats)

        a = TempAircraft("IN1")
        airport.handleInbound(a, time=10)

        #dequeue should return that same aircraft
        assert airport.holding.dequeue() == a
        self.stats.record_holding_entry.assert_called_once_with(a, 10) #checks that the function is called not its result

    def test_handleOutbound_enqueues_aircraft_and_records_stats(self):
        r = Runway("R2", "MIXED")
        airport = Airport([r], self.holding, self.takeOff, self.stats)

        a = TempAircraft("OUT1")
        airport.handleOutbound(a, time=7)

        assert airport.takeoff.dequeue() == a
        self.stats.record_takeoff_enqueue.assert_called_once_with(a, 7)

        
    #getEligibleRunways

    def test_getEligibleRunways_landing_returns_landing_and_mixed(self):
        r1 = Runway("R1", "LANDING")
        r2 = Runway("R2", "MIXED")
        r3 = Runway("R3", "TAKEOFF")

        airport = Airport([r1, r2, r3], self.holding, self.takeOff, self.stats)

        eligible = airport.getEligibleRunways("LANDING")

        assert r1 in eligible
        assert r2 in eligible
        assert r3 not in eligible

    def test_getEligibleRunways_takeoff_returns_takeoff_and_mixed(self):
        r1 = Runway("R1", "LANDING")
        r2 = Runway("R2", "MIXED")
        r3 = Runway("R3", "TAKEOFF")

        airport = Airport([r1, r2, r3], self.holding, self.takeOff, self.stats)

        eligible = airport.getEligibleRunways("TAKEOFF")

        assert r3 in eligible
        assert r2 in eligible
        assert r1 not in eligible

    def test_getEligibleRunways_unknown_operation_returns_empty(self):
        r = Runway("R1", "MIXED")
        airport = Airport([r], self.holding, self.takeOff, self.stats)

        assert airport.getEligibleRunways("UPDOWN") == []

  
    #assignLanding

    def test_assignLanding_available_landing_runways_assigns_plane_and_updates_stats(self):
        r = Runway("R1", "LANDING")

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        a = TempAircraft("IN2")
        airport.holding.enqueue(a, time=0)

        airport.assignLanding(time=5)

        #runway should time be occupied with aircraft A
        assert r.occupancy == "OCCUPIED"
        assert r.currentAircraft == a

        #sets fixed duration of 3
        assert r.startTime == 5
        assert r.duration == 3

        self.stats.record_landing.assert_called_once_with(a, 5)
        self.stats.record_runway_busy.assert_called_once_with(r, 3)

    def test_assignLanding_no_available_runways_does_not_dequeue(self):
        r = Runway("R1", "LANDING")
        r.occupancy = "OCCUPIED"  # not available

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        a = TempAircraft("IN3")
        airport.holding.enqueue(a, time=0)

        airport.assignLanding(time=5)

        #aircraft should still be in queue
        assert airport.holding.dequeue() == a
        self.stats.record_landing.assert_not_called()

    def test_assignLanding_runways_closed_does_not_dequeue(self):
        r = Runway("R1", "LANDING")
        r.status = "Runway Inspection"   # not AVAILABLE

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        a = TempAircraft("IN4")
        self.holding.enqueue(a, time=0)

        airport.assignLanding(time=5) 

        #aircraft should still be in queue
        assert self.holding.dequeue() == a
        self.stats.record_landing.assert_not_called()

    def test_assignLanding_empty_queue_does_nothing(self):
        r = Runway("R1", "LANDING")

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        airport.assignLanding(time=5)

        assert r.occupancy != "OCCUPIED"
        self.stats.record_landing.assert_not_called()

    def test_assignLanding_multiple_runways_assigns_multiple_planes(self):
        r1 = Runway("R1", "LANDING")
        r2 = Runway("R2", "LANDING")
        airport = Airport([r1, r2], self.holding, self.takeOff, self.stats)

        a1 = TempAircraft("IN5")
        a2 = TempAircraft("IN6")
        airport.holding.enqueue(a1, time=0)
        airport.holding.enqueue(a2, time=0)

        airport.assignLanding(time=10)

        assert r1.currentAircraft in (a1, a2)
        assert r2.currentAircraft in (a1, a2)
        assert r1.currentAircraft != r2.currentAircraft
        assert self.stats.record_landing.call_count == 2
        assert self.stats.record_runway_busy.call_count == 2


    #assignTakeOff

    def test_assignTakeOff_available_takeoff_runway_assigns_plane_and_updates_stats(self):
        r = Runway("R1", "TAKEOFF")

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        a = TempAircraft("OUT2")
        airport.takeoff.enqueue(a, time=0)

        airport.assignTakeOff(time=8)

        assert r.occupancy == "OCCUPIED"
        assert r.currentAircraft == a
        assert r.startTime == 8
        assert r.duration == 3

        self.stats.record_takeoff.assert_called_once_with(a, 8)
        self.stats.record_runway_busy.assert_called_once_with(r, 3)

    def test_assignTakeOff_closed_runways_does_not_dequeue(self):
        r = Runway("R1", "TAKEOFF")
        r.status = "Snow Clearance"

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        a = TempAircraft("OUT3")
        airport.takeoff.enqueue(a, time=0)

        airport.assignTakeOff(time=8)

        #aircraft should still be in queue
        assert self.takeOff.dequeue() == a
        self.stats.record_takeoff.assert_not_called()


    def test_assignTakeOff_no_available_runway_does_not_dequeue(self):
        r = Runway("R1", "TAKEOFF")
        r.occupancy = "OCCUPIED"

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        a = TempAircraft("OUT4")
        airport.takeoff.enqueue(a, time=0)

        airport.assignTakeOff(time=8)

        assert airport.takeoff.dequeue() == a
        self.stats.record_takeoff.assert_not_called()


    #updateRunways

    def test_updateRunways_frees_runway_when_time_passed(self):
        r = Runway("R1", "MIXED")
        r.occupancy = "OCCUPIED"
        r.occupiedUntil = 10
        r.currentAircraft = TempAircraft("A1")
        r.currentOperation = "LANDING"

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        airport.updateRunways(time=10)

        assert r.occupancy == "FREE"
        assert r.occupiedUntil == 0
        assert r.currentAircraft is None
        assert r.currentOperation is None

    def test_updateRunways_does_not_free_if_time_not_passed(self):
        r = Runway("R1", "MIXED")
        r.occupancy = "OCCUPIED"
        r.occupiedUntil = 10
        r.currentAircraft = TempAircraft("A1")
        r.currentOperation = "LANDING"

        airport = Airport([r], self.holding, self.takeOff, self.stats)

        airport.updateRunways(time=9)

        assert r.occupancy == "OCCUPIED"
        assert r.currentAircraft is not None

