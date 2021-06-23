class ProbabilisticRule(object):
    def __init__(self, head, body = None, weight = None):
        self.head = head
        self.body = body if body is not None else []
        self.weight = weight

    def __str__(self):
        res = ""
        if self.head is not None:
            if self.weight is not None:
                res += f"{self.weight}::"
            res += f"{str(self.head)}"
            if len(self.body) > 0:
                res +=f":-{','.join([str(x) for x in self.body])}."
            else:
                res += "."
        else:
            res = f"query({str(self.body[0])})."
        return res
    
    def asp_string(self):
        res = ""
        if self.head is not None:
            if self.weight is not None:
                res += f"{{{str(self.head)}}}"
            else:
                res += str(self.head)
        if len(self.body) > 0:
            res +=f":-{','.join([str(x) for x in self.body])}."
        else:
            res += "."
        return res

    def is_query(self):
        return False

class Query(object):
    def __init__(self, atom):
        self.atom = atom

    def __str__(self):
        return f"query({str(self.atom)})."

    def asp_string(self):
        return f":-not {str(self.atom)}."


    def is_query(self):
        return True


class Atom(object):
    def __init__(self, predicate, inputs = None):
        self.predicate = predicate
        self.inputs = inputs if inputs is not None else []
        self.inputs = [ x.replace("'", '"') for x in inputs ]

    def __str__(self):
        res = ""
        res += f"{self.predicate}"
        if len(self.inputs) > 0:
            res += f"({','.join(self.inputs)})"
        return res

class ProblogSemantics(object):
    def start(self, ast):  # noqa
        return ast

    def program(self, ast):  # noqa
        new_program = []
        for rule in ast:
            # this ensures that all guesses are unconditional
            if not rule.is_query() and rule.weight is not None and len(rule.body) > 0:
                # make a new unconditional guess
                head = Atom(f"aux_{rule.head.predicate}", inputs = rule.head.inputs)
                guess_rule = ProbabilisticRule(head, [], rule.weight)
                actual_rule = ProbabilisticRule(rule.head, rule.body + [head], None)
                new_program += [guess_rule, actual_rule]
            else:
                new_program.append(rule)
        return new_program

    def rule(self, ast):  # noqa
        prob = None
        if type(ast[0]) == tuple:
            prob = ast[0][1]
            ast = ast[2:]
        rule = ast[0]
        head = rule['head']
        body = rule['body']
        rule = ProbabilisticRule(head, body, prob)
        return rule

    def normal_rule(self, ast):  # noqa
        if type(ast) == Atom:
            head = ast
            body = []
        else:
            head = ast[0]
            body = ast[2]
        return { 'head' : head, 'body': body }

    def body(self, ast):  # noqa
        atoms = [ast[0]]
        for i in ast[1]:
            atoms.append(i[1])
        return atoms

    def atom(self, ast):  # noqa
        if type(ast) == tuple or type(ast) == list:
            predicate = ast[0]
            inputs = ast[2]
        else:
            predicate = ast
            inputs = []
        return Atom(predicate, inputs)

    def input(self, ast):  # noqa
        inputs = [ast[0]]
        for i in ast[1]:
            inputs.append(i[1])
        return inputs

    def term(self, ast):  # noqa
        if "." in ast:
            return '"' + ast + '"'
        return ast

    def probability(self, ast):  # noqa
        return ('weight', ast)

    def query(self, ast):  # noqa
        return Query(ast[1])

