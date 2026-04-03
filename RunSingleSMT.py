from z3 import *
import subprocess
import time

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
        else:
            print(f"Unknown solver: {solver_cmd}")
            return -1, "subFailed", ""

        end = time.time()
        output = proc.stdout.strip().lower()

        if proc.returncode == 0:
            if "sat" in output or "unsat" in output:
                return end - start, "intime", output
            else:
                return timeout_seconds, "timeoutOE", output
        else:
            return -1, "subFailed", output

    except subprocess.TimeoutExpired:
        return timeout_seconds, "timeoutOE", "unknown"


def run_query(smtlib_str, solver, timeout_seconds):
    print(f"\nRunning on solver: {solver}")
    print(f"Timeout: {timeout_seconds}s")
    print("-" * 40)

    runtime, result, output = measure_runtime_subprocess_stdin(smtlib_str, solver, timeout_seconds)

    print(f"Result:  {result}")
    print(f"Output:  {output}")
    print(f"Runtime: {runtime:.6f}s")
    return runtime, result, output


if __name__ == "__main__":
    # ---- PASTE YOUR SMT-LIB QUERY HERE ----
    smtlib_str = """
(set-logic QF_NIA)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun x0 () Int)
(declare-fun x1 () Int)
(declare-fun x2 () Int)
(declare-fun x3 () Int)
(declare-fun x4 () Int)
(assert
 (let ((?x16 (* (* (+ x2 x4) (+ x0 x4)) (+ (+ x4 x0) (- x0 x2)))))
(> ?x16 (* (+ x1 x3) (+ x3 x0)))))
(check-sat)

    """

    # ---- CONFIGURE THESE ----
    SOLVER = "mathsat"           # "z3", "cvc5", or "mathsat"
    TIMEOUT_SECONDS = 600

    run_query(smtlib_str, "z3", TIMEOUT_SECONDS)
    run_query(smtlib_str,"cvc5", TIMEOUT_SECONDS)
    run_query(smtlib_str, "mathsat", TIMEOUT_SECONDS)


