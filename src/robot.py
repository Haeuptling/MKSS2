class Robot:
    def __init__(self, id, position, energy):
        self.id = id
        self.position = position
        self.energy = energy
        self.status = {}
        self.inventory = {}
    
    def get_status(self):
        pass

    def move(self):
        pass

    def pickup(self):
        pass

    def pickdown(self):
        pass

    def get_state(self):
        pass

    def get_actions(self):
        pass

    def attack(self):
        pass

