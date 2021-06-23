class MaxPlusFloat(object):
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return self if self.value >= other.value else other

    def __iadd__(self, other):
        self.value = max(self.value, other.value)

    def __mul__(self, other):
        return MaxPlusFloat(self.value + other.value)

    def __imul__(self, other):
        self.value += other.value

    def __str__(self):
        return str(self.value)

def parse(value, atom = None):
    return MaxPlusFloat(float(value))

def negate(value):
    return value

zero = MaxPlusFloat(float("-inf"))
one = MaxPlusFloat(0)
dtype = object
