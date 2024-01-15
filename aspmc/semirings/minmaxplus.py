class MinMaxPlusFloat(object):
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return MinMaxPlusFloat((min(self.value[0], other.value[0]), max(self.value[1], other.value[1])))

    def __iadd__(self, other):
        self.value[0] = max(self.value[0], other.value[0])
        self.value[1] = max(self.value[1], other.value[1])
        return self

    def __mul__(self, other):
        return MinMaxPlusFloat((self.value[0] + other.value[0], self.value[1] + other.value[1]))

    def __imul__(self, other):
        self.value[0] += other.value[0]
        self.value[1] += other.value[1]
        return self

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return repr(self)

def parse(value, atom = None):
    value = value[1:-1]
    value = value.split(',')
    return MinMaxPlusFloat((float(value[0]), float(value[1])))

def from_value(value):
    return MinMaxPlusFloat(value)

def negate(value):
    return zero()

def to_string(value):
    return str(value.value)
    
def is_idempotent():
    return True

def zero():
    return MinMaxPlusFloat((float("inf"), float("-inf")))

def one():
    return MinMaxPlusFloat((0, 0))
dtype = object
pattern = '\([+-]?([0-9]*[.])?[0-9]+,[+-]?([0-9]*[.])?[0-9]+\)'
