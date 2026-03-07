import pytest
from backend.statistics import Statistics


class TempParams:
    def __init__(self, arrival_stddev_min=0, departure_stddev_min=0, tick_size_min=1):
        self.arrival_stddev_min = arrival_stddev_min
        self.departure_stddev_min = departure_stddev_min
        self.tick_size_min = tick_size_min

class TempAircraft:
    def __init__(self, scheduledTime=None):
        self.scheduledTime = scheduledTime
        self.enteredHoldingAt = None
        self.joinedTakeoffQueueAt = None

#TESTS

#Queue snapshots: max + average
def test_snapshot_queues_max_and_avg():
    stats = Statistics()

    stats.snapshot_queues(holding_size=1, takeoff_size=3, time=0)
    stats.snapshot_queues(holding_size=4, takeoff_size=2, time=1)
    stats.snapshot_queues(holding_size=2, takeoff_size=10, time=2)

    rep = stats.report()

    assert rep["maxHoldingQueue"] == 4.0
    assert rep["avgHoldingQueue"] == pytest.approx((1 + 4 + 2) / 3)

    assert rep["maxTakeoffQueue"] == 10.0
    assert rep["avgTakeoffQueue"] == pytest.approx((3 + 2 + 10) / 3)


#Landing: holding time avg + arrival delay avg + max arrival delay
def test_record_landing_updates_holding_and_delay():
    stats = Statistics()

    a1 = TempAircraft(scheduledTime=10)
    a1.enteredHoldingAt = 12
    stats.record_landing(a1, time=20)  # holding=8, delay=10

    a2 = TempAircraft(scheduledTime=5)
    a2.enteredHoldingAt = 6
    stats.record_landing(a2, time=30)  # holding=24, delay=25 (max)

    rep = stats.report()

    assert rep["avgHoldingTime"] == pytest.approx((8 + 24) / 2)
    assert rep["avgArrivalDelay"] == pytest.approx((10 + 25) / 2)
    assert rep["maxArrivalDelay"] == 25.0


#Takeoff: avg wait + max wait (ignore missing join time)
def test_record_takeoff_wait_and_max_and_missing_join():
    stats = Statistics()

    a1 = TempAircraft()
    a1.joinedTakeoffQueueAt = 5
    stats.record_takeoff(a1, time=12)  # wait=7

    a2 = TempAircraft()
    a2.joinedTakeoffQueueAt = 1
    stats.record_takeoff(a2, time=20)  # wait=19 (max)

    a3 = TempAircraft()
    a3.joinedTakeoffQueueAt = None
    stats.record_takeoff(a3, time=50)

    rep = stats.report()

    assert rep["avgTakeoffWait"] == pytest.approx((7 + 19) / 2)
    assert rep["maxTakeoffWait"] == 19.0


#Diversions and cancellations counters
def test_diversions_and_cancellations():
    stats = Statistics()

    stats.record_diversion()
    stats.record_diversion()
    stats.record_cancellation()

    rep = stats.report()
    assert rep["diversions"] == 2.0
    assert rep["cancellations"] == 1.0


#Standard div tests

#INBOUND
#If sigma is 0, there should be NO randomness: spawn == scheduled
def test_inbound_sigma_zero_returns_scheduled():
    stats = Statistics()
    stats.configure_from_params(TempParams(arrival_stddev_min=0), seed=1)

    assert stats.sample_inbound_spawn_time(100) == 100
    assert stats.sample_inbound_spawn_time(0) == 0

#Same seed should produce the same "random" sequence
def test_inbound_same_seed_same_results():
    params = TempParams(arrival_stddev_min=5)

    s1 = Statistics()
    s1.configure_from_params(params, seed=123)
    seq1 = [s1.sample_inbound_spawn_time(100) for _ in range(30)]

    s2 = Statistics()
    s2.configure_from_params(params, seed=123)
    seq2 = [s2.sample_inbound_spawn_time(100) for _ in range(30)]

    assert seq1 == seq2

#Spawn time should never go below 0
def test_inbound_never_negative():
    stats = Statistics()
    stats.configure_from_params(TempParams(arrival_stddev_min=50), seed=2)

    #scheduled is small
    for _ in range(1000):
        assert stats.sample_inbound_spawn_time(1) >= 0

#Over many samples: average should be close to scheduled time
def test_inbound_mean_close_to_scheduled():
    stats = Statistics()
    stats.configure_from_params(TempParams(arrival_stddev_min=5), seed=42)

    scheduled = 100
    n = 10000
    samples = [stats.sample_inbound_spawn_time(scheduled) for _ in range(n)]

    mean = sum(samples) / n

    #allow small tolerance because of rounding to int minutes
    assert abs(mean - scheduled) < 0.25

#Over many samples, "spread" (std dev) should be close to sigma
def test_inbound_spread_close_to_sigma():
    stats = Statistics()
    stats.configure_from_params(TempParams(arrival_stddev_min=5), seed=99)

    scheduled = 100
    n = 15000
    samples = [stats.sample_inbound_spawn_time(scheduled) for _ in range(n)]

    #convert to jitter values
    jitters = [x - scheduled for x in samples]

    #calculate std div
    mean = sum(jitters) / n
    variance = sum((x - mean) ** 2 for x in jitters) / n
    stdev = variance ** 0.5

    #rounding shrinks spread slightly: allow tolerance
    assert stdev == pytest.approx(5, rel=0.06)


#OUTBOUND
def test_outbound_sigma_zero_returns_scheduled():
    stats = Statistics()
    #arrival sigma is non-zero departure sigma is zero
    stats.configure_from_params(TempParams(arrival_stddev_min=5, departure_stddev_min=0), seed=1)

    assert stats.sample_outbound_spawn_time(100) == 100