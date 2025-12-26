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
from openai import OpenAI

# ===========================================================
# 1. OpenAI Setup
# ===========================================================

client = OpenAI()

def call_LLM(prompt):
    """Send prompt to LLM and return the text."""
    response = client.chat.completions.create(
        model="gpt-4o",  # or your model from Uni of Edinburgh
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    #print("TOTAL TOKENS USED:", response.usage.total_tokens)
    return response.choices[0].message.content.strip()

# ge(add(ARG0, ARG3), add(ARG2, ARG2)) <--- print(individual) <- stored like this by DEAP

# x0 + x3 >= x2 + x2 <--- print(z3 representation) -> the best way for LLM to output? can easily add logic and s.to_smt2(), made by gp.compile

# (set-logic QF_NIA) <--- print(gp_tree_to_smt(individual)), made adding converting z3 representation into smt-lib with s.to_smt2 and adding logic at the top
# ; benchmark generated from python API
# (set-info :status unknown)
# (declare-fun x2 () Int)
# (declare-fun x3 () Int)
# (declare-fun x0 () Int)
# (assert
#  (>= (+ x0 x3) (+ x2 x2)))
# (check-sat)

# ===========================================================
# 2. GP + Z3 Primitive Setup
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
    toolbox.register("mate", gp.cxOnePoint) #change this later
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


def gp_tree_to_smt(individual):
    """Convert DEAP GP tree into an SMT-LIB formula string."""
    func = gp.compile(expr=individual, pset=pset)
    vars_z3 = [Int(f"x{i}") for i in range(4)]
    z3_formula = func(*vars_z3)
    if isinstance(z3_formula, bool):
        z3_formula = BoolVal(z3_formula)

    s = Solver()
    s.add(z3_formula)

    smt_str = "(set-logic QF_NIA)\n" + s.to_smt2()
    return smt_str

def evaluate(individual, NUM_VARS, timeout_seconds):
    # Convert solver with assertions to SMT-LIB string
    smtlib_str = gp_tree_to_smt(individual)

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

def llm_mutate(individual):
    smt_formula = gp_tree_to_smt(individual)

    prompt = f"""
    You are an SMT mutation operator for genetic programming.
    
    Given this SMT-LIB formula:
    
    {smt_formula}
    
    Produce a SMALL mutation of the formula using the SAME variable names x0..x4.
    Output the mutated formula **translated into the DEAP GP tree format** like:
    
    ['gt', ['add', 'x0', 'x1'], ['mul', 'x2', 'x3']]
    
    Rules:
    - Use only these primitives: add, sub, mul, gt, lt, ge, le, eq.
    - Use variables x0..x4 (no new ones).
    - Keep mutation minimal (change 1–2 small elements).
    - Output ONLY the Python list for the mutated GP tree.
    """

    mutated_tree = call_LLM(prompt)
    #figure out what we're getting back here

def llm_crossover(f1: str, f2: str):
    prompt = f"""
    You are an SMT crossover operator.
    
    Given two SMT-LIB formulas, produce a *single new formula* that is
    syntactically valid and merges sub-expressions from both parents.
    
    Rules:
    - Combine at least one sub-expression from each parent.
    - Do not rewrite either formula entirely.
    - Keep the output valid SMT-LIB 2.0.
    - Output ONLY the new formula.
    
    Parent A:
    {f1}
    
    Parent B:
    {f2}
    """
    mutated_tree = call_LLM(prompt)
    #figure out what we're getting back here

def join(ind1, ind2):
    new_tree = ind1 + ind2
    new_ind = creator.IndividualSMT(new_tree)
    return new_ind

# ===========================================================
# 5. Run Evolution
# ===========================================================

GLOBAL_CSV = "LLM_fuzzer_results.csv"

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
        parents = population #

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

def is_well_formed_z3(expr_str, num_vars):
    try:
        vars_z3 = {f"x{i}": Int(f"x{i}") for i in range(num_vars)}

        expr = eval(expr_str, {}, vars_z3)

        if not isinstance(expr, BoolRef):
            return False

        s = Solver()
        s.add(expr)  # type check happens here
        return True
    except Exception:
        return False



def test_llm_mutation():
    # could we potentially add in the struggle solver to the prompt to help mutation/crossover?
    NUM_VARS = 4
    MAX_DEPTH = 5
    RUNS = 100
    well_formed_smtlib = 0 #100,100, 100,100, 100 (vars4,depth3)
    error_smtlib = []
    well_formed_z3 = 0 #96,99, 100,100,100
    error_z3 = []
    well_formed_deap = 0 #98,98, 97,100,100
    error_deap = []

    # Setup DEAP GP with your primitives, terminals, and variables
    DEAP_setup(NUM_VARS, MAX_DEPTH)

    for i in range(RUNS):
        # Create a single individual
        ind = toolbox.individual()
        #print("Original individual (DEAP GP tree):")
        print("\nOriginal DEAP representation:")
        print(ind)

        # Convert to Z3 representation
        vars_z3 = [Int(f"x{i}") for i in range(NUM_VARS)]
        func = gp.compile(expr=ind, pset=pset)
        z3_expr = func(*vars_z3)
        # print("\nOriginal Z3 representation:")
        # print(z3_expr)

        # Convert to SMT-LIB string
        smtlib_str = gp_tree_to_smt(ind)
        # print("\nOriginal SMT-LIB representation:")
        # print(smtlib_str)

        # Prompt LLM for Z3-style mutation
        prompt_z3 = f"""
    You are an SMT mutation operator.
    
    Given this Z3-style formula:
    
    {z3_expr}
    
    Produce a mutation using only variables specified in the input expression and primitives +, -, *, >, <, >=, <=, == ONLY. and,or are not defined and should NOT be used.
    Aim to make this mutation such that it will make the expression significantly harder for an SMT solver to solve, but only mutate a single operand from the root (do not change the root operator)
    Output ONLY the mutated formula in Z3-style format.
    
    Rules:
    - Output ONLY the Z3 formula, nothing else.
    - Do NOT include any Markdown code fences like ```smt``` or ``` or any other annotations.
    - Keep it valid Z3-style syntax, and make sure the root operator gives a Boolean expression and the two operands to it have the same type to prevent type errors.
    
    """
        # z3_mutated = call_LLM(prompt_z3)
        # # print("\nLLM Z3-style mutation output:")
        # # print(z3_mutated)
        # if is_well_formed_z3(z3_mutated, NUM_VARS):
        #     well_formed_z3 += 1
        # else:
        #     error_z3.append(z3_mutated)

        # Prompt LLM for SMT-LIB mutation
        prompt_smtlib = f"""
    You are an SMT mutation operator.
    
    Given this SMT-LIB formula:
    
    {smtlib_str}
    
    Produce a mutation using only variables specified in the input string and primitives +, -, *, >, <, >=, <=, = (as defined in SMT-LIB).
    Aim to make this mutation such that it will make the expression significantly harder for an SMT solver to solve, but only mutate a single operand from the root (do not change the root operator)
    Output ONLY the mutated formula in SMT-LIB format.
    
    Rules:
    - Output ONLY the SMT-LIB formula, nothing else, but make sure this includes the logic and the variable declarations before the assert (as in the formula provided).
    - Do NOT include any Markdown code fences like ```smt``` or ``` or any other annotations.
    - Keep it valid SMT-LIB 2.0 syntax.
    
    """
        # smtlib_mutated = call_LLM(prompt_smtlib)
        # # print("\nLLM SMT-LIB mutation output:")
        # # print(smtlib_mutated)
        # _, smtlib_res = measure_runtime_subprocess_stdin(smtlib_mutated,"z3",0.1)
        # if smtlib_res != "subFailed":
        #     well_formed_smtlib += 1
        # else:
        #     error_smtlib.append(smtlib_mutated)

        # Prompt LLM for DEAP mutation
        prompt_deap = f"""
    You are an SMT mutation operator.
    
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
        
    Produce a mutation using primitives defined in the pset (i.e only add, sub, mul, gt, lt, ge, le or eq), you may introduce new variables in the form of ARGx where x is a number up to {NUM_VARS - 1}
    Aim to make this mutation such that it will make the expression significantly harder for an SMT solver to solve, but only mutate a single operand from the root (do not change the root operator)
    Output ONLY the mutated formula in DEAP format so I can parse it straight back into DEAP.
    
    Rules:
    - Output ONLY the formula, nothing else. and, or, nand, etc. are NOT permitted. Use only primitives provided in the set above
    - The root operator gives a Boolean expression and the operands of this must evaluate to the same type to prevent type errors.
    - Do NOT include any Markdown code fences like ```smt``` or ``` or any other annotations.
    
    """
        deap_mutated = call_LLM(prompt_deap)

        if is_well_formed_deap(deap_mutated, pset, NUM_VARS):
            #well_formed_deap += 1
            print("\nLLM DEAP mutation output:")
            print(deap_mutated)
        else:
            print("\nDEAP MUTATION WAS INVALID")
            print(deap_mutated)
            #error_deap.append(deap_mutated)

    # print(f"Well-formed SMT-LIB LLM outputs: {well_formed_smtlib}/{RUNS}")
    # print(f"Error mutations for SMT-LIB: {error_smtlib}")
    # print(f"Well-formed DEAP LLM outputs: {well_formed_deap}/{RUNS}")
    # print(f"Error mutations for DEAP:  {error_deap}")
    # print(f"Well-formed z3 LLM outputs: {well_formed_z3}/{RUNS}")
    # print(f"Error mutations for z3: {error_z3}")

import re

# operator → (deap_name, precedence)
OPS = {
    '+':  ('add', 2),
    '-':  ('sub', 2),
    '*':  ('mul', 3),
    '>':  ('gt', 1),
    '<':  ('lt', 1),
    '>=': ('ge', 1),
    '<=': ('le', 1),
    '==': ('eq', 1),
}

TOKEN_REGEX = re.compile(
    r'\s*(>=|<=|==|[()+\-*<>]|x\d+)\s*'
)

def tokenize(expr: str):
    return TOKEN_REGEX.findall(expr)

def infix_to_ast(tokens):
    """Shunting-yard → AST"""
    output = []
    ops = []

    def pop_op():
        op = ops.pop()
        rhs = output.pop()
        lhs = output.pop()
        output.append((op, lhs, rhs))

    for tok in tokens:
        if tok.startswith('x'):
            output.append(tok)
        elif tok == '(':
            ops.append(tok)
        elif tok == ')':
            while ops[-1] != '(':
                pop_op()
            ops.pop()
        else:  # operator
            _, prec = OPS[tok]
            while ops and ops[-1] != '(' and OPS[ops[-1]][1] >= prec:
                pop_op()
            ops.append(tok)

    while ops:
        pop_op()

    return output[0]

def ast_to_deap(node):
    if isinstance(node, str):
        return node
    op, lhs, rhs = node
    deap_name = OPS[op][0]
    return f"{deap_name}({ast_to_deap(lhs)}, {ast_to_deap(rhs)})"

def infix_to_deap(expr: str) -> str:
    tokens = tokenize(expr)
    ast = infix_to_ast(tokens)
    return ast_to_deap(ast)


if __name__ == "__main__":
    #main()
    test_llm_mutation()




