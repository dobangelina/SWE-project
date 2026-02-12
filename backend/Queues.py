from collections import deque #(FIFO Queue for Take-Off)
from queue import PriorityQueue #(Priority queue for Holding)

from aircraft import Aircraft
from SimulationEngine import SimTime

class HoldingQueue:
    #class constructor initializing attributes
    def __init__(self):
        #each item will be: tuple of (priority, arrival_order, Aircraft)
        #priority: 0 for emergency, 1 otherwise (lower value = higher priority)
        #arrival order: +1 each enqeue (FIFO if non-emergency)
        self.items = PriorityQueue()
        self.arrival_order = 0
        self.orderingRule = "Emergency-first"

    #adds a new aircraft to the queue, returns None
    def enqueue(self, a: Aircraft, time: SimTime) -> None:
        priority = not(a.isEmergency())
        self.items.put((priority, self.arrival_order, a))
        #increment the order (acts like a counter)
        self.arrival_order += 1
        
        #log the time aircraft entered holding queue
        a.enteredHoldingAt = time

    
    #removes the top aircraft from the queue and returns it (None if empty)
    def dequeue(self) -> Aircraft | None:
        #check if queue empty return None
        if self.items.empty():
            return None
        #unpacking tuple to get aircraft
        _,_, aircraftObj = self.items.get() 
        return aircraftObj
    
    #returns the aircraft at the top of the queue (None if empty)
    def peek(self) -> Aircraft | None:
        #check if queue empty return None
        if self.items.empty():
            return None
        #temporarily remove the item from queue and add it back
        temp = self.items.get()
        self.items.put(temp)
        #unpacking tuple to get aircraft
        _,_, aircraftObj = temp
        return aircraftObj

    #returns the size of the Holding queue
    def size(self) -> int:
        return self.items.qsize()


class TakeOffQueue:
    #constructor initializing attributes
    def __init__(self):
        self.items = deque()
        self.orderingRule = "FIFO Only"

    #logic of queue follows First In First Out so no priority needed

    def enqueue(self, a: Aircraft, time: SimTime) -> None:
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