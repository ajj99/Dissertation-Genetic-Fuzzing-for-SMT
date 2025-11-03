
# from z3 import *
# import cvc5
# from cvc5 import Kind
# import random
# from deap import base, creator, tools, gp, algorithms
# import operator
# import math
# import time
# from abc import ABC, abstractmethod
#
#
# class SolverAdapter(ABC):
#     """Abstract base class for any SMT solver."""
#     @abstractmethod
#     def const(self, val): pass
#     @abstractmethod
#     def add(self, x, y): pass
#     @abstractmethod
#     def sub(self, x, y): pass
#     @abstractmethod
#     def mul(self, x, y): pass
#     @abstractmethod
#     def gt(self, x, y): pass
#     @abstractmethod
#     def lt(self, x, y): pass
#     @abstractmethod
#     def ge(self, x, y): pass
#     @abstractmethod
#     def le(self, x, y): pass
#     @abstractmethod
#     def eq(self, x, y): pass
#     @abstractmethod
#     def make_vars(self, num): pass
#     @abstractmethod
#     def assert_formula(self, expr): pass
#     @abstractmethod
#     def check(self): pass
#
# class Z3Adapter(SolverAdapter):
#     def __init__(self):
#         self.solver = Solver()
#
#     # z3 works with symbolic objects IntVal, BoolVan etc not plain integers/bools
#     # so const converts a python int -> z3 int constant for e.g
#     def const(self, val):
#         if isinstance(val, (int, bool)):
#             return IntVal(val) if isinstance(val, int) else BoolVal(val)
#         return val
#
#     #regularly defined operators as z3, internally defined __methods in z3
#     def add(self, x, y): return x + y
#     def sub(self, x, y): return x - y
#     def mul(self, x, y): return x * y
#     def gt(self, x, y): return x > y
#     def lt(self, x, y): return x < y
#     def ge(self, x, y): return x >= y
#     def le(self, x, y): return x <= y
#     def eq(self, x, y): return x == y
#
#     def make_vars(self, num):
#         return [Int(f"x{i}") for i in range(num)]
#
#     def assert_formula(self, expr):
#         self.solver.add(expr)
#
#     def check(self):
#         return self.solver.check()
#
# class CVC5Adapter(SolverAdapter):
#     class Term:
#         #Wraps a cvc5.Term and implements Python operators
#         def __init__(self, adapter, term):
#             self.adapter = adapter
#             self.term = term
#
#         #if other is already a cvc5adapter term, returns the underlying cvc5 term
#         #if other is not, such as int or bool, sends to const
#         # which converts it into a cvc5 term via mkinteger, etc.
#         def unwrap(self, other):
#             if isinstance(other, CVC5Adapter.Term):
#                 return other.term
#             return self.adapter.const(other)
#
#         # Operator overloads, Python internally performs these when it sees +, -, etc.
#         #r funcs handle reverse cases where a constant is on the LHS (3+x) not RHS (x+3)
#         #takes the expr either side of the operator and recursively unpacks them and then wraps them into a cvc5 term
#         def __add__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.add(self.term, self.unwrap(other)))
#         def __radd__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.add(self.unwrap(other), self.term))
#         def __sub__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.sub(self.term, self.unwrap(other)))
#         def __rsub__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.sub(self.unwrap(other), self.term))
#         def __mul__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.mul(self.term, self.unwrap(other)))
#         def __rmul__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.mul(self.unwrap(other), self.term))
#
#
#         def __gt__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.gt(self.term, self.unwrap(other)))
#         def __lt__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.lt(self.term, self.unwrap(other)))
#         def __ge__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.ge(self.term, self.unwrap(other)))
#         def __le__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.le(self.term, self.unwrap(other)))
#         def __eq__(self, other): return CVC5Adapter.Term(self.adapter, self.adapter.eq(self.term, self.unwrap(other)))
#
#         def __repr__(self): return f"CVC5Term({self.term})"
#
#     def __init__(self):
#         self.solver = cvc5.Solver()
#         self.solver.setLogic("QF_NIA")
#         self.solver.setOption("tlimit", "1000")
#         self.sort = self.solver.getIntegerSort()
#
#     def const(self, val):
#         if isinstance(val, CVC5Adapter.Term):
#             return val.term
#         if isinstance(val, bool):
#             return self.solver.mkBoolean(val)
#         if isinstance(val, cvc5.Term):
#             return val
#         return self.solver.mkInteger(val)
#
#     # Primitive operations
#     def add(self, x, y): return self.solver.mkTerm(Kind.ADD, x, y)
#     def sub(self, x, y): return self.solver.mkTerm(Kind.SUB, x, y)
#     def mul(self, x, y): return self.solver.mkTerm(Kind.MULT, x, y)
#     def gt(self, x, y): return self.solver.mkTerm(Kind.GT, x, y)
#     def lt(self, x, y): return self.solver.mkTerm(Kind.LT, x, y)
#     def ge(self, x, y): return self.solver.mkTerm(Kind.GEQ, x, y)
#     def le(self, x, y): return self.solver.mkTerm(Kind.LEQ, x, y)
#     def eq(self, x, y): return self.solver.mkTerm(Kind.EQUAL, x, y)
#
#     def make_vars(self, num):
#         raw = [self.solver.mkConst(self.sort, f"x{i}") for i in range(num)]
#         return [CVC5Adapter.Term(self, t) for t in raw]
#
#     def assert_formula(self, expr):
#         if isinstance(expr, CVC5Adapter.Term):
#             expr = expr.term
#
#         elif isinstance(expr, bool):
#             expr = self.solver.mkBoolean(expr)
#         self.solver.assertFormula(expr)
#     def check(self):
#         return self.solver.checkSat()
#
# #CONFIG
# NUM_VARS = 3
# NUM_ASSERTS = 2
# MAX_DEPTH = 3
#
# #PRIMITIVES
# # Use only ArithRef/BoolRef-like types from the z3 module so gp.compile creates
# # functions that expect numeric/bool-like arguments.
# pset = gp.PrimitiveSetTyped("MAIN", [ArithRef] * NUM_VARS, BoolRef)
#
# # Arithmetic operations use operator.* (these will call CVC5Proxy methods when needed)
# pset.addPrimitive(operator.add, [ArithRef, ArithRef], ArithRef, name="add")
# pset.addPrimitive(operator.sub, [ArithRef, ArithRef], ArithRef, name="sub")
# pset.addPrimitive(operator.mul, [ArithRef, ArithRef], ArithRef, name="mul")
#
# # Comparisons
# pset.addPrimitive(operator.gt, [ArithRef, ArithRef], BoolRef, name="gt")
# pset.addPrimitive(operator.lt, [ArithRef, ArithRef], BoolRef, name="lt")
# pset.addPrimitive(operator.ge, [ArithRef, ArithRef], BoolRef, name="ge")
# pset.addPrimitive(operator.le, [ArithRef, ArithRef], BoolRef, name="le")
# pset.addPrimitive(operator.eq, [ArithRef, ArithRef], BoolRef, name="eq")
#
# # constants and terminals
# pset.addEphemeralConstant("rand100", lambda: random.randint(0, 100), ArithRef)
# pset.addTerminal(True, BoolRef)
# pset.addTerminal(False, BoolRef)
#
# #DEAP SETUP
# creator.create("RunTimeFitness", base.Fitness, weights=(1.0,))
# creator.create("IndividualSMT", gp.PrimitiveTree, fitness=creator.RunTimeFitness)
#
# toolbox = base.Toolbox()
# toolbox.register("expr", gp.genFull, pset=pset, min_=1, max_=MAX_DEPTH)
# toolbox.register("individual", tools.initIterate, creator.IndividualSMT, toolbox.expr)
# toolbox.register("population", tools.initRepeat, list, toolbox.individual)
#
# # evaluation -> compile once, run on both adapters
# def eval_individualSMT(individual):
#     func = gp.compile(expr=individual, pset=pset)
#
#     # ----- Z3 -----
#     z3 = Z3Adapter()
#     z3_vars = z3.make_vars(NUM_VARS)             # returns real z3 Ints
#     z3_expr = func(*z3_vars)                     # compiled function uses operator.* which works for z3
#     z3.assert_formula(z3_expr)
#     start = time.time()
#     z3.check()
#     z3_time = time.time() - start
#
#     # ----- cvc5 -----
#     cvc5_adapter = CVC5Adapter()
#     cvc5_vars = cvc5_adapter.make_vars(NUM_VARS)
#     cvc5_expr = func(*cvc5_vars)                  # compiled function uses operator.*, proxies delegate to adapter
#
#     # if cvc5_expr is wrapped, unwrap to raw term before asserting
#     if isinstance(cvc5_expr, CVC5Adapter.Term):
#         cvc5_expr = cvc5_expr.term
#
#     cvc5_adapter.assert_formula(cvc5_expr)
#     start = time.time()
#     cvc5_adapter.check()
#     cvc5_time = time.time() - start
#
#     # difference between relative
#     return ((z3_time + cvc5_time) / 2, )
#
# toolbox.register("evaluate", eval_individualSMT)
# toolbox.register("select", tools.selTournament, tournsize=3)
# toolbox.register("mate", gp.cxOnePoint)
# toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
# toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)
#
# # GP loop (unchanged)
# def main():
#     population = toolbox.population(n=20)   # use smaller for testing
#     hof = tools.HallOfFame(5)
#
#     statistics = tools.Statistics(lambda smt: smt.fitness.values[0])
#     statistics.register("avg", lambda fits: sum(fits) / len(fits))
#     statistics.register("min", min)
#     statistics.register("max", max)
#
#     population, log = algorithms.eaSimple(
#         population=population,
#         toolbox=toolbox,
#         cxpb=0.5,
#         mutpb=0.2,
#         ngen=5,
#         stats=statistics,
#         halloffame=hof,
#         verbose=False
#     )
#
#     def pretty_print_tree(tree):
#         s = str(tree)
#         s = s.replace("add", "+")
#         s = s.replace("sub", "-")
#         s = s.replace("mul", "*")
#         s = s.replace("gt", ">")
#         s = s.replace("lt", "<")
#         s = s.replace("ge", ">=")
#         s = s.replace("le", "<=")
#         s = s.replace("eq", "==")
#         return s
#
#     print("Best individuals:")
#     for smt in hof:
#         print(pretty_print_tree(smt))
#         print(smt.fitness.values)
#
#     return population, log, hof
#
# if __name__ == "__main__":
#     main()
#
from z3 import *
import subprocess
from z3 import Solver
import random
import time
from deap import base, creator, tools, gp, algorithms
# from pysmt.shortcuts import Solver
# from pysmt.smtlib.parser import SmtLibParser
from io import StringIO
import operator

# ===========================================================
# 1. GP + Z3 Primitive Setup
# ===========================================================

NUM_VARS = 3
MAX_DEPTH = 6

pset = gp.PrimitiveSetTyped("MAIN", [ArithRef]*NUM_VARS, BoolRef)

# Arithmetic
pset.addPrimitive(lambda x, y: x + y, [ArithRef, ArithRef], ArithRef, name="add")
pset.addPrimitive(lambda x, y: x - y, [ArithRef, ArithRef], ArithRef, name="sub")
pset.addPrimitive(lambda x, y: x * y, [ArithRef, ArithRef], ArithRef, name="mul")

# Comparisons
pset.addPrimitive(lambda x, y: x > y, [ArithRef, ArithRef], BoolRef, name="gt")
pset.addPrimitive(lambda x, y: x < y, [ArithRef, ArithRef], BoolRef, name="lt")
pset.addPrimitive(lambda x, y: x >= y, [ArithRef, ArithRef], BoolRef, name="ge")
pset.addPrimitive(lambda x, y: x <= y, [ArithRef, ArithRef], BoolRef, name="le")
pset.addPrimitive(lambda x, y: x == y, [ArithRef, ArithRef], BoolRef, name="eq")

# Constants and terminals
#pset.addEphemeralConstant("rand100", lambda: IntVal(random.randint(0, 100)), ArithRef)
pset.addTerminal(BoolVal(True), BoolRef)
pset.addTerminal(BoolVal(False), BoolRef)

# pset.addPrimitive(And, [BoolRef, BoolRef], BoolRef, name="And")
# pset.addPrimitive(Or, [BoolRef, BoolRef], BoolRef, name="Or")
# pset.addPrimitive(Not, [BoolRef], BoolRef, name="Not")

# ===========================================================
# 2. DEAP individual and population setup
# ===========================================================

creator.create("RunTimeFitness", base.Fitness, weights=(1.0,))  # maximise runtime
creator.create("IndividualSMT", gp.PrimitiveTree, fitness=creator.RunTimeFitness)

toolbox = base.Toolbox()
toolbox.register("expr", gp.genFull, pset=pset, min_=1, max_=MAX_DEPTH, type_=BoolRef)
toolbox.register("individual", tools.initIterate, creator.IndividualSMT, toolbox.expr)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# ===========================================================
# 3. Evaluation and Solving
# ===========================================================

def measure_runtime_subprocess_stdin(smtlib_str, solver_cmd):

    start = time.time()
    subprocess.run([solver_cmd, "-in"], input=smtlib_str, text=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end = time.time()
    return end - start

def evaluate(individual):
    # Compile DEAP expression
    func = gp.compile(expr=individual, pset=pset)

    # Create Z3 variables
    vars_z3 = [Int(f"x{i}") for i in range(NUM_VARS)]

    # Build Z3 formula
    z3_formula = func(*vars_z3)
    if isinstance(z3_formula, bool):
        z3_formula = BoolVal(z3_formula)

    # Use a Z3 solver to collect all assertions
    s = Solver()
    s.add(z3_formula)
    #print(z3_formula)

    # Manually set logic (example: QF_LIA)
    logic_str = "(set-logic QF_LIA)\n"

    # Convert solver with assertions to SMT-LIB string
    smtlib_str = logic_str + s.to_smt2()

    threads = 4
    z3_header = f"(set-option :parallel.enable true)\n(set-option :parallel.threads {threads})\n"
    cvc5_header = f"(set-option :threads {threads})\n"

    t_z3 = measure_runtime_subprocess_stdin(z3_header + smtlib_str, "z3")
    t_cvc5 = measure_runtime_subprocess_stdin(cvc5_header + smtlib_str, "cvc5")

    # Fitness = relative difference between runtimes
    if max(t_z3, t_cvc5) == 0:
        fitness = 0.0
    else:

        fitness = 100 * abs(t_z3 - t_cvc5) / max(t_z3, t_cvc5)
        print(t_z3, t_cvc5,fitness)

    return (fitness,)
    #return ((t_z3 + t_cvc5) / 2),

# ===========================================================
# 4. Register GP operators
# ===========================================================

toolbox.register("evaluate", evaluate)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("mate", gp.cxOnePoint)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

# ===========================================================
# 5. Run Evolution
# ===========================================================

def main():
    population = toolbox.population(n=20)   # use smaller for testing
    hof = tools.HallOfFame(5)

    statistics = tools.Statistics(lambda smt: smt.fitness.values[0])
    statistics.register("avg", lambda fits: sum(fits) / len(fits))
    statistics.register("min", min)
    statistics.register("max", max)

    population, log = algorithms.eaSimple(
        population=population,
        toolbox=toolbox,
        cxpb=0.5,
        mutpb=0.4,
        ngen=30,
        stats=statistics,
        halloffame=hof,
        verbose=False
    )

    # def pretty_print_tree(tree):
    #     s = str(tree)
    #     s = s.replace("add", "+")
    #     s = s.replace("sub", "-")
    #     s = s.replace("mul", "*")
    #     s = s.replace("gt", ">")
    #     s = s.replace("lt", "<")
    #     s = s.replace("ge", ">=")
    #     s = s.replace("le", "<=")
    #     s = s.replace("eq", "==")
    #     return s

    print("Best individuals:")
    for smt in hof:
        #print(pretty_print_tree(smt))
        print(smt)
        print(smt.fitness.values)

    return population, log, hof

if __name__ == "__main__":
    main()





