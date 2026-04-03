import sexpdata
from z3 import ArithRef, BoolRef
from deap import gp
from z3 import Int, Solver, BoolVal
import operator

NUM_VARS = 5  # ARG0 .. ARG4

def build_pset(num_vars):
    pset = gp.PrimitiveSetTyped("MAIN", [ArithRef] * NUM_VARS, BoolRef)

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

    # # Terminals
    pset.addTerminal(BoolVal(True), BoolRef)
    pset.addTerminal(BoolVal(False), BoolRef)

    #pset_join = copy.deepcopy(pset)

    def z3_and(x, y):
        if isinstance(x, bool):
            x = BoolVal(x)
        if isinstance(y, bool):
            y = BoolVal(y)
        return And(x, y)

    pset.addPrimitive(
        z3_and,
        [BoolRef, BoolRef],
        BoolRef,
        name="and_"
    )
    return pset


def deap_to_smtlib(deap_str, pset, num_vars, logic="QF_NIA"):

    # Parse DEAP string into an individual
    individual = gp.PrimitiveTree.from_string(deap_str, pset)
    print(individual)
    # Compile to a callable
    func = gp.compile(expr=individual, pset=pset)

    # Build Z3 variables
    vars_z3 = [Int(f"x{i}") for i in range(num_vars)]

    # Evaluate the DEAP expression with Z3 variables
    z3_formula = func(*vars_z3)
    print(z3_formula)
    if isinstance(z3_formula, bool):
        z3_formula = BoolVal(z3_formula)

    # Build SMT-LIB string via Z3 solver
    s = Solver()
    s.add(z3_formula)
    return f"(set-logic {logic})\n" + s.to_smt2()


def batch_convert(deap_strings, num_vars=NUM_VARS, logic="QF_NIA"):
    """
    Convert a list of DEAP AST strings to SMT-LIB formula strings.

    Args:
        deap_strings: list of DEAP expression strings
        num_vars:     number of ARG variables in your pset
        logic:        SMT-LIB logic

    Returns:
        list of SMT-LIB strings (same order as input), None on parse failure
    """
    pset = build_pset(num_vars)
    results = []
    for i, deap_str in enumerate(deap_strings):
        try:
            smtlib = deap_to_smtlib(deap_str.strip(), pset, num_vars, logic)
            results.append(smtlib)
        except Exception as e:
            print(f"[Warning] Formula {i} failed: {e}\n  Input: {deap_str[:80]}")
            results.append(None)
    return results


# ── Example usage ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    deap_formulas = [
        "gt(mul(mul(add(ARG2, ARG4), add(ARG0, ARG4)), add(add(ARG4, ARG0), sub(ARG0, ARG2))),mul(add(ARG1, ARG3), add(ARG3, ARG0)))",
        "lt(mul(mul(mul(ARG2, ARG4), sub(ARG2, ARG3)), sub(mul(ARG2, ARG3), mul(ARG0, ARG3))), mul(sub(add(ARG3, ARG0), mul(ARG3, ARG0)), sub(sub(ARG3, ARG4), ARG3)))",
        "lt(mul(mul(mul(ARG1, ARG2), mul(ARG2, ARG3)), sub(sub(ARG1, ARG3), add(ARG3, ARG4))), sub(mul(mul(ARG2, ARG4), mul(ARG1, ARG0)), mul(mul(ARG3, ARG0), mul(ARG2, ARG2))))",
        "ge(mul(mul(sub(add(ARG2, ARG3), add(ARG3, ARG4)), add(sub(ARG0, ARG3), mul(ARG4, ARG0))), mul(add(add(ARG2, ARG0), mul(ARG1, ARG4)), mul(mul(ARG1, ARG0), sub(ARG0, ARG4)))), mul(add(add(add(ARG1, ARG1), sub(ARG2, ARG4)), mul(sub(ARG4, ARG0), add(ARG1, ARG3))), mul(sub(sub(add(ARG3, ARG0), sub(ARG3, ARG4)), sub(ARG4, ARG0)), sub(add(mul(mul(mul(add(sub(ARG3, ARG4), mul(sub(ARG4, ARG0), add(ARG1, ARG3))), mul(sub(sub(add(ARG3, ARG0), sub(ARG3, ARG4)), sub(ARG4, ARG0)), sub(add(mul(mul(ARG2, ARG0), add(ARG0, ARG0)), ARG4), add(ARG3, mul(ARG1, ARG0))))), ARG0), add(ARG0, ARG0)), ARG4), mul(add(add(ARG0, ARG0), add(add(ARG2, ARG4), mul(ARG2, ARG4))), mul(mul(ARG1, ARG0), ARG4))))))",
        "gt(mul(add(sub(mul(ARG2, ARG1), sub(ARG2, ARG0)), sub(add(ARG0, ARG1), sub(ARG0, ARG2)))\
        add(add(mul(ARG2, ARG2), sub(ARG4, sub(sub(ARG4, ARG3), add(ARG2, ARG2))))\
                   sub(mul(ARG2, ARG4), add(ARG1, ARG3)))), mul(sub(ARG4, ARG1), mul(ARG3, ARG3)))"

        #"and_(and_(gt(mul(mul(mul(ARG3, ARG4), add(ARG2, ARG0)), mul(add(ARG2, ARG4), add(ARG1, ARG4))), mul(mul(mul(ARG3, ARG3), sub(ARG3, ARG0)), add(sub(ARG4, ARG0), sub(ARG0, ARG0)))), and_(gt(mul(add(sub(sub(ARG0, ARG0), sub(ARG1, ARG2)), add(mul(ARG2, ARG2), add(ARG4, ARG2))), mul(sub(sub(ARG1, ARG0), sub(ARG3, ARG2)), mul(mul(ARG1, ARG3), mul(ARG0, ARG1)))), sub(add(mul(add(ARG2, ARG1), mul(ARG0, ARG1)), sub(add(ARG1, ARG4), sub(ARG1, ARG1))), sub(sub(sub(ARG4, ARG3), mul(ARG1, ARG3)), sub(sub(ARG0, ARG4), sub(ARG3, ARG3))))), and_(gt(mul(mul(mul(ARG3, ARG4), add(ARG2, ARG0)), mul(add(ARG2, ARG4), add(ARG1, ARG4))), mul(mul(mul(ARG3, ARG3), sub(ARG3, ARG0)), add(sub(ARG4, ARG0), sub(ARG0, ARG0)))), and_(gt(mul(add(sub(sub(ARG0, ARG0), sub(ARG1, ARG2)), add(mul(ARG2, ARG2), add(ARG4, ARG2))), mul(sub(sub(ARG1, ARG0), sub(ARG3, ARG2)), mul(mul(ARG1, ARG3), mul(ARG0, ARG1)))), sub(add(mul(add(ARG2, ARG1), mul(ARG0, ARG1)), sub(add(ARG1, ARG4), sub(ARG1, ARG1))), sub(sub(sub(ARG4, ARG3), mul(ARG1, ARG3)), sub(sub(ARG0, ARG4), sub(ARG3, ARG3))))), eq(sub(mul(mul(add(ARG2, ARG4), add(ARG2, ARG0)), add(mul(ARG2, ARG1), mul(ARG2, ARG4))), add(sub(sub(ARG4, ARG1), sub(ARG0, ARG4)), sub(sub(ARG2, ARG0), sub(ARG2, ARG2)))), add(sub(mul(sub(ARG0, ARG0), mul(ARG4, ARG2)), mul(add(ARG2, ARG3), mul(ARG2, ARG4))), add(sub(sub(ARG2, add(sub(add(add(ARG4, ARG1), add(ARG2, ARG1)), add(sub(ARG0, sub(add(ARG2, ARG1), add(ARG3, ARG0))), sub(ARG1, ARG0))), mul(mul(mul(ARG2, ARG3), add(ARG1, ARG3)), mul(mul(ARG2, ARG4), sub(add(ARG1, ARG4), mul(ARG3, ARG1)))))), add(ARG0, ARG0)), mul(add(ARG3, ARG1), mul(ARG2, ARG1))))))))), gt(mul(mul(sub(ARG1, ARG4), mul(ARG0, ARG4)), mul(add(mul(add(ARG2, ARG2), add(ARG3, ARG3)), ARG4), add(ARG1, ARG4))), mul(sub(sub(add(add(ARG2, ARG0), add(ARG1, ARG2)), ARG4), sub(ARG4, ARG4)), add(sub(ARG4, ARG0), sub(ARG0, ARG0)))))"
    ]

    smtlib_formulas = batch_convert(deap_formulas, num_vars=NUM_VARS)

    for i, (deap, smt) in enumerate(zip(deap_formulas, smtlib_formulas)):
        print(f"── Formula {i} ──────────────────────────────")
        print(f"DEAP : {deap[:60]}...")
        print(f"SMT  :\n{smt}")

