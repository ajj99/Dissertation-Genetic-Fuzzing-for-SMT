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

creator.create("RunTimeFitness", base.Fitness, weights=(1.0,))
creator.create("IndividualSMT", gp.PrimitiveTree, fitness=creator.RunTimeFitness)

def DEAP_setup(NUM_VARS, MAX_DEPTH):
    global toolbox, pset
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

    toolbox = base.Toolbox()
    toolbox.register("expr", gp.genFull, pset=pset, min_=1, max_=MAX_DEPTH, type_=BoolRef)
    toolbox.register("individual", tools.initIterate, creator.IndividualSMT, toolbox.expr)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    toolbox.register("evaluate", evaluate)
    toolbox.register("select", tools.selTournament, tournsize=3)
    toolbox.register("mate", cxOnePointWithTOS)
    toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
    toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

# ===========================================================
# 3. Evaluation and Solving
# ===========================================================

def measure_runtime_subprocess_stdin(smtlib_str, solver_cmd, timeout_seconds):

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


def evaluate(individual, NUM_VARS, timeout_seconds):
    # Compile DEAP expression
    #print(individual)
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

    #print(smtlib_str)
    individual.smtlib_str = smtlib_str

    t_z3, res_z3 = measure_runtime_subprocess_stdin(smtlib_str, "z3", timeout_seconds)
    t_cvc5, res_cvc5 = measure_runtime_subprocess_stdin(smtlib_str, "cvc5", timeout_seconds)
    t_mathsat, res_mathsat = measure_runtime_subprocess_stdin(smtlib_str, "mathsat", timeout_seconds)

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

        individual.fastest_runtime = min(non_timeout_times)
        individual.flag = "TO"
        return (fitness,)

    if len(timeout_solvers) == 2:
        # The 1 non-timeout solver determines the “min time”
        non_timeout_time = next(t for (_, res, t) in timeouts if res == "intime")
        timeout_solvers_names = [name for (name, _) in timeout_solvers]

        individual.TOS = set(timeout_solvers_names)

        fitness = 1000 + (timeout_seconds / non_timeout_time)

        individual.fastest_runtime = non_timeout_time
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
    individual.fastest_runtime = times[fastest]
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


def join(ind1, ind2):
    new_tree = ind1 + ind2
    new_ind = creator.IndividualSMT(new_tree)
    return new_ind

# ===========================================================
# 5. Run Evolution
# ===========================================================

GLOBAL_CSV = "all_fuzzer_results.csv"

def init_global_csv():
    if not os.path.exists(GLOBAL_CSV):
        with open(GLOBAL_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "POP_SIZE",
                "NGEN",
                "NUM_VARS",
                "MAX_DEPTH",
                "joinpb",
                "mutpb",
                "crosspb",
                "fitness",
                "formula",
                "solver",
                "runtime",
                "diff_from_fastest"
            ])


def main():
    init_global_csv()
    timeout_seconds = 3

    POP_SIZE_LIST   = [20, 50]
    NGEN_LIST       = [10, 20]
    NUM_VARS_LIST   = [4, 5]
    MAX_DEPTH_LIST  = [5, 6]
    JOINPB_LIST     = [0.2, 0.4]
    MUTPB_LIST      = [0.2, 0.4]
    CROSSPB_LIST    = [0.2, 0.4]

    for pop in POP_SIZE_LIST:
        for ngen in NGEN_LIST:
            for num_vars in NUM_VARS_LIST:
                for max_depth in MAX_DEPTH_LIST:
                    for joinpb in JOINPB_LIST:
                        for mutpb in MUTPB_LIST:
                            for crosspb in CROSSPB_LIST:

                                print("\n===================================================")
                                print(f"Running fuzzer with parameters:")
                                print(f"POP_SIZE   = {pop}")
                                print(f"NGEN       = {ngen}")
                                print(f"NUM_VARS   = {num_vars}")
                                print(f"MAX_DEPTH  = {max_depth}")
                                print(f"joinpb     = {joinpb}")
                                print(f"mutpb      = {mutpb}")
                                print(f"crosspb    = {crosspb}")
                                print("===================================================\n")

                                DEAP_setup(num_vars, max_depth)
                                run_fuzzer(
                                    POP_SIZE=pop,
                                    NGEN=ngen,
                                    NUM_VARS=num_vars,
                                    MAX_DEPTH=max_depth,
                                    jnpb=joinpb,
                                    mutpb=mutpb,
                                    cxpb=crosspb
                                )



def run_fuzzer(POP_SIZE, NGEN, NUM_VARS, MAX_DEPTH, jnpb, mutpb, cxpb):
    timeout_seconds = 3

    #NGEN = 10
    #POP_SIZE = 20
    # Initialize population and hall of fame
    population = toolbox.population(n=POP_SIZE)
    hof = tools.HallOfFame(5)

    # Set up statistics
    statistics = tools.Statistics(lambda smt: smt.fitness.values[0])
    statistics.register("avg", lambda fits: sum(fits) / len(fits))
    statistics.register("min", min)
    statistics.register("max", max)

    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals"] + statistics.fields

    # Evaluate initial population, each fitness starts as not valid as it hasn't been evaluated (new)
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    for ind in invalid_ind:
        ind.fitness.values = toolbox.evaluate(ind, NUM_VARS, timeout_seconds)

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

        # Store original population as parents
        parents = population

        # Apply crossover and mutation (internally clones)
        children = algorithms.varAnd(parents, toolbox, cxpb=cxpb, mutpb=mutpb)

        # Offspring is now (mutated/crossed) offspring + original parents
        join_pool = parents + children

        # "Join" operator -> creates new individuals from parents
        joined_offspring = []
        for i in range(0, len(join_pool) - 1, 2):
            if random.random() < jnpb:
                new_ind = join(join_pool[i], join_pool[i + 1])
                joined_offspring.append(new_ind)

        offspring = parents + children + joined_offspring

        for ind in children + joined_offspring:
            del ind.fitness.values  # marks them as invalid

        # Keep only distinct trees after cloning, mutation, crossover and join
        seen = set()
        unique_offspring = []
        for ind in offspring:
            tree_str = str(ind)
            if tree_str not in seen:  # use the object id
                seen.add(tree_str)
                unique_offspring.append(ind)
            # else:
            #     print("FOUND DUPLICATE")

        offspring = unique_offspring

        # # # Mark all cloned/offspring individuals as requiring reevaluation
        # for ind in offspring:
        #     ind.fitness.values = toolbox.evaluate(ind, NUM_VARS, timeout_seconds) # force invalid

        # Evaluate the individuals who don't have a fitness yet (new)
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        for ind in invalid_ind:
            ind.fitness.values = toolbox.evaluate(ind, NUM_VARS, timeout_seconds)

        # Remove any individuals which had solver return codes == 1
        offspring = [ind for ind in offspring if getattr(ind, "flag", None) != "ERROR"]

        # Update the hall of fame with the generated individuals
        hof.update(offspring)

        # Select top POP_SIZE individuals for next generation
        offspring.sort(key=lambda ind: ind.fitness.values[0], reverse=True)
        population[:] = offspring[:POP_SIZE]

        for ind in population:
            print(ind.flag, ind.fitness.values)

        # Record statistics
        record = statistics.compile(population)
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        print(logbook.stream)

    best_ind = max(hof, key=lambda ind: ind.fitness.values[0])
    best_formula = str(best_ind)
    best_fitness = best_ind.fitness.values[0]

    # Determine struggle solver
    tos = getattr(best_ind, "TOS", None)

    if isinstance(tos, set):
        struggle_solver = list(tos)[0] if tos else "None"
    else:
        struggle_solver = tos

    print(f"Struggle solver selected: {struggle_solver}")

    smt_query = getattr(best_ind, "smtlib_str", None)
    # Re-run on struggle solver with 10 min timeout
    if tos and smt_query:
        long_timeout_runtime, _ = measure_runtime_subprocess_stdin(smt_query, struggle_solver, 600)
        print(f"10-minute timeout runtime: {long_timeout_runtime} sec")

        # Compute difference from fastest
        fastest = getattr(best_ind, "fastest_runtime", None)
        if fastest is not None:
            diff = long_timeout_runtime - fastest
        else:
            diff = 0
    else:
        diff = 0
        long_timeout_runtime = 0

    # Append one row to global CSV
    timestamp = datetime.datetime.now().isoformat()

    with open(GLOBAL_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            POP_SIZE,
            NGEN,
            NUM_VARS,
            MAX_DEPTH,
            jnpb,
            mutpb,
            cxpb,
            best_fitness,
            best_formula,
            struggle_solver,
            long_timeout_runtime,
            diff
        ])

    print(f"Logged run to {GLOBAL_CSV}")

if __name__ == "__main__":
    main()




