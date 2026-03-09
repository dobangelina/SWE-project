from backend.SimulationParameters import SimulationParams
from backend.SimulationEngine import SimulationEngine
from backend.statistics import Statistics
from backend.queues import HoldingQueue, TakeOffQueue
from backend.runway import Runway
from backend.airport import Airport
from frontend.frontend import create_ui


def build_engine(seed: int = 42) -> SimulationEngine:
    """
    Create and configure a SimulationEngine instance with default parameters.

    The default configuration includes:
    - 2 runways:
        * Runway 1: TAKEOFF operations
        * Runway 2: LANDING operations
    - Inbound flow rate: 12 aircraft per hour
    - Outbound flow rate: 12 aircraft per hour
    - No stochastic arrival/departure variation (stddev = 0)
    - Simulation tick resolution of 1 minute
    - Fuel emergency threshold at 15 minutes
    - Minimum fuel diversion threshold at 10 minutes

    This function constructs all required backend components for the airport
    simulation, including the simulation parameters, statistics tracker,
    holding and takeoff queues, runways, and the airport environment itself.
    These components are then assembled into a fully initialised
    ``SimulationEngine`` object.

    Parameters
    ----------
    seed : int, optional
        Random seed used to initialise the simulation's random number
        generator. Providing a seed ensures deterministic and reproducible
        simulation runs. Default is 42.

    Returns
    -------
    SimulationEngine
        A fully configured simulation engine ready to run or be passed to
        the frontend UI.

    """

    params = SimulationParams(
        num_runways=2,
        inbound_rate_per_hour=12.0,
        outbound_rate_per_hour=12.0,
        arrival_stddev_min=0,
        departure_stddev_min=0,
        tick_size_min=1,
        fuel_emergency_min=15,
        fuel_min_min=10,
    )

    stats = Statistics()
    holding = HoldingQueue()
    takeoff = TakeOffQueue()

    runways = [
        Runway(runway_id=1, runway_mode="TAKEOFF"),
        Runway(runway_id=2, runway_mode="LANDING"),
    ]

    airport = Airport(runways=runways, holding=holding, takeoff=takeoff, stats=stats)

    return SimulationEngine(
        params=params,
        airport=airport,
        stats=stats,
        seed=seed,
    )


def main():
    engine = build_engine(seed=1)
    create_ui(engine)


if __name__ == "__main__":
    main()