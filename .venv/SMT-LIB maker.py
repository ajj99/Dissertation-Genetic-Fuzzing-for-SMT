from z3 import *
import subprocess
from z3 import Solver
import random
import time, datetime
from deap import base, creator, tools, gp, algorithms
from io import StringIO
import operator
import os
import csv

# ===========================================================
# 1. GP + Z3 Primitive Setup
# ===========================================================

NUM_VARS = 5
MAX_DEPTH = 6
timeout_seconds = 3

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
    try:
        if solver_cmd == "z3":
            proc = subprocess.run([solver_cmd, "-in"], input=smtlib_str, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds)
        elif solver_cmd == "cvc5":
            proc = subprocess.run([solver_cmd, "--lang", "smtlib2"], input=smtlib_str, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds)

        elif solver_cmd == "mathsat":
            proc = subprocess.run([solver_cmd, "-input=smt2"], input=smtlib_str, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_seconds)

        end = time.time()
        output = proc.stdout.strip().lower()

        if proc.returncode == 0:
            if "sat" in output or "unsat" in output:
                result = "intime"
                return end - start, result
            else: #"unknown", probably rare that branch is hit
                result = "timeoutOE"
                return timeout_seconds, result
        else:
            result = "subFailed"
            return -1, result

    except subprocess.TimeoutExpired:
        return timeout_seconds, "timeoutOE"


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
    logic_str = "(set-logic QF_NIA)\n"

    # Convert solver with assertions to SMT-LIB string
    smtlib_str = logic_str + s.to_smt2()

    t_z3, res_z3 = measure_runtime_subprocess_stdin(smtlib_str, "z3")
    t_cvc5, res_cvc5 = measure_runtime_subprocess_stdin(smtlib_str, "cvc5")
    t_mathsat, res_mathsat = measure_runtime_subprocess_stdin(smtlib_str, "mathsat")

    individual.z3_time = t_z3
    individual.cvc5_time = t_cvc5
    individual.mathsat_time = t_mathsat

    print(t_z3,t_cvc5,t_mathsat)

    if (res_z3 == "subFailed" or
        res_cvc5 == "subFailed" or
        res_mathsat == "subFailed"):

        individual.flag = "ERROR"
        print("ERROR FORMULA")
        return (0,)

    if (res_z3 == "timeoutOE" and
        res_cvc5 == "timeoutOE" and
        res_mathsat == "timeoutOE"):

        fitness = 200 # both timed out so give some reward and let it crossover
        individual.flag = "TO"
        return (fitness,)

    timeouts = [
        ("z3", res_z3, t_z3),
        ("cvc5", res_cvc5, t_cvc5),
        ("mathsat", res_mathsat, t_mathsat),
    ]

    timeout_solvers = [(name, t) for (name, res, t) in timeouts if res == "timeoutOE"]

    if len(timeout_solvers) == 1:
        # That solver is the time-out-of-stress (TOS)
        name, time = timeout_solvers[0]
        individual.TOS = {name}

        # min runtime among non-timeout solvers
        non_timeout_times = [t for (_, res, t) in timeouts if res == "intime"]
        fitness = 1000 + (timeout_seconds / min(non_timeout_times)) #should this be max?

        individual.flag = "TO"
        return (fitness,)

    if len(timeout_solvers) == 2:
        # The 1 non-timeout solver determines the “min time”
        non_timeout_time = next(t for (_, res, t) in timeouts if res == "intime")
        timeout_solvers_names = [name for (name, _) in timeout_solvers]

        individual.TOS = set(timeout_solvers_names)

        fitness = 1000 + (timeout_seconds / non_timeout_time)

        individual.flag = "TO"
        return (fitness,)


        # Fitness = relative difference between runtimes
    threshold = 0.1
    if max(t_z3, t_cvc5, t_mathsat) < threshold: #essentially ignore any SMT that run quickly on both
        fitness = 0.0
        individual.flag = "OK"
        return (fitness,)

    times = {
        "z3": t_z3,
        "cvc5": t_cvc5,
        "mathsat": t_mathsat,
    }

    slowest = max(times, key=times.get)
    fastest = min(times, key=times.get)

    difference = times[slowest] - times[fastest]

    if difference > 0.5: #deemed to run significantly slower
        individual.TOS = slowest

    fitness = difference / times[fastest]

    individual.TOS = set()
    individual.flag = "OK"
    return (fitness,)

# ===========================================================
# 4. Register GP operators
# ===========================================================

def cxOnePointWithTOS(ind1, ind2):
    tos1 = getattr(ind1, "TOS", set())
    tos2 = getattr(ind2, "TOS", set())

    # Only perform crossover if they share a struggling solver (TOS)
    if tos1.intersection(tos2):
        return gp.cxOnePoint(ind1, ind2)
    else:
        return ind1, ind2

toolbox.register("evaluate", evaluate)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("mate", cxOnePointWithTOS)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

def join(ind1, ind2):
    new_tree = ind1 + ind2
    new_ind = creator.IndividualSMT(new_tree)
    return new_ind

# ===========================================================
# 5. Run Evolution
# ===========================================================

def main():
    global timeout_seconds
    NGEN = 10
    POP_SIZE = 20
    # Initialize population and hall of fame
    population = toolbox.population(n=POP_SIZE)
    hof = tools.HallOfFame(5)

    # Set up statistics
    statistics = tools.Statistics(lambda smt: smt.fitness.values[0])
    statistics.register("avg", lambda fits: sum(fits) / len(fits))
    statistics.register("min", min)
    statistics.register("max", max)

    # Parameters
    cxpb = 0.6
    mutpb = 0.2
    jnpb = 0.2

    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals"] + statistics.fields

    # Evaluate initial population, each fitness starts as not valid as it hasn't been evaluated (new)
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    for ind in invalid_ind:
        ind.fitness.values = toolbox.evaluate(ind)

    # Remove any individuals which had solver return codes == 1
    population = [ind for ind in population if getattr(ind, "flag", None) != "ERROR"]

    record = statistics.compile(population)
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    print(logbook.stream)


    # Begin the generational loop
    for gen in range(1, NGEN + 1):

        num_TO = sum(1 for ind in population if getattr(ind, "flag", None) == "TO")

        # If MORE THAN HALF timeout → increase the timeout by 1 second
        if num_TO > len(population) / 2:
            timeout_seconds += 1
            print(f"More than half the population timed out at generation {gen}.")
            print(f"Increasing timeout to {timeout_seconds} seconds.")

        for ind in population:
            print(ind.flag, ind.fitness.values)

        # Store original population as parents
        parents = population

        # Apply crossover and mutation (internally clones)
        children = algorithms.varAnd(parents, toolbox, cxpb=cxpb, mutpb=mutpb)

        # Offspring is now (mutated/crossed) offspring + original parents
        offspring = parents + children

        # "Join" operator -> creates new individuals from parents
        joined_offspring = []
        for i in range(0, len(offspring) - 1, 2):
            if random.random() < jnpb:
                new_ind = join(offspring[i], offspring[i + 1])
                joined_offspring.append(new_ind)

        # Add any new (joined) individuals to the offspring
        offspring.extend(joined_offspring)

        # Keep only distinct trees after cloning, mutation, crossover and join
        seen = set()
        unique_offspring = []
        for ind in offspring:
            if id(ind) not in seen:  # use the object id
                seen.add(id(ind))
                unique_offspring.append(ind)
        offspring = unique_offspring

        # # Mark all cloned/offspring individuals as requiring reevaluation
        # for ind in offspring:
        #     ind.fitness.values = toolbox.evaluate(ind) # force invalid

        # Evaluate the individuals who don't have a fitness yet (new)
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid_ind:
            ind.fitness.values = toolbox.evaluate(ind)

        # Remove any individuals which had solver return codes == 1
        offspring = [ind for ind in offspring if getattr(ind, "flag", None) != "ERROR"]

        # Update the hall of fame with the generated individuals
        hof.update(offspring)

        # Select top POP_SIZE individuals for next generation
        offspring.sort(key=lambda ind: ind.fitness.values[0], reverse=True)
        population[:] = offspring[:POP_SIZE]

        # Record statistics
        record = statistics.compile(population)
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        print(logbook.stream)


    # Folder inside results/
    subfolder = f"{NGEN}gens_{POP_SIZE}pop_{NUM_VARS}vars_{MAX_DEPTH}depth_{jnpb}join_{mutpb}mut_{cxpb}cross_{timeout_seconds}to"
    folder_path = os.path.join("results", subfolder)

    # Create the subfolder if missing
    os.makedirs(folder_path, exist_ok=True)

    best_fitness = int(round((max(ind.fitness.values[0] for ind in hof))))
    for ind in hof:
        print(ind.fitness.values)

    # Timestamped file
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{best_fitness}_{timestamp}.csv"
    file_path = os.path.join(folder_path, filename)

    with open(file_path,"w",newline="",encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["formula", "fitness", "z3", "cvc5","mathsat"])
        for ind in hof:
            writer.writerow([
                str(ind),
                ind.fitness.values[0],
                getattr(ind, "z3_time", None),
                getattr(ind, "cvc5_time", None),
                getattr(ind, "mathsat_time", None)
            ])

    print(f"Hall of Fame saved to {file_path}")

    # print("Best individuals:")
    # for smt in hof:
    #     print(smt)
    #     print(smt.fitness.values)
    #     print(smt.z3_time, smt.cvc5_time, smt.mathsat_time)
        #print runtimes here to store


def rerun_query():
    smt_query = """(set-logic QF_NIA)
(declare-fun x3 () Int)
(declare-fun x4 () Int)
(declare-fun x1 () Int)
(declare-fun x0 () Int)
(declare-fun x2 () Int)
(assert
 (let ((?x184 (* (* (* x2 x0) (* x3 x1)) (* (* x4 x4) (+ x3 x3)))))
(let ((?x73 (* (* (* x2 x4) (+ x0 x1)) (* (+ x2 x3) (* x0 x2)))))
(< ?x73 ?x184))))
(check-sat)

"""

    start_time = time.perf_counter()

    result = subprocess.run(
        ["cvc5", "--lang", "smt2"],
        # ["z3","--in"],
        input=smt_query,
        text=True,
        capture_output=True,
        timeout=3
    )

    end_time = time.perf_counter()
    runtime = end_time - start_time

    print("CVC5 Output:")
    print(result.stdout.strip())
    if result.stderr:
        print("Errors:", result.stderr.strip())

    print(f"Runtime: {runtime:.6f} seconds")

if __name__ == "__main__":
    #rerun_query()
    main()





