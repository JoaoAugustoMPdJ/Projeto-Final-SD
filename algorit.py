class LamportClock:
    def __init__(self):
        self.time = 0
        self.pending_events = []
        
    def increment(self):
        self.time += 1
        self.pending_events.append(('local', self.time))
        return self.time
        
    def update(self, received_time):
        self.time = max(self.time, received_time) + 1
        self.pending_events.append(('received', received_time, self.time))
        return self.time
        
    def get_time(self):
        return self.time
        
    def get_events(self):
        return self.pending_events.copy()
        
    def clear_events(self):
        self.pending_events = []