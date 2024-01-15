class TwoGradient(object):
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return TwoGradient((self.value[0] + other.value[0], self.value[1] + other.value[1], self.value[2] + other.value[2]))

    def __iadd__(self, other):
        self.value[0] += other.value[0]
        self.value[1] += other.value[1]
        self.value[2] += other.value[2]
        return self

    def __mul__(self, other):
        return TwoGradient((self.value[0] * other.value[0], 
                            self.value[0] * other.value[1] + self.value[1] * other.value[0], 
                            self.value[0] * other.value[2] + self.value[2] * other.value[0]))

    def __imul__(self, other):
        self.value[1] *= other.value[0]
        self.value[1] += self.value[0] * other.value[1]
        self.value[2] *= other.value[0]
        self.value[2] += self.value[0] * other.value[2]
        self.value[0] *= other.value[0]
        return self

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return repr(self.value)

def parse(value, atom = None):
    value = value[1:-1]
    value = value.split(',')
    return TwoGradient((float(value[0]), float(value[1]), float(value[2])))

def from_value(value):
    return TwoGradient(value)

def negate(value):
    return TwoGradient((1.0 - value.value[0], -value.value[1], -value.value[2]))

def to_string(value):
    return f"({value.value[0]},{value.value[1]},{value.value[2]})"

def is_idempotent():
    return False

def zero():
    return TwoGradient((0.0, 0.0, 0.0))
def one():
    return TwoGradient((1.0, 0.0, 0.0))

dtype = object
pattern = '\([+-]?([0-9]*[.])?[0-9]+,[+-]?([0-9]*[.])?[0-9],[+-]?([0-9]*[.])?[0-9]+\)'
