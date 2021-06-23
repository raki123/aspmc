first = None
class Gradient(object):
    def __init__(self, value):
        self.value = value

    def __add__(self, other):
        return Gradient((self.value[0] + other.value[0], self.value[1] + other.value[1]))

    def __iadd__(self, other):
        self.value[0] += other.value

    def __mul__(self, other):
        return Gradient((self.value[0] * other.value[0], self.value[0] * other.value[1] + self.value[1] * other.value[0]))

    def __imul__(self, other):
        self.value[1] *= other.value[0]
        self.value[1] += self.value[0] * other.value[1]
        self.value[0] *= other.value[0]

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return repr(self.value)

def parse(value, atom = None):
    global first
    if first is None:
        first = atom
    if atom is first:
        return Gradient((float(value), 1.0))
    else:
        return Gradient((float(value), 0.0))

def negate(value):
    return Gradient((1.0 - value.value[0], -value.value[1]))

zero = Gradient((0.0, 0.0))
one = Gradient((1.0, 0.0))
dtype = object
