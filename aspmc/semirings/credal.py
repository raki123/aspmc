import numpy as np

def parse(value, atom = None):
    value = value[1:-1]
    value = value.split(',')
    return np.array([float(value[0]), float(value[1])])

def from_value(value):
    return np.array(value)

def negate(value):
    return value.copy()

def to_string(value):
    return f"{value[0]} <= p <= {value[1]}"

def is_idempotent():
    return False

def zero():
    return np.array([0.0, 0.0])
def one():
    return np.array([1.0, 1.0])
    
dtype = float
pattern = '[(][0-9]+[,][0-9]+[)]'
