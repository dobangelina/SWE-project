from dataclasses import dataclass, field
from SimulationEngine import SimTime

@dataclass
class Statistics:
    # Queue Sizes
    max_holding_size: int = 0
    takeoff_size: int = 0  
    
    # Holding / Landing Metrics
    holding_time_sum: float = 0.0
    holding_count: int = 0
    
    # Takeoff Metrics
    takeoff_wait_sum: float = 0.0
    takeoff_count: int = 0
    
    # Arrival / Delay Metrics
    arrival_delay_sum: float = 0.0
    arrival_count: int = 0
    max_arrival_delay:  SimTime = 0.0 # Please change this, SimTime is an object
    
    # Exceptions
    diversions: int = 0
    cancellations: int = 0
    
    # Runway Usage (Map<Runway, int>)
    runway_busy_time: dict = field(default_factory=dict)

    def record_holding_entry(self, aircraft, time: float) -> None:
        pass

    def record_landing(self, aircraft, time: float) -> None:
        pass

    def record_takeoff_enqueue(self, aircraft, time: float) -> None:
        pass

    def record_takeoff(self, aircraft, time: float) -> None:
        pass

    def record_diversion(self, aircraft, time: float) -> None:
        pass

    def record_cancellation(self, aircraft, time: float) -> None:
        pass