from z3 import *
import random
from deap import base, creator, tools, gp, algorithms
import operator
import math

# # Configuration
NUM_VARS = 5  # number of integer variables
NUM_ASSERTS = 2  # number of assertions
MAX_DEPTH = 3 # maximum depth of nested expressions
#

#https://deap.readthedocs.io/en/master/tutorials/basic/part2.html

pset = gp.PrimitiveSetTyped("MAIN", [ArithRef]*NUM_VARS, BoolRef)

pset.addPrimitive(lambda x, y: x + y, [ArithRef, ArithRef], ArithRef, name="add")
pset.addPrimitive(lambda x, y: x - y, [ArithRef, ArithRef], ArithRef, name="sub")
pset.addPrimitive(lambda x, y: x * y, [ArithRef, ArithRef], ArithRef, name="mul")

pset.addPrimitive(lambda x, y: x > y, [ArithRef, ArithRef], BoolRef, name="gt")
pset.addPrimitive(lambda x, y: x < y, [ArithRef, ArithRef], BoolRef, name="lt")
pset.addPrimitive(lambda x, y: x >= y, [ArithRef, ArithRef], BoolRef, name="ge")
pset.addPrimitive(lambda x, y: x <= y, [ArithRef, ArithRef], BoolRef, name="le")
pset.addPrimitive(lambda x, y: x == y, [ArithRef, ArithRef], BoolRef, name="eq")

pset.addEphemeralConstant("rand100", lambda: random.randint(0, 100), ArithRef)

pset.addTerminal(True, BoolRef)
pset.addTerminal(False, BoolRef)

#creator.create defines new classes at runtime which inherit from existing python types e.g base.Fitness
creator.create("RunTimeFitness", base.Fitness, weights = (1.0,))
creator.create("IndividualSMT", gp.PrimitiveTree, fitness = creator.RunTimeFitness)

toolbox = base.Toolbox()

#toolbox.register is used to name and store functions with preset arguments so they can be called easily

#expr generates a random GP tree
toolbox.register("expr", gp.genFull, pset=pset, min_=1, max_=MAX_DEPTH)

#individual wraps that tree in an Individual object with fitness
toolbox.register("individual", tools.initIterate, creator.IndividualSMT, toolbox.expr)

#population creates n individuals to form the GP population
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

def eval_individualSMT(individual):
    #compile GP tree into callable function
    func = gp.compile(expr=individual, pset=pset)

    #create z3 integer vars
    z3_variables = [Int(f"x{i}") for i in range(NUM_VARS)]
    #z3 variables = [x0, x1]

    #initialise a z3 solver
    z3_solver = Solver()
    z3_solver.set("timeout", 100000)
    #for _ in range(NUM_ASSERTS) <- can add multiple constraints into one individual
    #typically one constraint per individual

    #evaluate GP expression with list (*) of z3 variables
    #z3_expr = func(Int("x0"), Int("x1"), Int("x2"))
    z3_expr = func(*z3_variables)
    #z3_expr = x0 - x1 + 7

    z3_solver.add(z3_expr)

    #measure how long z3 takes
    import time
    start = time.time()
    z3_solver.check()
    end = time.time()
    solve_time = end - start

    #return fitness
    return (solve_time, )

#these act as direct aliases i.e. when toolbox.evaluate is called run eval_.. function
toolbox.register("evaluate", eval_individualSMT)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("mate", gp.cxOnePoint)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

#gp loop
def main():

    #random.seed(22)

    population = toolbox.population(n=1000)
    hof = tools.HallOfFame(5)

    statistics = tools.Statistics(lambda smt: smt.fitness.values[0])
    statistics.register("avg", lambda fits: sum(fits) / len(fits))
    statistics.register("min", min)
    statistics.register("max", max)

    population, log = algorithms.eaSimple(
        population = population,
        toolbox = toolbox,
        cxpb = 0.5,
        mutpb = 0.2,
        ngen = 3,
        stats = statistics,
        halloffame = hof,
        verbose = False
    )

    def pretty_print_tree(tree):
        # Convert DEAP PrimitiveTree to string
        s = str(tree)

        # Replace DEAP primitive names with symbols
        s = s.replace("add", "+")
        s = s.replace("sub", "-")
        s = s.replace("mul", "*")
        s = s.replace("gt", ">")
        s = s.replace("lt", "<")
        s = s.replace("ge", ">=")
        s = s.replace("le", "<=")
        s = s.replace("eq", "==")

        return s

    # Print Hall of Fame
    print("Best individuals:")
    for smt in hof:
        print(pretty_print_tree(smt))
        print(smt.fitness.values)

    return population, log, hof

if __name__ == "__main__":
    main()