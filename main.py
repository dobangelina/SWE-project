# main.py
from __future__ import annotations

from backend.SimulationParameters import SimulationParams
from backend.SimulationEngine import SimulationEngine, EmergencyType
from backend.statistics import Statistics
from backend.queues import HoldingQueue, TakeOffQueue
from backend.runway import Runway
from backend.airport import Airport
from backend.aircraft import Aircraft
from frontend.frontend import create_ui


def fmt_emergency(a: Aircraft) -> str:
    e = getattr(a, "emergency", None)
    if e is None:
        return "-"
    flags = []
    if e.fuel_emergency:
        flags.append("FUEL")
    if e.mechanical_failure:
        flags.append("MECH")
    if e.passenger_illness:
        flags.append("ILL")
    return "|".join(flags) if flags else "-"


def snapshot_holding_order(holding: HoldingQueue) -> list[Aircraft]:
    temp = []
    ordered = []
    while holding.size() > 0:
        item = holding.dequeue_with_order()
        if item is None:
            break
        temp.append(item)
        ordered.append(item[3])

    # restore
    for _, _, order, a in temp:
        holding.enqueue_with_order(a, a.enteredHoldingAt, order)

    return ordered


def print_state(engine: SimulationEngine) -> None:
    now = engine.get_time()
    airport = engine.airport

    print("\n" + "=" * 90)
    print(f"TICK @ t={now} min")
    print("-" * 90)

    # Runways
    print("RUNWAYS:")
    for r in airport.runways:
        a = r.currentAircraft
        aid = a.id if a else "-"
        atype = a.type if a else "-"
        ef = fmt_emergency(a) if a else "-"
        fuel = a.fuelRemaining if a else "-"
        print(
            f"  RWY {r.id:>2} | cap={r.mode:<7} status={r.status:<9} "
            f"op={str(getattr(r, 'currentOperation', None)):<7} "
            f"occUntil={r.occupiedUntil:<4} | ac={aid:<3} {atype:<7} fuel={fuel!s:<3} emg={ef}"
        )

    # Holding queue (actual service order)
    print("\nHOLDING (service order):")
    ordered = snapshot_holding_order(airport.holding)
    if not ordered:
        print("  (empty)")
    else:
        for i, a in enumerate(ordered, 1):
            print(
                f"  {i:>2}. {a.id:<3} sched={a.scheduledTime:<4} entered={a.enteredHoldingAt!s:<4} "
                f"fuel={a.fuelRemaining:<3} emg={fmt_emergency(a)}"
            )

    # Takeoff queue (FIFO)
    print("\nTAKEOFF (FIFO):")
    tq = airport.takeoff.to_list()
    if not tq:
        print("  (empty)")
    else:
        for i, a in enumerate(tq, 1):
            print(
                f"  {i:>2}. {a.id:<3} joined={a.joinedTakeoffQueueAt!s:<4} emg={fmt_emergency(a)}"
            )

    # Stats snapshot (running totals)
    rep = engine.get_report()
    print("\nSTATS (so far):")
    for k in [
        "maxHoldingQueue",
        "avgHoldingQueue",
        "maxTakeoffQueue",
        "avgTakeoffQueue",
        "avgHoldingTime",
        "avgTakeoffWait",
        "avgArrivalDelay",
        "maxArrivalDelay",
        "diversions",
        "cancellations",
    ]:
        print(f"  {k:<15}: {rep.get(k)}")


def build_engine(seed: int = 42) -> SimulationEngine:
    params = SimulationParams(
        num_runways=2,
        inbound_rate_per_hour=12.0,
        outbound_rate_per_hour=6.0,
        arrival_stddev_min=0,
        departure_stddev_min=0,
        emergencies_per_tick=0,
        tick_size_min=1,
        fuel_emergency_min=15,
        fuel_min_min=10,
    )

    stats = Statistics()
    holding = HoldingQueue()
    takeoff = TakeOffQueue()

    runways = [
        Runway(runway_id=1, runway_mode="MIXED", runway_status="AVAILABLE"),
        Runway(runway_id=2, runway_mode="LANDING", runway_status="AVAILABLE"),
    ]

    airport = Airport(runways=runways, holding=holding, takeoff=takeoff, stats=stats)
    engine = SimulationEngine(params=params, airport=airport, stats=stats, seed=seed)
    return engine


def inject_test_aircraft(engine: SimulationEngine) -> None:

    airport = engine.airport
    now = engine.get_time()

    # Fuel emergencies with different fuel
    a1 = Aircraft("T1", "INBOUND", scheduledTime=now, fuelRemaining=14, emergency=EmergencyType(fuel_emergency=True))
    a2 = Aircraft("T2", "INBOUND", scheduledTime=now, fuelRemaining=12, emergency=EmergencyType(fuel_emergency=True))
    a3 = Aircraft("T3", "INBOUND", scheduledTime=now, fuelRemaining=18, emergency=EmergencyType(fuel_emergency=True))


    a4 = Aircraft("T4", "INBOUND", scheduledTime=now, fuelRemaining=50, emergency=EmergencyType(mechanical_failure=True))

    # Non-emergency inbound
    a5 = Aircraft("T5", "INBOUND", scheduledTime=now, fuelRemaining=40, emergency=None)

    for a in [a1, a2, a3, a4, a5]:
        airport.handleInbound(a, now)

    # Some outbound
    o1 = Aircraft("O1", "OUTBOUND", scheduledTime=now, fuelRemaining=0, emergency=None)
    o2 = Aircraft("O2", "OUTBOUND", scheduledTime=now, fuelRemaining=0, emergency=None)
    airport.handleOutbound(o1, now)
    airport.handleOutbound(o2, now)


def main() -> None:
    engine = build_engine(seed=1)

    # Start at t=0, inject a known queue state
    inject_test_aircraft(engine)

    # Run a few ticks with detailed printing
    for _ in range(15):
        print_state(engine)
        engine.tick()

    # Final report
    print("\n" + "#" * 90)
    print("FINAL REPORT")
    rep = engine.get_report()
    for k, v in rep.items():
        print(f"{k:<15}: {v}")


if __name__ == "__main__":
    #create_ui() #testing creating the UI in main.py, it works
    main()