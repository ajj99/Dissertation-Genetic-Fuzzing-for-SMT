from z3 import Int, Solver
import random

# -------------------------
# Configuration
# -------------------------
NUM_VARS = 3  # number of integer variables
NUM_ASSERTS = 2  # number of assertions
MAX_DEPTH = 2  # maximum depth of nested expressions


# -------------------------
# Helper functions
# -------------------------
def random_var_name():
    return random.choice(["x"]) + str(random.randint(0, 9))


# Generate a random integer expression recursively
def random_int_expr(vars_list, depth=0):
    if depth >= MAX_DEPTH or random.random() < 0.3:
        # Base case: constant or variable
        return random.choice(vars_list) if random.random() < 0.5 else random.randint(0, 10)

    # Random operation
    op = random.choice(['+', '-', '*'])
    left = random_int_expr(vars_list, depth + 1)
    right = random_int_expr(vars_list, depth + 1)

    if op == '+':
        return left + right
    elif op == '-':
        return left - right
    elif op == '*':
        return left * right


# Generate a random Boolean comparison between integer expressions
def random_bool_expr(vars_list):
    left = random_int_expr(vars_list)
    right = random_int_expr(vars_list)
    op = random.choice(['>', '<', '>=', '<=', '='])
    if op == '>':
        return left > right
    elif op == '<':
        return left < right
    elif op == '>=':
        return left >= right
    elif op == '<=':
        return left <= right
    elif op == '=':
        return left == right


# -------------------------
# Generate variables
# -------------------------
vars_list = [Int(random_var_name()) for _ in range(NUM_VARS)]

# -------------------------
# Generate random Boolean assertions
# -------------------------
solver = Solver()
for _ in range(NUM_ASSERTS):
    expr = random_bool_expr(vars_list)
    solver.add(expr)

# -------------------------
# Output SMT-LIB
# -------------------------
print(solver.to_smt2())
