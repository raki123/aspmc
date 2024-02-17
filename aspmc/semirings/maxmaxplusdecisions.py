names = []

class MinMaxPlusFloat(object):
    def __init__(self, value, decisions):
        self.value = value
        self.decisions = decisions

    def __add__(self, other):
        first = self if self.value[0] >= other.value[0] else other
        second = self if self.value[1] >= other.value[1] else other
        return MinMaxPlusFloat((first.value[0], second.value[1]), (first.decisions[0], second.decisions[1]))

    def __iadd__(self, other):
        if self.value[0] > other.value[0]:
            self.value[0] = other.value[0]
            self.decisions[0] = other.decisions[0]
        if self.value[1] > other.value[1]:
            self.value[1] = other.value[1]
            self.decisions[1] = other.decisions[1]
        return self

    def __mul__(self, other):
        return MinMaxPlusFloat( (self.value[0] + other.value[0], self.value[1] + other.value[1]),
                                (self.decisions[0] | other.decisions[0], self.decisions[1] | other.decisions[1]))

    def __imul__(self, other):
        self.value[0] += other.value[0]
        self.value[1] += other.value[1]
        self.decisions[0] |= other.decisions[0]
        self.decisions[1] |= other.decisions[1]
        return self

    def __str__(self):
        min_decisions = [ names[i] for i in range(len(names)) if self.decisions[0] & 2**i ]
        min_decisions = ", ".join(min_decisions)
        max_decisions = [ names[i] for i in range(len(names)) if self.decisions[1] & 2**i ]
        max_decisions = ", ".join(max_decisions)
        ret = f"Minimum of {self.value[0]} with true atoms: {min_decisions}\n"
        ret += f"Maximum of {self.value[1]} with true atoms: {max_decisions}"
        return ret

    def __repr__(self):
        return str(self)

def parse(value, atom = None):
    value = value[1:-1]
    value = value.split(',')
    return MinMaxPlusFloat((float(value[0]), float(value[1])), (int(value[2]), int(value[3])))

def from_value(value):
    return MinMaxPlusFloat(value, (0, 0))

def negate(value):
    return one()

def to_string(value):
    return f"({value.value},{value.decisions})"

def is_idempotent():
    return True

def zero():
    return MinMaxPlusFloat((float("-inf"), float("-inf")), (0, 0))
def one():
    return MinMaxPlusFloat((0, 0), (0, 0))

dtype = object
pattern = '\(\([+-]?([0-9]*[.])?[0-9]+,[+-]?([0-9]*[.])?[0-9]+,\),\([0-9]+,[0-9]+\)\)'