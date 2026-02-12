from dataclasses import dataclass
from SimulationEngine import SimTime
SimTime = float

@dataclass

class Report:
    
    # Holding / Landing Stats 
    max_holding_size: int = 0
    avg_holding_size: float = 0.0
    max_holding_time: SimTime = 0.0
    avg_holding_time: float = 0.0
    
    # Takeoff Stats 
    max_takeoff_queue_size: int = 0
    max_takeoff_wait: SimTime = 0.0
    avg_takeoff_wait: float = 0.0
    
    # Exceptions 
    diversions: int = 0
    cancellations: int = 0
    
    # Simulation Info 
    total_time: int = 0