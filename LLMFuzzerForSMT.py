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
import numpy as np
from collections import Counter
from openai import OpenAI

# Generate a random seed (1–10,000 is more than enough for 5–10 runs)
SEED = random.randint(1, 10_000)
successful_mutation = 0
total_mutations = 0
successful_crossover = 0
total_crossovers = 0

# Seed all randomness
random.seed(SEED)
np.random.seed(SEED)

# OpenAI setup

client = OpenAI()

def call_LLM(prompt):
    """Send prompt to LLM and return the text."""
    response = client.chat.completions.create(
        model="gpt-4o",  # or your model from Uni of Edinburgh
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        timeout=60
    )
    #print("TOTAL TOKENS USED:", response.usage.total_tokens)
    return response.choices[0].message.content.strip()

# GP + Z3 Primitive Setup

creator.create("RunTimeFitness", base.Fitness, weights=(1.0,))
creator.create("IndividualSMT", gp.PrimitiveTree, fitness=creator.RunTimeFitness)

def DEAP_setup(NUM_VARS, MAX_DEPTH):
    global toolbox, pset, pset_join
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

    # Terminals
    pset.addTerminal(BoolVal(True), BoolRef)
    pset.addTerminal(BoolVal(False), BoolRef)

    pset_join = copy.deepcopy(pset)
    pset_join.addPrimitive(lambda x, y: x & y, [BoolRef, BoolRef], BoolRef, name="and_")

    # DEAP individual and population setup

    toolbox = base.Toolbox()
    toolbox.register("expr", gp.genFull, pset=pset, min_=1, max_=MAX_DEPTH, type_=BoolRef)
    toolbox.register("individual", tools.initIterate, creator.IndividualSMT, toolbox.expr)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    toolbox.register("evaluate", evaluate)
    toolbox.register("select", tools.selTournament, tournsize=3)
    toolbox.register("mate", cxLLM) # for LLM crossover, replace with cxOnePointWithTOS() otherwise
    toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
    toolbox.register("mutate", mutLLM, num_vars = NUM_VARS) # for LLM mutation, replace with mutUniform() otherwise

# Evaluation and Solving


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
                return end - start, result, output
            else:  # "unknown", probably rare that branch is hit
                result = "timeoutOE"
                return timeout_seconds, result, output
        else:
            result = "subFailed"
            return -1, result, output

    except subprocess.TimeoutExpired:
        return timeout_seconds, "timeoutOE", "unknown"


def evaluate(individual, NUM_VARS, timeout_seconds):
    # Compile DEAP expression

    func = gp.compile(expr=individual, pset=pset_join)

    # Create Z3 variables
    vars_z3 = [Int(f"x{i}") for i in range(NUM_VARS)]

    # Build Z3 formula
    z3_formula = func(*vars_z3)
    if isinstance(z3_formula, bool):
        z3_formula = BoolVal(z3_formula)

    # Use a Z3 solver to collect all assertions
    s = Solver()
    s.add(z3_formula)

    # Manually set logic (example: QF_LIA)
    logic_str = "(set-logic QF_NIA)\n"

    # Convert solver with assertions to SMT-LIB string
    smtlib_str = logic_str + s.to_smt2()
    individual.smtlib_str = smtlib_str

    t_z3, res_z3, status_z3 = measure_runtime_subprocess_stdin(smtlib_str, "z3", timeout_seconds)
    t_cvc5, res_cvc5, status_cvc5 = measure_runtime_subprocess_stdin(smtlib_str, "cvc5", timeout_seconds)
    t_mathsat, res_mathsat, status_mathsat = measure_runtime_subprocess_stdin(smtlib_str, "mathsat", timeout_seconds)


    if (res_z3 == "subFailed" or
        res_cvc5 == "subFailed" or
        res_mathsat == "subFailed"):

        individual.flag = "ERROR"
        print("ERROR FORMULA")
        return (0,)

    if (res_z3 == "timeoutOE" and
        res_cvc5 == "timeoutOE" and
        res_mathsat == "timeoutOE"):
        individual.TOS = {"z3", "cvc5", "mathsat"}
        fitness = 200 # all timed out so give some reward and let it crossover
        individual.flag = "TO"
        return (fitness,)

    timeouts = [
        ("z3", res_z3, t_z3),
        ("cvc5", res_cvc5, t_cvc5),
        ("mathsat", res_mathsat, t_mathsat),
    ]

    timeout_solvers = [(name, t) for (name, res, t) in timeouts if res == "timeoutOE"]

    if len(timeout_solvers) == 1:
        # That solver is the time-out solver (TOS)
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
        individual.TOS = {slowest}
    else:
        individual.TOS = set()

    fitness = difference / times[fastest]

    individual.flag = "OK"
    individual.fastest_runtime = times[fastest]
    return (fitness,)

# Register GP operators

# def cxOnePointWithTOS(ind1, ind2):
#     tos1 = getattr(ind1, "TOS", set())
#     tos2 = getattr(ind2, "TOS", set())
#
#     # Only perform crossover if they share a struggling solver (TOS)
#     if tos1.intersection(tos2):
#         return gp.cxOnePoint(ind1, ind2)
#     else:
#         return ind1, ind2

def cxLLM(ind1, ind2):
    global successful_crossover
    global total_crossovers
    prompt = f"""
        You are an SMT crossover operator aiming to create HARD formula (formula that take SMT solver a long time to solve)

        Given these 2 DEAP PrimitiveTree individuals:

        {ind1}, {ind2}
        Here is the Primitive Set (pset) definition:

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

        Produce a crossover using only the 2 individuals provided by picking a node on each of the individuals and swapping the subtrees beneath that node.
        Aim to make this crossover such that it will make the two resulting trees significantly harder for an SMT solver to solve.
        Do NOT introduce any new material at all, simply perform the crossover (such that the summed lengths of the formula before and after are identical)
        Choose this crossover point in a way such that the two resulting trees represent syntactically valid SMT formula (in DEAP format).

        Rules:
        - Output ONLY the formula, nothing else. and, or, nand, etc. are NOT permitted. Use only primitives provided in the set above
        - The root operator remains a Boolean expression and the operands of this must evaluate to the same type to prevent type errors.
        - Do NOT include any Markdown code fences like ```smt``` or ``` or any other annotations.
        - THIS IS IMPORTANT: Place a <SEP> token (formatted exactly like that) between the end of the first tree output and the start of the second so I can parse them easily.

        """
    output = call_LLM(prompt)
    total_crossovers += 1

    try:
        new_pt1, new_pt2 = output.split("<SEP>", 1)
        new_ind1 = gp.PrimitiveTree.from_string(new_pt1.strip(), pset)
        new_ind2 = gp.PrimitiveTree.from_string(new_pt2.strip(), pset)

    except Exception:
        return ind1, ind2

    if no_new_material(ind1, ind2, new_ind1, new_ind2):
        child1 = creator.IndividualSMT(new_ind1)
        child2 = creator.IndividualSMT(new_ind2)
        successful_crossover +=1

        return child1, child2

    return ind1, ind2


def count_primitives(tree):
    """
    Count only the primitives (operators) in a DEAP PrimitiveTree.
    Terminals / ARGs are ignored.
    Returns a Counter {primitive_name: count}.
    """
    counts = Counter()
    for node in tree:
        if isinstance(node, gp.Primitive):
            counts[node.name] += 1
    return counts


def no_new_material(parent1, parent2, child1, child2):
    """
    Returns True if the combined counts of operators in children
    EXACTLY match the counts in parents.
    Ignores leaf terminals (ARG0, ARG1, constants).
    """
    parent_counts = count_primitives(parent1) + count_primitives(parent2)
    child_counts = count_primitives(child1) + count_primitives(child2)

    # Must be exactly equal
    return parent_counts == child_counts


def mutLLM(ind, num_vars):
    global successful_mutation
    global total_mutations
    prompt = f"""
    You are an SMT mutation operator aiming to create HARD formula (formula that take SMT solver a long time to solve)

    Given this DEAP PrimitiveTree individual:

    {ind}
    Here is the Primitive Set (pset) definition:

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

    Produce a mutation using primitives defined in the pset (i.e only add, sub, mul), you may introduce new variables in the form of ARGx where x is a number up to {num_vars - 1}.
    Aim to make this mutation such that it will make the expression significantly harder for an SMT solver to solve, but do NOT mutate the root operator and only mutate one side (subtree) of the root.
    Do NOT use comparison operators (le, ge, eq, gt, lt) as children of other comparisons or arithmetic operators.
    Output ONLY the mutated formula in DEAP format so I can parse it straight back into DEAP.

    Rules:
    - Output ONLY the formula, nothing else. and, or, nand, etc. are NOT permitted. Use only primitives provided in the set above
    - The root operator gives a Boolean expression and the operands of this must evaluate to the same type to prevent type errors.
    - Do NOT include any Markdown code fences like ```smt``` or ``` or any other annotations.

    """

    total_mutations +=1
    try:
        mutated_str = call_LLM(prompt)
    except Exception as e:
        return (ind,)

    try:
        tree = gp.PrimitiveTree.from_string(mutated_str, pset)
    except Exception:
        return (ind,)

    # Root operator unchanged
    if tree[0].name != ind[0].name:
        return (ind, )

    # ARG bounds check
    for node in tree:
        if node.name.startswith("ARG"):
            idx = int(node.name[3:])
            if idx >= num_vars:
                return (ind,)

    # At least one subtree changed
    if str(tree) == str(ind):
        return (ind,)

    try:
        func = gp.compile(tree, pset)
        if not isinstance(func(*([0] * num_vars)), bool):
            return (ind,)
    except Exception:
        return (ind,)

    successful_mutation+=1
    return (creator.IndividualSMT(tree),)

def join(ind1, ind2):
    new_ind = gp.PrimitiveTree.from_string(
        f"and_({ind1}, {ind2})", pset_join)

    return creator.IndividualSMT(new_ind)


# Run Evolution

GLOBAL_CSV = f"Tests_FuzzerLLMCrossoverAndMutation.csv"

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
                "timeout",
                "fitness",
                "formula",
                "solver",
                "runtime",
                "diff_from_fastest"
            ])

# GLOBAL_CSV = "Tests_FitnessProgressLLM.csv"
#
# def init_global_csv():
#     if not os.path.exists(GLOBAL_CSV):
#         with open(GLOBAL_CSV, "w", newline="", encoding="utf-8") as f:
#             writer = csv.writer(f)
#             writer.writerow([
#                     "generation",
#                     "nevals",
#                     "min",
#                     "avg",
#                     "max"
#                 ])


def main():
    init_global_csv()
    global total_crossovers
    global total_mutations
    global successful_crossover
    global successful_mutation

    # ---- Default values ----
    DEFAULT_POP_SIZE = 25
    DEFAULT_GEN_SIZE = 30
    DEFAULT_NUM_VARS = 5
    DEFAULT_MAX_DEPTH = 5
    DEFAULT_JOIN_PB = 0.0
    DEFAULT_MUTATE_PB = 0.4
    DEFAULT_CROSSOVER_PB = 0.4
    DEFAULT_TIMEOUT_SECONDS = 5

    # # ---- Two variation values for each parameter ----
    # POP_SIZE_LIST   = [10, 30]
    # NGEN_LIST       = [10, 30]
    # NUM_VARS_LIST   = [3, 5]
    # MAX_DEPTH_LIST  = [4, 6]
    # JOINPB_LIST     = [0.0, 0.4]
    # MUTPB_LIST      = [0.0, 0.4]
    # CROSSPB_LIST    = [0.0, 0.8]
    # TIMEOUT_LIST    = [1, 10]

    # # ---- Two variation values for each parameter ----
    # POP_SIZE_LIST   = [15, 25]
    # NGEN_LIST       = [15, 25]
    # NUM_VARS_LIST   = []
    # MAX_DEPTH_LIST  = []
    # JOINPB_LIST     = [0.1, 0.3]
    # MUTPB_LIST      = [0.1, 0.3]
    # CROSSPB_LIST    = [0.2, 0.4]
    # TIMEOUT_LIST    = [5]
    # -------------------------------------------------
    # Run the BASELINE experiment
    # -------------------------------------------------
    print("\n================ BASELINE EXPERIMENT ================")
    DEAP_setup(DEFAULT_NUM_VARS, DEFAULT_MAX_DEPTH)

    for i in range(3):
        run_fuzzer(
            POP_SIZE=DEFAULT_POP_SIZE,
            NGEN=DEFAULT_GEN_SIZE,
            NUM_VARS=DEFAULT_NUM_VARS,
            MAX_DEPTH=DEFAULT_MAX_DEPTH,
            jnpb=DEFAULT_JOIN_PB,
            mutpb=DEFAULT_MUTATE_PB,
            cxpb=DEFAULT_CROSSOVER_PB,
            timeout_seconds=DEFAULT_TIMEOUT_SECONDS
        )

    # -------------------------------------------------
    # 2. Run 16 single-parameter experiments
    # For each parameter:
    #   - replace default with low value
    #   - replace default with high value
    # -------------------------------------------------

    # experiments = [
    #     ("POP_SIZE", POP_SIZE_LIST, "POP_SIZE"),
    #     ("NGEN", NGEN_LIST, "NGEN"),
    #     ("NUM_VARS", NUM_VARS_LIST, "NUM_VARS"),
    #     ("MAX_DEPTH", MAX_DEPTH_LIST, "MAX_DEPTH"),
    #     #("JOIN_PB", JOINPB_LIST, "jnpb"),
    #     ("MUTATE_PB", MUTPB_LIST, "mutpb"),
    #     ("CROSSOVER_PB", CROSSPB_LIST, "cxpb"),
    #     ("TIMEOUT", TIMEOUT_LIST, "timeout_seconds"),
    # ]
    #
    # for param_name, param_values, arg_key in experiments:
    #
    #     for val in param_values:
    #
    #         # Start from defaults and override ONE parameter
    #         args = {
    #             "POP_SIZE": DEFAULT_POP_SIZE,
    #             "NGEN": DEFAULT_GEN_SIZE,
    #             "NUM_VARS": DEFAULT_NUM_VARS,
    #             "MAX_DEPTH": DEFAULT_MAX_DEPTH,
    #             #"jnpb": DEFAULT_JOIN_PB,
    #             "mutpb": DEFAULT_MUTATE_PB,
    #             "cxpb": DEFAULT_CROSSOVER_PB,
    #             "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
    #         }
    #
    #         args[arg_key] = val  # override just one parameter
    #
    #         print("\n================ PARAMETER SWEEP ==================")
    #         print(f"Varying {param_name}, using {val}")
    #         print("Arguments:", args)
    #         print("===================================================\n")
    #
    #         DEAP_setup(args["NUM_VARS"], args["MAX_DEPTH"])
    #         run_fuzzer(**args)

    # with open(GLOBAL_CSV, "a", encoding="utf-8") as f:
    #     f.write(f"\nSeed: {SEED}\n")

    with open(GLOBAL_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([])

def run_fuzzer(POP_SIZE, NGEN, NUM_VARS, MAX_DEPTH, jnpb, mutpb, cxpb, timeout_seconds):
    global successful_mutation
    global successful_crossover
    global total_mutations
    global total_crossovers
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

        offspring = unique_offspring


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
        struggle_solver = list(tos)

        print(f"Struggle solver selected: {struggle_solver}")

    smt_query = getattr(best_ind, "smtlib_str", None)

    # Re-run on struggle solver with 10 min timeout

    if tos and smt_query:
        results = []

        for solver in struggle_solver:
            long_timeout_runtime, _, best_ind.status = measure_runtime_subprocess_stdin(smt_query, solver, 600)
            print(f"10-minute timeout runtime: {long_timeout_runtime} sec on {solver}")

            # Compute difference from fastest
            fastest = getattr(best_ind, "fastest_runtime", None)
            if fastest is not None:
                diff = (long_timeout_runtime - fastest) / fastest
            else:
                diff = 0

            results.append((solver, long_timeout_runtime, diff))

        struggle_solver, long_timeout_runtime, diff = max(results, key=lambda x: x[2])

    else:
        struggle_solver = None
        diff = 0
        long_timeout_runtime = 0

    status = getattr(best_ind, "status", None)

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
            timeout_seconds,
            best_fitness,
            best_formula,
            struggle_solver,
            long_timeout_runtime,
            diff,
            status
        ])

    # with open(GLOBAL_CSV, "a", newline="", encoding="utf-8") as f:
    #     writer = csv.writer(f)
    #     for record in logbook:
    #         writer.writerow([
    #             record["gen"],
    #             record["nevals"],
    #             record["min"],
    #             record["avg"],
    #             record["max"]
    #         ])


def is_well_formed_deap(expr_str, pset, num_vars):
    try:
        tree = gp.PrimitiveTree.from_string(expr_str, pset)
        func = gp.compile(tree, pset)

        # Type-safe dummy execution
        dummy_vars = [Int(f"x{i}") for i in range(num_vars)]
        func(*dummy_vars)

        return True
    except Exception:
        return False

if __name__ == "__main__":
    main()

