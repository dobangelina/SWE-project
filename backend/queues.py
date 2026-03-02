from .aircraft import Aircraft
from collections import deque #(FIFO Queue for Take-Off)
from queue import PriorityQueue #(Priority queue for Holding)

class HoldingQueue:
    #class constructor initializing attributes
    def __init__(self):
        #each item will be: tuple of (priority, fuel, arrival_order, Aircraft)
        #old priority: 0 for emergency, 1 otherwise (lower value = higher priority)
        # new priority: uses a function based on the fuel amount (Low fuel amount = high emergency, high fuel amount = low emergency)
        # for simplicity, we can just make the priority equal to the fuel amount. 

        #arrival order: +1 each enqeue (FIFO if non-emergency)
        self.items = PriorityQueue()
        self.arrival_order = 0
        self.orderingRule = "Emergency-first"

    #adds a new aircraft to the queue, returns None
    def enqueue(self, a: Aircraft, time: int) -> None:

        is_fuel_emergency = bool(a.emergency and getattr(a.emergency, "fuel_emergency", False))
        if a.isEmergency():
            if is_fuel_emergency:
                emergency_priority = 0  # fuel emergency
            else:
                emergency_priority = 1  # other emergency
        else:
            emergency_priority = 2  # non-emergency
        fuel_key = a.fuelRemaining if is_fuel_emergency else 10 ** 9

        self.items.put((emergency_priority,fuel_key, self.arrival_order, a))
        #increment the order (acts like a counter)
        self.arrival_order += 1
        
        #log the time aircraft entered holding queue
        a.enteredHoldingAt = time

    def enqueue_with_order(self, a: Aircraft, time: int, order: int) -> None:
        emergency_priority = 0 if a.isEmergency() else 1
        is_fuel_emergency = bool(a.emergency and getattr(a.emergency, "fuel_emergency", False))
        fuel_key = a.fuelRemaining if is_fuel_emergency else 10 ** 9
        self.items.put((emergency_priority, fuel_key, order, a))
        a.enteredHoldingAt = time

    def dequeue_with_order(self):
        if self.items.empty():
            return None
        emergency_priority, fuel_key, order, aircraft = self.items.get()
        return emergency_priority, fuel_key, order, aircraft

    
    #removes the top aircraft from the queue and returns it (None if empty)
    def dequeue(self) -> Aircraft | None:
        #check if queue empty return None
        if self.items.empty():
            return None
        #unpacking tuple to get aircraft
        _, _, _, aircraft_obj = self.items.get()
        return aircraft_obj
    
    #returns the aircraft at the top of the queue (None if empty)
    def peek(self) -> Aircraft | None:
        #check if queue empty return None
        if self.items.empty():
            return None
        return self.items.queue[0][3]

    #returns the size of the Holding queue
    def size(self) -> int:
        return self.items.qsize()

    def to_list(self):
        # For UI snapshot
        return [t[3] for t in list(self.items.queue)]


class TakeOffQueue:
    #constructor initializing attributes
    def __init__(self):
        self.items = deque()
        self.orderingRule = "FIFO Only"

    #logic of queue follows First In First Out so no priority needed

    def enqueue(self, a: Aircraft, time: int) -> None:
        self.items.append(a)
        #log the time aircraft joined take-off queue
        a.joinedTakeoffQueueAt = time

    def dequeue(self) -> Aircraft | None:
        #check if queue empty return None
        if self.isEmpty():
            return None
        
        return self.items.popleft()
    
    def peek(self) -> Aircraft | None:
        if self.isEmpty():
            return None
        return self.items[0]

    def size(self) -> int:
        return len(self.items)
    
    #wasnt in the diagram but added it as deque doesnt have such method
    def isEmpty(self) -> bool:
        return not(self.items)

    def to_list(self):
        # For UI snapshot / debugging
        return list(self.items)
