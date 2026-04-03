def formula_depth(formula: str) -> int:
    depth = 0
    max_depth = 0

    for char in formula:
        if char == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == ")":
            depth -= 1

    return max_depth

def main():
    formulas = [
        "ge(mul(add(mul(add(ARG2, ARG1), mul(ARG0, ARG2)), mul(mul(ARG0, ARG4), mul(ARG2, ARG4))), mul(mul(ARG4, ARG4), sub(ARG3, ARG4))), mul(mul(mul(mul(ARG0, ARG3), sub(ARG4, ARG1)), sub(add(mul(ARG0, ARG1), sub(ARG2, ARG3)), mul(mul(ARG1, ARG2), add(ARG3, ARG4)))), add(mul(ARG2, ARG2), mul(ARG3, ARG3))))",
        "gt(mul(mul(sub(ARG0, ARG4), mul(ARG1, ARG0)), mul(sub(ARG4, ARG3), add(ARG0, ARG2))), mul(sub(sub(mul(add(ARG3, ARG4), ARG0), sub(mul(ARG1, ARG2), mul(ARG3, ARG4))), mul(sub(mul(ARG3, ARG2), sub(ARG1, ARG2)), sub(mul(ARG0, ARG4), add(ARG2, ARG3)))), add(mul(ARG0, ARG1), sub(mul(mul(ARG2, ARG3), mul(mul(ARG4, ARG1), add(ARG0, ARG1))), mul(add(ARG2, ARG3), sub(ARG3, ARG4))))))",
        "gt(mul(add(ARG2, ARG4), mul(ARG0, ARG4)), mul(mul(ARG1, ARG3), add(sub(ARG1, mul(ARG3, ARG2)), mul(ARG1, ARG4))))",
        "ge(add(mul(add(mul(ARG4, ARG3), sub(ARG3, ARG1)), add(mul(ARG0, ARG4), sub(ARG4, ARG3))), mul(sub(add(ARG0, ARG1), add(ARG2, ARG0)), sub(sub(ARG2, ARG1), sub(mul(ARG2, ARG3), sub(ARG2, ARG3))))), sub(mul(sub(mul(ARG3, ARG2), sub(ARG0, ARG3)), mul(add(ARG2, ARG4), mul(ARG0, ARG0))), sub(mul(add(ARG1, ARG1), sub(ARG1, ARG3)), sub(mul(mul(ARG1, ARG1), mul(ARG1, ARG0)), mul(add(mul(ARG0, ARG1), ARG0), mul(mul(ARG0, ARG0), sub(mul(ARG3, ARG1), add(mul(ARG2, ARG4), mul(ARG3, ARG3)))))))))",
        "lt(sub(add(sub(sub(ARG0, ARG1), sub(ARG1, ARG4)), sub(mul(ARG0, ARG1), add(ARG4, ARG2))), sub(mul(sub(ARG0, ARG1), add(ARG1, ARG0)), mul(add(ARG1, ARG0), mul(ARG3, ARG0)))), mul(add(mul(mul(ARG4, ARG4), add(ARG3, ARG0)), add(add(ARG2, ARG0), add(ARG4, ARG3))), add(sub(add(ARG0, ARG2), mul(ARG4, ARG2)), add(mul(ARG3, ARG0), add(mul(ARG0, ARG1), add(mul(ARG0, ARG0), mul(mul(ARG0, ARG0), add(mul(ARG0, ARG0), mul(ARG0, mul(ARG0, ARG0))))))))))",
        "eq(add(mul(mul(mul(ARG4, ARG2), sub(ARG4, ARG2)), add(add(ARG0, ARG2), mul(ARG0, ARG2))), sub(mul(sub(ARG4, ARG3), add(ARG4, ARG4)), sub(add(ARG2, ARG0), mul(ARG0, ARG1)))), add(mul(sub(ARG3, ARG3), add(ARG2, ARG2)), mul(mul(mul(ARG3, ARG3), ARG3), mul(mul(ARG4, ARG0), add(ARG1, mul(ARG2, add(mul(ARG2, ARG3), add(mul(ARG3, ARG4), add(mul(ARG0, ARG1), mul(ARG1, sub(ARG4, ARG3)))))))))))",
        "ge(mul(sub(mul(ARG2, ARG0), add(ARG4, ARG2)), sub(sub(ARG4, ARG3), mul(mul(ARG3, ARG0), add(ARG1, ARG1)))), mul(mul(sub(ARG0, ARG4), mul(ARG4, ARG2)), sub(mul(mul(ARG4, ARG4), ARG0), mul(mul(ARG4, ARG2), add(ARG3, ARG3)))))",
        "eq(sub(sub(mul(add(ARG4, ARG4), add(ARG4, ARG3)), sub(mul(ARG3, ARG4), sub(ARG4, ARG3))), mul(sub(add(ARG2, ARG3), sub(ARG4, ARG3)), add(sub(ARG3, ARG0), add(ARG3, ARG2)))), mul(mul(sub(add(ARG0, ARG0), mul(ARG3, ARG0)), sub(sub(ARG4, ARG2), mul(ARG1, ARG1))), add(mul(sub(ARG1, ARG3), mul(ARG3, ARG4)), add(add(ARG1, ARG1), mul(mul(ARG0, ARG4), add(ARG2, mul(ARG2, mul(ARG2, mul(ARG2, ARG2)))))))))",
        "gt(mul(mul(mul(ARG4, ARG2), sub(ARG2, ARG1)), add(mul(ARG3, ARG0), sub(ARG3, ARG4))), mul(add(add(sub(ARG4, ARG2), mul(mul(ARG3, ARG3), mul(ARG3, ARG3))), sub(sub(ARG3, ARG1), mul(ARG0, ARG2))), add(mul(ARG0, ARG1), mul(ARG2, ARG3))))",
        "eq(add(add(add(add(ARG1, ARG2), mul(ARG0, ARG1)), mul(mul(ARG4, ARG2), mul(ARG1, ARG2))), sub(mul(add(ARG0, ARG2), sub(ARG1, ARG3)), sub(mul(ARG2, ARG4), add(ARG3, ARG3)))), add(sub(mul(sub(ARG1, ARG1), add(ARG2, ARG0)), mul(mul(ARG0, ARG1), sub(ARG3, ARG0))), mul(add(add(mul(ARG3, ARG4), mul(ARG3, ARG4)), sub(mul(ARG3, ARG4), mul(ARG3, ARG4))), mul(mul(ARG0, ARG1), mul(ARG2, mul(ARG3, add(mul(ARG0, ARG1), sub(mul(ARG4, ARG4), add(mul(ARG4, ARG4), sub(ARG4, ARG4))))))))))",
        "gt(mul(mul(sub(ARG0, ARG0), sub(ARG2, ARG4)), mul(sub(ARG3, ARG1), add(ARG1, ARG0))), mul(add(mul(sub(ARG4, ARG3), mul(ARG1, ARG3)), mul(add(ARG4, ARG2), mul(ARG2, ARG2))), mul(add(sub(ARG0, ARG2), sub(ARG2, ARG3)), add(mul(ARG4, ARG2), add(ARG3, ARG0)))))",
        "lt(mul(sub(ARG2, ARG0), sub(mul(ARG0, ARG1), mul(ARG0, ARG4))), mul(add(mul(add(ARG1, ARG4), mul(ARG3, ARG1)), sub(add(ARG3, ARG1), add(ARG2, ARG2))), add(mul(mul(ARG4, ARG1), sub(ARG1, ARG1)), mul(sub(ARG0, mul(ARG4, ARG4)), sub(mul(ARG4, ARG3), mul(ARG3, ARG2))))))",
        "ge(add(sub(mul(ARG4, ARG4), add(ARG2, ARG4)), sub(add(ARG1, ARG3), add(ARG2, ARG0))), mul(sub(add(mul(ARG4, ARG2), sub(ARG1, ARG2)), sub(mul(ARG1, ARG4), mul(mul(ARG3, ARG1), add(ARG3, ARG4)))), mul(sub(ARG1, ARG4), mul(mul(ARG3, ARG1), add(mul(ARG0, ARG1), mul(mul(ARG2, ARG3), add(mul(mul(ARG2, ARG3), ARG3), mul(mul(ARG2, ARG3), mul(ARG3, mul(ARG3, ARG3))))))))))",
        "lt(mul(sub(add(add(ARG0, ARG4), sub(ARG1, ARG2)), sub(add(ARG3, ARG0), mul(ARG3, ARG3))), add(add(mul(ARG1, ARG2), add(ARG1, ARG1)), mul(add(ARG4, ARG4), add(ARG4, ARG4)))), add(add(sub(sub(ARG1, ARG0), sub(ARG3, ARG0)), add(add(ARG3, ARG0), mul(ARG0, ARG0))), add(add(sub(ARG2, ARG4), sub(ARG1, ARG2)), mul(sub(mul(ARG3, ARG2), sub(ARG2, ARG0)), add(ARG3, ARG1)))))",
        "le(mul(add(add(sub(ARG0, ARG4), mul(ARG4, ARG3)), sub(add(ARG3, ARG2), add(ARG4, ARG3))), sub(add(mul(ARG3, ARG1), mul(ARG0, ARG2)), mul(add(ARG2, ARG4), sub(ARG3, ARG1)))), add(mul(sub(mul(mul(ARG2, ARG0), add(mul(ARG3, ARG3), ARG3)), sub(mul(ARG4, ARG3), sub(ARG1, ARG1))), sub(sub(ARG0, ARG4), add(ARG1, ARG1))), mul(add(mul(add(ARG1, ARG4), mul(ARG1, ARG2)), mul(mul(ARG3, ARG4), add(mul(ARG2, ARG3), mul(ARG2, ARG3)))), mul(add(mul(ARG0, ARG1), mul(ARG2, ARG3)), sub(mul(mul(ARG3, ARG4), ARG0), mul(ARG1, ARG4))))))",
        "eq(mul(mul(mul(sub(ARG3, ARG1), sub(ARG3, ARG1)), add(sub(ARG3, ARG1), add(ARG3, ARG3))), sub(add(sub(ARG3, ARG0), add(ARG2, ARG2)), sub(sub(ARG4, ARG3), add(ARG3, ARG2)))), sub(add(sub(add(mul(ARG2, ARG4), mul(ARG0, ARG4)), mul(sub(ARG4, ARG3), add(ARG4, ARG2))), sub(add(ARG4, ARG3), add(ARG4, ARG2))), add(mul(mul(ARG1, ARG2), sub(ARG0, ARG3)), mul(mul(ARG3, ARG2), mul(mul(mul(ARG2, ARG1), add(mul(ARG4, ARG0), ARG0)), add(mul(ARG1, ARG4), sub(mul(ARG3, ARG2), ARG2)))))))",
        "le(mul(add(mul(sub(ARG1, ARG0), add(ARG3, ARG1)), mul(add(ARG1, ARG3), sub(ARG3, ARG4))), mul(mul(add(ARG2, ARG4), sub(ARG1, ARG2)), mul(add(ARG0, ARG4), add(ARG3, ARG2)))), mul(sub(mul(sub(mul(ARG3, ARG2), mul(ARG3, ARG4)), mul(add(ARG4, ARG0), mul(ARG4, ARG2))), sub(mul(mul(ARG0, ARG2), add(ARG1, ARG4)), mul(mul(ARG3, ARG1), add(mul(ARG3, ARG2), sub(ARG4, ARG0))))), mul(add(mul(ARG0, ARG1), sub(mul(ARG4, ARG3), mul(ARG4, ARG2))), mul(add(ARG2, ARG3), sub(ARG4, ARG1)))))",
        "le(mul(sub(add(sub(ARG4, ARG2), sub(ARG1, ARG0)), add(mul(ARG0, ARG2), add(ARG1, ARG2))), add(mul(add(ARG4, ARG1), mul(ARG3, ARG2)), sub(mul(ARG3, ARG0), mul(ARG4, ARG3)))), mul(mul(sub(mul(ARG2, ARG0), add(ARG3, ARG3)), add(mul(ARG2, ARG3), sub(ARG1, ARG2))), mul(add(mul(mul(ARG0, ARG1), mul(ARG2, ARG3)), mul(mul(ARG1, ARG2), mul(ARG3, ARG4))), add(mul(mul(ARG0, ARG1), mul(ARG2, ARG3)), mul(mul(ARG1, ARG2), mul(mul(ARG3, ARG4), add(ARG0, mul(ARG1, ARG0))))))))",
        "ge(mul(add(mul(mul(ARG0, ARG1), mul(ARG2, ARG3)), sub(mul(ARG1, ARG4), mul(ARG3, ARG0))), sub(sub(mul(ARG3, ARG3), sub(ARG0, ARG0)), mul(add(ARG4, ARG4), mul(ARG3, ARG2)))), mul(sub(sub(mul(ARG3, ARG3), sub(ARG0, ARG0)), mul(add(ARG4, ARG4), mul(ARG3, ARG2))), mul(sub(sub(ARG0, ARG3), add(ARG1, ARG3)), add(sub(ARG0, ARG3), mul(mul(ARG4, ARG4), add(mul(ARG2, ARG2), sub(mul(ARG1, ARG1), mul(mul(ARG1, ARG1), ARG3))))))))",
        "gt(mul(sub(sub(sub(ARG0, ARG2), mul(ARG1, ARG1)), mul(mul(ARG4, ARG4), sub(ARG3, ARG4))), sub(sub(add(ARG4, ARG2), mul(ARG1, ARG3)), add(sub(ARG2, ARG4), mul(ARG2, ARG1)))), mul(add(mul(ARG2, ARG1), sub(mul(ARG0, ARG4), add(ARG3, ARG2))), mul(add(ARG0, ARG1), sub(mul(ARG3, ARG4), add(mul(ARG2, ARG0), sub(mul(ARG4, ARG3), add(ARG1, ARG3)))))))",

    ]

    for i, f in enumerate(formulas, 1):
        print(f"{formula_depth(f)}")

if __name__ == "__main__":
    main()