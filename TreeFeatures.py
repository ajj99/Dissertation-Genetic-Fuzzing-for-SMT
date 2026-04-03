import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import umap

from collections import Counter
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Constants

BOOL_OPS = {'and_'}
CMP_OPS = {'gt', 'lt', 'ge', 'le', 'eq'}
ARITH_OPS = {'add', 'sub', 'mul', 'div', 'neg'}

SOLVER_STYLE = {
    "mathsat": "tab:green",
    "z3": "tab:orange",
    "cvc5": "tab:blue",
}


# Tree Parsing

def parse_tree(deap_str):
    """Parse a DEAP string into a nested tuple tree: (name, [children])."""
    tokens = re.findall(r'[(),]|[A-Za-z_][A-Za-z0-9_]*|\d+', deap_str)
    pos = [0]

    def parse():
        token = tokens[pos[0]]
        pos[0] += 1
        if pos[0] < len(tokens) and tokens[pos[0]] == '(':
            pos[0] += 1
            children = []
            while pos[0] < len(tokens) and tokens[pos[0]] != ')':
                if tokens[pos[0]] == ',':
                    pos[0] += 1
                else:
                    children.append(parse())
            if pos[0] < len(tokens):
                pos[0] += 1
            return (token, children)
        else:
            return (token, [])

    return parse()


# Feature Extraction

def extract_tree_features(deap_str):
    """Extract structural and operator features from a DEAP formula tree."""
    try:
        tree = parse_tree(deap_str)
    except Exception as e:
        print(f"  Parse error: {e}")
        return None

    depths = []
    op_counts = Counter()
    arith_depths = []
    node_count = [0]
    leaf_count = [0]

    def walk(node, depth):
        name, children = node
        node_count[0] += 1
        depths.append(depth)

        if not children:
            leaf_count[0] += 1
            return

        op_counts[name] += 1

        if name in ARITH_OPS:
            arith_depths.append(depth)

        for child in children:
            walk(child, depth + 1)

    walk(tree, 0)

    total_arith = sum(op_counts[o] for o in ARITH_OPS)

    return {
        # size / shape
        #"max_depth":         max(depths),
        #"mean_depth":        np.mean(depths),
        #"branching_factor":  node_count[0] / max(leaf_count[0], 1),

        #operator class counts
        #"n_bool":            total_bool,
        #"n_cmp":             total_cmp,
        #"n_arith":           total_arith,
        #"n_mul":             op_counts.get("mul", 0),
        #"n_add":             op_counts.get("add", 0),
        #"n_sub":             op_counts.get("sub", 0),

        #operator class ratios
        #"ratio_bool":        total_bool  / total_ops,
        #"ratio_cmp":         total_cmp   / total_ops,
        #"ratio_arith":       total_arith / total_ops,
        "ratio_mul_arith":   op_counts.get("mul", 0) / max(total_arith, 1),

        # depth of first occurrence of each class
        #"depth_first_bool":  min(bool_depths,  default=0),
        #"depth_first_cmp":   min(cmp_depths,   default=0),
        #"depth_first_arith": min(arith_depths, default=0),

        # mean depth of each class
        "mean_depth_arith":  np.mean(arith_depths) if arith_depths else 0,
        #"mean_depth_cmp":    np.mean(cmp_depths)   if cmp_depths   else 0,
        #"mean_depth_bool":   np.mean(bool_depths)  if bool_depths  else 0,

        # nonlinearity proxy
        "max_arith_depth":   max(arith_depths, default=0),

        # # root operator one-hot
        # "root_is_gt":        int(root_op == "gt"),
        # "root_is_lt":        int(root_op == "lt"),
        # "root_is_ge":        int(root_op == "ge"),
        # "root_is_le":        int(root_op == "le"),
        # "root_is_eq":        int(root_op == "eq"),
        # "root_is_and":       int(root_op == "and_"),
    }


# Plotting

def plot_pca_umap_sidebyside(X, solvers, root_labels):
    """Plot PCA and UMAP side by side, coloured by solver, labelled by root node."""

    # PCA
    pca = PCA(n_components=2)
    pca_coords = pca.fit_transform(X)
    pca_var = sum(pca.explained_variance_ratio_)
    print(f"PCA variance: {pca_var:.2%}")

    # UMAP
    reducer = umap.UMAP(n_components=2, random_state=42,
                        n_neighbors=10, min_dist=0.1)
    umap_coords = reducer.fit_transform(X)

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    for ax, coords, xlabel, ylabel, subtitle in [
        (axes[0], pca_coords, "PC1", "PC2", "PCA"),
        (axes[1], umap_coords, "UMAP-1", "UMAP-2", "UMAP"),
    ]:
        for i, (x, y) in enumerate(coords):
            colour = SOLVER_STYLE.get(solvers[i], "tab:gray")
            ax.scatter(x, y, color=colour, s=80, zorder=2)
            ax.text(x, y, root_labels[i], fontsize=7, zorder=3)

        ax.set_title(subtitle, fontsize=18)
        ax.set_xlabel(xlabel, fontsize=16)
        ax.set_ylabel(ylabel, fontsize=16)
        ax.grid(True, linestyle="--", alpha=0.3)


    legend_handles = [
        mpatches.Patch(color=SOLVER_STYLE["mathsat"], label="MathSAT"),
        mpatches.Patch(color=SOLVER_STYLE["z3"], label="Z3"),
        mpatches.Patch(color=SOLVER_STYLE["cvc5"], label="cvc5"),
    ]
    axes[0].legend(handles=legend_handles, loc="lower right", fontsize=12, frameon=True)

    plt.subplots_adjust(wspace=0.3)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":

    deap_formulas = [
        "gt(mul(sub(add(mul(ARG2, ARG0), sub(ARG2, ARG2)), ARG2), add(sub(mul(ARG3, ARG0), mul(ARG4, ARG3)), ARG2)), sub(mul(sub(mul(ARG0, ARG1), add(ARG3, ARG0)), sub(sub(ARG4, ARG3), sub(ARG3, ARG4))), mul(sub(ARG0, ARG0), mul(add(ARG1, ARG4), sub(ARG0, ARG4)))))",
        "lt(mul(sub(mul(sub(ARG1, ARG4), sub(ARG4, ARG4)), mul(sub(ARG0, ARG3), mul(ARG1, ARG1))), sub(sub(add(ARG0, ARG0), sub(ARG0, ARG1)), mul(mul(ARG4, ARG1), mul(ARG1, ARG4)))), sub(mul(add(ARG1, ARG1), mul(add(ARG1, ARG3), add(ARG1, ARG1))), mul(add(sub(ARG0, ARG2), sub(ARG2, ARG4)), mul(mul(ARG1, ARG2), add(ARG3, ARG4)))))",
        "le(mul(mul(sub(mul(ARG1, ARG4), mul(ARG0, ARG1)), mul(mul(ARG0, ARG2), sub(ARG4, ARG0))), mul(sub(add(ARG3, mul(ARG1, ARG4)), mul(ARG3, ARG3)), mul(mul(ARG3, ARG2), sub(ARG2, ARG1)))), ARG1)",
        "le(add(sub(mul(add(ARG2, ARG3), mul(ARG0, mul(ARG0, mul(ARG3, ARG0)))), mul(mul(ARG2, ARG1), mul(ARG1, ARG3))), mul(add(add(mul(add(ARG1, ARG0), mul(ARG0, ARG0)), mul(add(ARG4, ARG4), mul(ARG3, ARG0))), add(ARG3, ARG4)), mul(add(ARG0, sub(add(ARG4, ARG3), sub(ARG2, ARG0))), sub(ARG1, ARG4)))), sub(mul(mul(sub(ARG1, ARG2), mul(ARG3, ARG0)), sub(add(ARG3, ARG4), sub(ARG1, ARG4))), add(mul(add(ARG1, ARG0), mul(ARG0, ARG0)), mul(add(ARG4, ARG4), mul(ARG3, ARG0)))))",
        "gt(mul(sub(ARG1, ARG2), add(add(add(add(ARG3, ARG2), ARG2), sub(ARG1, ARG2)), sub(add(ARG2, ARG0), mul(mul(ARG4, ARG4), ARG4)))), sub(mul(mul(add(ARG3, ARG0), add(ARG0, ARG3)), add(mul(ARG1, ARG0), sub(ARG1, ARG3))), add(ARG1, mul(add(ARG0, ARG1), mul(ARG1, ARG0)))))",
        "eq(sub(mul(add(add(ARG3, sub(mul(ARG3, ARG1), add(ARG3, ARG3))), mul(mul(sub(ARG2, ARG3), mul(ARG1, ARG3)), ARG2)), mul(add(ARG2, ARG4), mul(ARG3, ARG3))), mul(sub(mul(ARG2, ARG2), add(mul(sub(ARG1, ARG4), mul(ARG2, ARG1)), add(ARG1, ARG1))), add(add(ARG0, ARG4), add(ARG2, ARG4)))), sub(add(sub(sub(ARG4, ARG0), sub(ARG0, ARG1)), mul(ARG2, add(ARG0, ARG3))), mul(sub(mul(ARG2, ARG4), mul(ARG4, ARG0)), sub(sub(ARG0, ARG1), sub(ARG0, ARG2)))))",
        "lt(mul(mul(mul(sub(ARG4, ARG2), mul(add(ARG2, ARG2), ARG2)), mul(sub(ARG1, ARG1), mul(ARG2, ARG2))), mul(add(mul(ARG4, ARG2), sub(ARG3, ARG0)), sub(mul(ARG3, ARG0), sub(ARG1, ARG1)))), mul(mul(ARG3, add(sub(ARG1, add(add(ARG3, ARG0), sub(ARG4, ARG4))), add(ARG0, ARG0))), add(ARG4, ARG2)))",
        "gt(sub(ARG4, ARG4), mul(mul(sub(ARG4, ARG1), mul(ARG3, ARG4)), mul(add(ARG3, ARG2), sub(ARG1, mul(ARG3, mul(mul(ARG3, sub(mul(ARG2, ARG1), mul(ARG3, ARG3))), mul(ARG0, ARG0)))))))",
        "ge(sub(add(sub(ARG1, add(ARG3, ARG4)), mul(ARG0, mul(ARG4, ARG3))), mul(mul(add(ARG1, ARG3), ARG2), add(add(ARG3, ARG1), mul(ARG4, ARG4)))), add(add(sub(mul(ARG3, ARG2), add(ARG1, ARG0)), mul(sub(mul(sub(ARG3, ARG1), mul(ARG3, ARG0)), ARG0), mul(ARG4, mul(sub(mul(mul(add(ARG1, ARG3), mul(ARG2, ARG2)), add(add(ARG1, ARG3), mul(ARG4, ARG4))), ARG1), mul(ARG3, ARG0))))), mul(mul(mul(ARG4, ARG4), sub(ARG1, ARG4)), sub(mul(ARG4, ARG2), ARG1))))",
        "lt(mul(sub(mul(add(ARG3, ARG1), mul(ARG3, ARG2)), mul(ARG0, mul(ARG0, ARG4))), add(mul(ARG3, add(ARG2, mul(ARG4, ARG4))), sub(add(ARG2, ARG3), mul(ARG1, ARG1)))), mul(add(add(sub(ARG4, ARG2), add(ARG4, ARG4)), add(mul(ARG4, ARG0), mul(ARG1, ARG4))), add(ARG1, ARG0)))",
        "gt(mul(add(sub(mul(ARG2, ARG1), sub(ARG2, ARG0)), sub(add(ARG0, ARG1), sub(ARG0, ARG2))), add(add(mul(ARG2, ARG2), sub(ARG4, sub(sub(ARG4, ARG3), add(ARG2, ARG2)))), sub(mul(ARG2, ARG4), add(ARG1, ARG3)))), mul(sub(ARG4, ARG1), mul(ARG3, ARG3)))",
        "gt(mul(sub(ARG3, ARG2), mul(ARG1, add(add(ARG1, ARG1), mul(mul(sub(ARG1, ARG1), ARG4), ARG1)))), add(mul(ARG2, ARG2), mul(ARG4, ARG3)))",
        "ge(mul(mul(sub(add(ARG2, ARG3), add(ARG3, ARG4)), add(sub(ARG0, ARG3), mul(ARG4, ARG0))), mul(add(add(ARG2, ARG0), mul(ARG1, ARG4)), mul(mul(ARG1, ARG0), sub(ARG0, ARG4)))), mul(add(add(add(ARG1, ARG1), sub(ARG2, ARG4)), mul(sub(ARG4, ARG0), add(ARG1, ARG3))), mul(sub(sub(add(ARG3, ARG0), sub(ARG3, ARG4)), sub(ARG4, ARG0)), sub(add(mul(mul(mul(add(sub(ARG3, ARG4), mul(sub(ARG4, ARG0), add(ARG1, ARG3))), mul(sub(sub(add(ARG3, ARG0), sub(ARG3, ARG4)), sub(ARG4, ARG0)), sub(add(mul(mul(ARG2, ARG0), add(ARG0, ARG0)), ARG4), add(ARG3, mul(ARG1, ARG0))))), ARG0), add(ARG0, ARG0)), ARG4), mul(add(add(ARG0, ARG0), add(add(ARG2, ARG4), mul(ARG2, ARG4))), mul(mul(ARG1, ARG0), ARG4)))))",
        "lt(add(sub(add(add(mul(sub(ARG3, ARG0), sub(ARG2, ARG0)), ARG1), sub(ARG4, ARG2)), mul(mul(ARG3, ARG1), sub(ARG1, ARG2))), mul(add(add(ARG2, ARG3), mul(ARG3, ARG2)), sub(mul(ARG0, ARG0), mul(ARG4, ARG0)))), add(sub(add(add(ARG2, ARG0), mul(ARG1, ARG3)), sub(add(ARG1, ARG3), mul(ARG3, ARG2))), sub(add(sub(ARG1, ARG4), mul(ARG2, ARG2)), sub(add(ARG0, ARG0), add(ARG1, ARG0)))))",
        "lt(mul(ARG4, mul(mul(ARG4, ARG4), sub(ARG0, ARG0))), mul(mul(mul(ARG4, ARG1), mul(ARG1, ARG1)), sub(mul(mul(sub(ARG4, ARG2), mul(ARG2, ARG0)), ARG0), mul(ARG4, ARG4))))",
        "lt(mul(sub(sub(ARG2, ARG2), ARG3), sub(sub(ARG1, ARG1), add(ARG1, ARG2))), mul(mul(ARG4, ARG1), add(ARG1, ARG4)))",
        "gt(mul(mul(add(ARG2, ARG4), add(ARG0, ARG4)), add(add(ARG4, ARG0), sub(ARG0, ARG2))), mul(add(ARG1, ARG3), add(ARG3, ARG0)))",
        "gt(mul(add(add(mul(ARG2, ARG4), mul(ARG4, ARG0)), add(sub(ARG2, ARG1), sub(ARG1, ARG1))), add(sub(add(ARG4, ARG2), sub(ARG2, ARG1)), sub(mul(ARG3, ARG0), mul(ARG1, ARG3)))), add(add(add(mul(ARG2, ARG2), mul(ARG4, ARG1)), sub(sub(ARG4, ARG0), sub(ARG1, ARG4))), sub(add(mul(ARG0, ARG2), sub(ARG4, ARG0)), add(sub(ARG4, ARG1), add(ARG1, ARG0)))))",
        "eq(add(mul(ARG1, mul(mul(sub(ARG2, ARG3), sub(ARG0, ARG2)), sub(ARG4, ARG3))), ARG3), mul(add(sub(add(ARG2, ARG2), mul(ARG2, ARG2)), mul(add(ARG2, ARG1), sub(ARG4, add(ARG1, ARG3)))), mul(sub(mul(sub(ARG4, ARG2), ARG4), mul(mul(ARG3, ARG1), mul(ARG1, ARG3))), mul(mul(ARG2, ARG0), sub(ARG1, ARG2)))))",
        "eq(sub(add(mul(add(sub(ARG3, ARG0), ARG1), add(ARG2, ARG0)), add(add(ARG4, ARG1), sub(ARG2, ARG3))), sub(sub(add(ARG1, ARG3), mul(add(ARG0, ARG0), add(ARG2, ARG0))), add(ARG0, mul(ARG4, ARG3)))), add(sub(mul(ARG1, add(ARG0, ARG1)), mul(add(ARG0, ARG1), mul(ARG2, add(mul(sub(sub(ARG1, ARG4), mul(ARG2, ARG1)), ARG1), add(ARG2, ARG2))))), mul(add(mul(ARG1, ARG4), mul(ARG4, ARG4)), mul(add(ARG0, ARG3), mul(ARG0, ARG0)))))",
        "and_(ge(ARG0, mul(sub(sub(add(ARG0, ARG3), sub(ARG2, ARG4)), add(ARG2, ARG3)), mul(mul(add(ARG3, ARG3), mul(ARG4, ARG0)), mul(sub(ARG0, ARG2), mul(ARG3, ARG2))))), and_(lt(sub(mul(add(ARG4, sub(ARG3, ARG1)), mul(mul(ARG3, ARG2), mul(mul(ARG3, ARG0), sub(ARG1, ARG0)))), mul(sub(ARG2, sub(ARG0, ARG4)), mul(mul(ARG0, ARG3), ARG3))), ARG0), ge(sub(add(ARG0, ARG0), add(ARG3, ARG2)), mul(mul(ARG3, ARG3), mul(ARG2, ARG3)))))",
        "and_(and_(gt(add(add(add(add(ARG1, ARG3), ARG3), add(ARG3, ARG1)), add(mul(ARG0, ARG4), sub(ARG0, ARG3))), sub(sub(sub(ARG0, ARG3), add(ARG0, ARG2)), mul(add(ARG2, ARG2), sub(ARG0, ARG2)))), eq(add(mul(add(ARG1, ARG1), mul(ARG1, ARG4)), sub(mul(ARG0, ARG2), mul(ARG3, ARG3))), sub(mul(add(ARG3, ARG1), add(ARG1, ARG3)), sub(mul(ARG4, ARG1), add(ARG3, ARG2))))), and_(gt(add(add(add(add(ARG1, ARG3), ARG3), add(ARG3, ARG1)), add(mul(ARG0, ARG4), sub(ARG0, ARG3))), sub(sub(sub(ARG0, ARG3), add(ARG0, ARG2)), mul(ARG2, sub(ARG0, ARG2)))), and_(gt(add(ARG0, ARG2), sub(sub(sub(ARG0, ARG3), add(ARG0, ARG2)), mul(add(ARG2, ARG2), sub(mul(ARG4, ARG3), add(ARG1, ARG0))))), eq(add(mul(add(ARG1, ARG1), mul(ARG1, ARG4)), sub(mul(ARG0, ARG2), mul(ARG3, ARG3))), sub(mul(add(ARG3, ARG1), add(ARG1, ARG3)), sub(mul(ARG4, ARG1), add(ARG3, ARG2)))))))",
        "and_(and_(ge(sub(sub(ARG2, mul(sub(ARG3, ARG0), mul(ARG3, ARG0))), add(mul(sub(ARG1, ARG4), sub(ARG3, ARG4)), add(sub(ARG2, ARG2), add(ARG2, ARG4)))), sub(mul(mul(add(ARG0, ARG1), mul(ARG4, ARG3)), mul(add(ARG0, ARG1), add(ARG3, ARG0))), add(add(sub(ARG1, ARG4), add(ARG0, ARG3)), mul(sub(ARG0, ARG4), mul(ARG1, ARG1))))), and_(eq(mul(add(sub(ARG0, ARG3), add(ARG4, ARG4)), sub(sub(ARG3, ARG3), mul(ARG1, ARG0))), mul(mul(add(ARG1, ARG2), mul(ARG2, ARG2)), ARG1)), ge(add(mul(mul(ARG1, ARG3), mul(ARG2, ARG0)), add(add(ARG1, ARG3), add(add(sub(ARG0, ARG0), add(ARG3, ARG0)), ARG2))), mul(sub(mul(ARG4, ARG2), mul(ARG3, ARG4)), add(mul(ARG4, ARG3), add(ARG2, ARG4)))))), lt(add(sub(mul(sub(ARG3, ARG1), mul(ARG4, ARG3)), mul(add(add(ARG4, ARG1), mul(ARG3, ARG2)), add(ARG4, ARG2))), add(mul(mul(ARG3, ARG0), mul(ARG3, ARG1)), add(add(ARG3, ARG1), sub(ARG1, ARG1)))), sub(sub(mul(mul(ARG4, ARG2), mul(ARG0, ARG0)), add(add(ARG1, ARG3), add(ARG1, ARG3))), add(sub(sub(ARG0, ARG0), sub(ARG0, ARG1)), mul(sub(ARG4, ARG3), sub(ARG2, ARG4))))))",
        "and_(and_(le(ARG3, ARG2), le(mul(sub(add(add(ARG4, ARG2), add(ARG4, ARG0)), sub(mul(ARG1, ARG2), ARG3)), sub(mul(mul(ARG4, ARG1), add(ARG2, ARG2)), sub(sub(ARG4, ARG4), ARG2))), add(sub(sub(mul(ARG3, ARG0), add(ARG4, ARG2)), add(mul(ARG4, ARG1), sub(ARG4, ARG4))), mul(ARG4, sub(add(ARG2, ARG1), mul(ARG1, ARG0)))))), lt(add(ARG3, mul(mul(mul(ARG4, ARG0), mul(ARG1, ARG3)), mul(add(add(mul(ARG4, mul(ARG4, ARG0)), add(ARG2, ARG3)), ARG0), sub(ARG3, ARG2)))), sub(mul(add(sub(add(ARG4, ARG0), add(ARG4, ARG0)), sub(ARG4, ARG3)), mul(sub(ARG3, ARG2), ARG3)), add(mul(mul(ARG2, mul(mul(ARG2, ARG4), sub(ARG0, ARG2))), sub(ARG2, ARG2)), add(mul(ARG3, ARG1), mul(ARG1, ARG0))))))",
        "and_(and_(and_(and_(le(mul(ARG1, ARG3), sub(ARG1, ARG1)), le(mul(mul(sub(ARG3, ARG1), ARG3), sub(ARG3, mul(ARG3, ARG0))), add(mul(add(ARG2, ARG0), mul(ARG1, ARG4)), mul(mul(ARG0, add(ARG0, ARG0)), mul(ARG4, ARG2))))), gt(mul(add(ARG4, ARG3), add(ARG0, ARG3)), ARG1)), ge(mul(sub(mul(sub(ARG2, ARG3), mul(ARG2, ARG1)), add(mul(ARG3, ARG1), add(ARG0, ARG1))), mul(sub(mul(ARG0, ARG4), add(ARG1, ARG3)), ARG2)), add(add(add(add(ARG1, ARG2), add(ARG2, ARG2)), sub(mul(ARG1, ARG1), add(ARG1, ARG3))), add(sub(mul(ARG0, ARG3), sub(ARG4, ARG4)), ARG3)))), and_(and_(and_(and_(le(sub(ARG2, ARG4), sub(ARG1, ARG1)), le(mul(mul(sub(ARG3, ARG1), ARG3), sub(mul(ARG4, ARG4), mul(ARG3, ARG0))), add(mul(add(ARG2, ARG0), mul(ARG1, ARG4)), mul(mul(ARG0, add(ARG0, ARG0)), mul(ARG4, ARG2))))), gt(mul(add(ARG4, ARG3), add(ARG0, ARG3)), ARG1)), and_(and_(le(mul(ARG1, ARG3), ARG0), le(mul(mul(sub(ARG3, ARG1), add(ARG4, ARG3)), sub(mul(ARG4, ARG4), mul(ARG3, ARG0))), add(mul(add(ARG2, ARG0), mul(ARG1, ARG4)), mul(mul(ARG0, add(ARG0, ARG0)), mul(ARG4, ARG2))))), gt(mul(add(ARG4, ARG3), add(ARG0, ARG3)), mul(mul(ARG2, ARG0), mul(ARG2, mul(mul(ARG2, ARG4), mul(ARG3, ARG3))))))), ge(add(add(ARG2, ARG4), sub(ARG0, ARG0)), add(add(add(add(add(ARG2, ARG0), add(ARG0, ARG3)), add(ARG2, ARG2)), sub(sub(ARG0, ARG2), mul(ARG3, ARG3))), add(sub(mul(ARG0, ARG3), sub(ARG4, ARG4)), sub(add(ARG2, ARG0), mul(ARG0, ARG1)))))))",
        "and_(and_(eq(mul(add(sub(add(ARG4, ARG1), sub(ARG3, ARG0)), sub(sub(ARG1, ARG2), add(add(ARG0, ARG3), mul(ARG3, ARG4)))), add(sub(add(ARG4, ARG2), add(ARG3, ARG2)), sub(sub(ARG2, ARG0), add(ARG1, ARG4)))), ARG4), lt(add(ARG3, ARG3), sub(ARG3, ARG3))), and_(and_(eq(mul(add(sub(add(ARG4, ARG4), sub(ARG3, ARG0)), sub(sub(sub(add(ARG0, ARG0), mul(ARG2, ARG4)), ARG2), sub(ARG1, ARG1))), add(sub(add(ARG4, ARG2), add(ARG3, ARG2)), sub(sub(ARG2, ARG0), add(ARG1, ARG4)))), sub(ARG1, ARG2)), lt(add(ARG3, ARG3), sub(ARG3, ARG3))), lt(add(ARG3, ARG3), sub(ARG3, ARG3))))",
        "and_(ge(mul(mul(sub(add(ARG4, ARG3), mul(ARG3, ARG0)), add(mul(ARG0, ARG3), mul(ARG3, ARG2))), add(sub(add(ARG3, ARG4), sub(ARG3, ARG3)), sub(ARG3, ARG1))), mul(mul(mul(mul(ARG3, ARG3), mul(ARG2, ARG0)), sub(sub(ARG1, ARG2), add(ARG1, ARG3))), add(mul(add(ARG4, ARG0), add(ARG1, ARG3)), mul(mul(ARG3, ARG1), mul(ARG0, ARG1))))), and_(and_(gt(add(sub(mul(mul(ARG4, ARG0), add(ARG0, ARG3)), add(add(ARG4, ARG4), add(ARG1, ARG4))), mul(add(sub(ARG1, ARG0), sub(ARG2, ARG1)), mul(sub(ARG3, ARG4), add(ARG2, ARG0)))), mul(add(ARG0, ARG4), add(sub(sub(ARG3, ARG0), mul(ARG1, ARG3)), sub(mul(ARG1, ARG0), add(ARG1, ARG3))))), ge(mul(mul(sub(add(ARG4, ARG3), mul(ARG3, ARG0)), add(mul(ARG0, ARG3), mul(ARG3, ARG2))), add(sub(add(ARG3, ARG4), sub(ARG3, ARG3)), mul(sub(ARG1, ARG0), add(ARG2, ARG2)))), mul(mul(mul(mul(ARG3, ARG3), mul(ARG2, ARG0)), sub(sub(ARG1, ARG2), add(ARG1, ARG3))), add(mul(add(ARG4, ARG0), add(ARG1, ARG3)), mul(mul(ARG3, ARG1), mul(ARG0, ARG1)))))), and_(gt(add(sub(mul(mul(ARG4, ARG0), add(ARG0, ARG3)), add(add(ARG4, ARG4), add(ARG1, ARG4))), mul(add(sub(ARG1, ARG0), sub(ARG2, ARG1)), mul(sub(ARG3, ARG4), add(ARG4, ARG0)))), mul(sub(mul(mul(ARG0, ARG4), mul(ARG1, ARG3)), mul(add(ARG3, ARG2), add(ARG0, ARG0))), add(sub(sub(ARG3, ARG0), mul(ARG1, ARG3)), sub(mul(ARG1, add(ARG3, ARG4)), add(ARG1, ARG3))))), ge(mul(mul(sub(add(ARG4, ARG3), mul(ARG3, ARG0)), add(mul(ARG0, ARG3), mul(ARG3, ARG2))), add(sub(add(ARG3, ARG4), sub(ARG3, ARG3)), mul(sub(ARG1, ARG0), mul(ARG3, ARG2)))), mul(mul(mul(mul(ARG3, ARG3), mul(ARG2, ARG0)), sub(sub(ARG1, ARG2), add(ARG1, ARG3))), add(mul(add(ARG4, ARG0), add(ARG1, ARG3)), mul(mul(mul(ARG3, sub(sub(ARG4, ARG4), mul(ARG4, ARG1))), mul(ARG2, ARG1)), mul(ARG0, ARG1))))))))",
        "and_(lt(add(mul(add(add(ARG3, ARG4), add(ARG1, ARG3)), mul(mul(ARG3, mul(mul(ARG3, ARG1), sub(ARG0, ARG4))), add(ARG0, ARG2))), add(add(add(ARG2, ARG0), add(ARG3, ARG3)), sub(mul(ARG1, ARG0), mul(ARG1, ARG4)))), sub(add(mul(sub(ARG2, ARG4), sub(ARG4, ARG1)), add(sub(ARG1, ARG4), mul(ARG1, ARG2))), mul(sub(add(ARG3, ARG0), sub(ARG3, ARG3)), mul(add(ARG0, ARG3), add(ARG0, ARG2))))), le(mul(sub(sub(sub(ARG2, ARG3), add(ARG0, ARG1)), add(sub(ARG1, ARG4), sub(ARG1, ARG3))), sub(mul(add(ARG1, ARG0), sub(ARG1, ARG0)), add(sub(ARG0, ARG2), sub(ARG0, ARG2)))), sub(sub(sub(sub(ARG0, mul(ARG3, ARG1)), add(ARG0, ARG1)), sub(add(ARG4, ARG2), mul(ARG1, ARG3))), sub(add(sub(ARG3, ARG2), sub(ARG4, ARG0)), add(sub(ARG0, ARG3), sub(ARG1, ARG3))))))",
        "and_(lt(mul(sub(add(ARG2, ARG3), mul(ARG3, ARG2)), ARG1), mul(ARG4, ARG2)), eq(mul(mul(mul(ARG0, ARG2), sub(ARG1, ARG2)), sub(mul(ARG4, add(ARG4, ARG3)), mul(ARG4, ARG4))), add(add(mul(ARG2, ARG1), sub(ARG0, ARG4)), sub(mul(ARG0, ARG2), add(ARG1, ARG4)))))",
        "and_(gt(sub(sub(add(add(ARG1, ARG1), mul(ARG4, ARG4)), sub(add(ARG2, ARG1), mul(sub(ARG1, ARG2), sub(ARG2, ARG0)))), add(sub(add(ARG3, ARG4), sub(ARG1, ARG1)), add(mul(ARG2, ARG2), sub(ARG3, ARG1)))), sub(mul(add(sub(ARG1, ARG3), sub(ARG4, ARG0)), sub(sub(ARG1, ARG2), add(ARG3, ARG0))), mul(mul(ARG2, ARG1), sub(sub(ARG3, ARG0), mul(ARG0, ARG0))))), and_(eq(mul(sub(mul(ARG4, ARG1), mul(ARG2, ARG3)), mul(sub(ARG2, ARG1), sub(ARG4, ARG3))), mul(sub(sub(sub(ARG3, ARG4), ARG1), sub(ARG3, ARG1)), mul(mul(ARG2, ARG1), sub(ARG4, ARG0)))), gt(sub(sub(add(add(ARG1, ARG1), mul(ARG4, ARG4)), sub(add(ARG2, ARG1), mul(ARG0, ARG2))), add(sub(add(ARG3, ARG4), sub(ARG1, ARG0)), add(mul(add(mul(add(ARG4, ARG0), mul(ARG4, ARG3)), add(sub(ARG2, ARG1), mul(ARG1, ARG0))), ARG2), sub(ARG3, ARG1)))), sub(mul(add(sub(ARG1, ARG3), sub(ARG4, ARG0)), sub(sub(ARG1, ARG2), add(ARG3, ARG0))), mul(mul(mul(ARG2, ARG0), sub(ARG0, ARG2)), ARG1)))))",
        "and_(le(sub(add(mul(ARG0, ARG1), sub(sub(ARG4, ARG1), sub(ARG0, ARG4))), mul(mul(mul(ARG0, ARG1), add(ARG2, ARG1)), add(add(ARG3, ARG2), add(ARG2, ARG2)))), mul(mul(ARG2, ARG2), mul(mul(add(ARG3, ARG4), sub(ARG2, ARG0)), sub(mul(ARG0, sub(sub(ARG4, ARG1), add(mul(ARG1, ARG3), ARG3))), ARG3)))), and_(and_(ge(ARG3, ARG2), le(add(add(mul(ARG3, ARG4), mul(ARG1, ARG2)), sub(sub(ARG4, ARG0), add(ARG4, ARG3))), sub(sub(mul(ARG2, add(ARG3, ARG4)), mul(ARG3, ARG3)), sub(mul(ARG2, ARG3), sub(add(ARG4, ARG0), add(ARG3, ARG1)))))), and_(le(add(ARG1, ARG3), mul(mul(ARG2, ARG2), mul(mul(add(ARG3, ARG4), sub(ARG2, ARG0)), sub(mul(ARG0, sub(mul(ARG1, ARG4), sub(ARG2, ARG0))), ARG3)))), gt(add(sub(mul(mul(ARG0, ARG4), add(ARG4, ARG3)), add(sub(ARG3, ARG4), mul(sub(ARG2, ARG2), add(ARG3, ARG2)))), add(sub(add(ARG3, ARG4), mul(ARG1, ARG3)), add(add(ARG0, ARG0), sub(ARG3, ARG0)))), add(sub(mul(sub(ARG3, ARG4), mul(ARG4, ARG2)), add(add(ARG2, ARG0), sub(ARG1, ARG2))), add(mul(mul(ARG1, ARG4), mul(ARG1, ARG4)), mul(sub(ARG4, ARG3), sub(ARG0, ARG0))))))))",
        "and_(and_(gt(mul(mul(mul(ARG3, ARG4), add(ARG2, ARG0)), mul(add(ARG2, ARG4), add(ARG1, ARG4))), mul(mul(mul(ARG3, ARG3), sub(ARG3, ARG0)), add(sub(ARG4, ARG0), sub(ARG0, ARG0)))), and_(gt(mul(add(sub(sub(ARG0, ARG0), sub(ARG1, ARG2)), add(mul(ARG2, ARG2), add(ARG4, ARG2))), mul(sub(sub(ARG1, ARG0), sub(ARG3, ARG2)), mul(mul(ARG1, ARG3), mul(ARG0, ARG1)))), sub(add(mul(add(ARG2, ARG1), mul(ARG0, ARG1)), sub(add(ARG1, ARG4), sub(ARG1, ARG1))), sub(sub(sub(ARG4, ARG3), mul(ARG1, ARG3)), sub(sub(ARG0, ARG4), sub(ARG3, ARG3))))), and_(gt(mul(mul(mul(ARG3, ARG4), add(ARG2, ARG0)), mul(add(ARG2, ARG4), add(ARG1, ARG4))), mul(mul(mul(ARG3, ARG3), sub(ARG3, ARG0)), add(sub(ARG4, ARG0), sub(ARG0, ARG0)))), and_(gt(mul(add(sub(sub(ARG0, ARG0), sub(ARG1, ARG2)), add(mul(ARG2, ARG2), add(ARG4, ARG2))), mul(sub(sub(ARG1, ARG0), sub(ARG3, ARG2)), mul(mul(ARG1, ARG3), mul(ARG0, ARG1)))), sub(add(mul(add(ARG2, ARG1), mul(ARG0, ARG1)), sub(add(ARG1, ARG4), sub(ARG1, ARG1))), sub(sub(sub(ARG4, ARG3), mul(ARG1, ARG3)), sub(sub(ARG0, ARG4), sub(ARG3, ARG3))))), eq(sub(mul(mul(add(ARG2, ARG4), add(ARG2, ARG0)), add(mul(ARG2, ARG1), mul(ARG2, ARG4))), add(sub(sub(ARG4, ARG1), sub(ARG0, ARG4)), sub(sub(ARG2, ARG0), sub(ARG2, ARG2)))), add(sub(mul(sub(ARG0, ARG0), mul(ARG4, ARG2)), mul(add(ARG2, ARG3), mul(ARG2, ARG4))), add(sub(sub(ARG2, add(sub(add(add(ARG4, ARG1), add(ARG2, ARG1)), add(sub(ARG0, sub(add(ARG2, ARG1), add(ARG3, ARG0))), sub(ARG1, ARG0))), mul(mul(mul(ARG2, ARG3), add(ARG1, ARG3)), mul(mul(ARG2, ARG4), sub(add(ARG1, ARG4), mul(ARG3, ARG1)))))), add(ARG0, ARG0)), mul(add(ARG3, ARG1), mul(ARG2, ARG1))))))))), gt(mul(mul(sub(ARG1, ARG4), mul(ARG0, ARG4)), mul(add(mul(add(ARG2, ARG2), add(ARG3, ARG3)), ARG4), add(ARG1, ARG4))), mul(sub(sub(add(add(ARG2, ARG0), add(ARG1, ARG2)), ARG4), sub(ARG4, ARG4)), add(sub(ARG4, ARG0), sub(ARG0, ARG0)))))",
        "and_(and_(le(mul(mul(add(ARG4, ARG4), mul(ARG1, ARG1)), add(add(ARG0, ARG2), add(ARG4, ARG0))), mul(add(sub(ARG4, ARG1), add(ARG1, ARG0)), mul(add(ARG1, ARG1), mul(ARG2, ARG3)))), le(add(sub(ARG1, ARG2), add(mul(sub(ARG0, ARG3), add(ARG0, ARG3)), add(add(ARG3, ARG2), add(ARG0, ARG2)))), add(add(add(sub(ARG1, ARG3), sub(ARG0, ARG1)), mul(add(ARG2, ARG3), sub(ARG3, ARG4))), sub(add(mul(ARG3, ARG4), sub(ARG4, ARG1)), mul(mul(ARG2, ARG2), mul(sub(ARG4, ARG4), add(ARG0, ARG4))))))), and_(le(sub(sub(ARG3, ARG4), add(sub(mul(ARG2, ARG1), mul(ARG2, ARG3)), ARG3)), mul(sub(ARG3, ARG4), sub(ARG1, ARG1))), and_(True, gt(sub(add(add(add(sub(ARG3, ARG3), ARG2), mul(ARG3, ARG2)), add(add(ARG2, ARG3), sub(ARG2, ARG1))), mul(mul(add(ARG4, ARG3), sub(ARG1, ARG0)), add(add(ARG2, ARG0), sub(ARG1, ARG4)))), add(add(sub(add(ARG2, ARG0), sub(ARG3, ARG1)), sub(add(ARG4, ARG4), sub(ARG1, ARG0))), mul(add(sub(ARG3, ARG2), mul(ARG3, ARG4)), mul(sub(ARG4, ARG0), sub(ARG1, ARG3))))))))",
        "gt(sub(sub(sub(mul(ARG0, ARG4), mul(ARG0, ARG4)), mul(add(ARG2, ARG0), add(ARG0, ARG2))), sub(add(add(ARG3, ARG1), sub(ARG4, ARG3)), sub(sub(ARG0, ARG0), sub(ARG0, ARG3)))), add(mul(ARG1, ARG1), add(sub(sub(ARG3, ARG0), mul(ARG4, ARG2)), mul(add(ARG3, ARG4), add(ARG2, ARG1)))))",
        "and_(and_(gt(sub(mul(mul(mul(ARG4, ARG0), add(ARG2, ARG3)), add(mul(ARG1, ARG2), mul(ARG2, ARG2))), sub(sub(mul(ARG1, ARG4), add(ARG4, ARG2)), sub(mul(ARG0, ARG2), add(ARG3, mul(mul(ARG1, ARG3), sub(ARG0, ARG4)))))), sub(mul(add(add(ARG3, ARG3), add(ARG0, ARG2)), sub(sub(ARG1, ARG0), mul(ARG3, ARG2))), sub(add(mul(ARG1, ARG2), mul(ARG2, ARG3)), add(ARG0, ARG3)))), and_(ge(add(add(sub(ARG1, ARG4), sub(ARG4, ARG0)), sub(sub(ARG2, ARG1), sub(ARG2, ARG3))), add(mul(add(ARG1, ARG0), mul(ARG0, ARG2)), mul(add(ARG1, ARG2), mul(ARG1, ARG3)))), eq(add(ARG1, ARG3), add(ARG2, ARG3)))), and_(le(mul(add(add(ARG0, ARG3), mul(ARG2, ARG1)), mul(mul(ARG0, ARG0), sub(ARG2, ARG3))), sub(add(add(ARG0, ARG3), add(ARG2, ARG1)), add(add(ARG2, ARG2), sub(add(ARG3, ARG0), ARG1)))), eq(add(mul(ARG3, mul(ARG0, ARG2)), sub(ARG4, ARG0)), mul(mul(ARG4, ARG2), mul(ARG0, ARG4)))))",
        "and_(eq(add(mul(ARG2, ARG1), mul(ARG4, ARG4)), mul(mul(ARG1, ARG3), add(ARG3, ARG0))), and_(eq(add(mul(ARG2, ARG1), mul(ARG4, ARG4)), mul(mul(ARG1, ARG3), add(ARG3, ARG0))), gt(add(ARG2, ARG2), sub(ARG0, ARG4))))",
        "and_(and_(eq(mul(sub(add(ARG0, ARG4), mul(add(sub(ARG1, ARG2), add(ARG2, ARG1)), sub(ARG4, ARG3))), add(mul(ARG1, ARG0), add(ARG0, ARG2))), sub(mul(sub(ARG1, ARG0), add(ARG4, ARG0)), mul(mul(ARG4, ARG2), sub(ARG4, ARG0)))), and_(gt(mul(ARG3, ARG1), add(ARG4, ARG3)), le(mul(add(sub(ARG3, ARG2), sub(ARG1, ARG2)), mul(add(ARG2, ARG4), mul(ARG3, sub(sub(ARG0, ARG0), mul(ARG3, ARG0))))), add(sub(sub(add(ARG4, ARG2), ARG2), sub(ARG3, ARG3)), add(add(ARG3, ARG3), sub(ARG0, ARG0)))))), and_(eq(mul(sub(add(ARG0, ARG4), mul(add(sub(ARG1, ARG2), add(ARG2, ARG1)), sub(ARG4, ARG3))), add(mul(ARG1, ARG0), add(ARG0, ARG2))), sub(mul(sub(ARG1, ARG0), add(ARG4, ARG0)), mul(mul(ARG4, ARG2), sub(ARG4, ARG0)))), and_(gt(mul(ARG3, ARG1), add(ARG4, ARG3)), le(mul(add(sub(ARG3, mul(ARG1, ARG4)), sub(ARG1, ARG2)), mul(add(ARG2, ARG4), mul(ARG3, sub(sub(ARG0, ARG0), ARG2)))), add(sub(sub(add(ARG4, ARG2), ARG2), sub(ARG3, ARG3)), add(add(ARG3, ARG3), sub(ARG0, ARG0)))))))",
        "and_(and_(ge(mul(add(mul(ARG1, ARG1), mul(ARG1, ARG4)), mul(sub(ARG2, ARG4), add(mul(ARG3, ARG2), ARG3))), add(add(ARG0, ARG1), sub(add(ARG2, ARG2), sub(ARG4, mul(ARG0, ARG3))))), ge(add(ARG4, ARG3), sub(ARG0, ARG2))), and_(and_(ge(mul(add(mul(ARG1, ARG1), mul(sub(ARG3, ARG2), ARG4)), mul(sub(ARG2, ARG4), add(ARG2, ARG3))), add(add(ARG4, ARG1), sub(add(ARG2, ARG2), sub(ARG4, mul(ARG0, ARG3))))), ge(add(ARG4, ARG3), sub(ARG0, ARG2))), gt(ARG4, ARG3)))",
        "and_(and_(le(sub(ARG1, ARG0), sub(sub(ARG0, ARG1), ARG1)), ge(add(mul(mul(ARG0, ARG0), sub(ARG2, ARG4)), mul(mul(ARG1, ARG4), add(mul(ARG2, ARG2), ARG3))), mul(sub(sub(ARG1, ARG0), sub(ARG1, ARG0)), sub(mul(ARG3, ARG2), sub(ARG4, ARG1))))), and_(and_(gt(mul(sub(sub(ARG0, ARG3), add(mul(add(ARG0, ARG4), sub(ARG4, ARG2)), ARG3)), sub(mul(ARG4, ARG1), add(ARG1, ARG2))), mul(mul(sub(ARG2, ARG0), add(add(ARG0, ARG1), sub(ARG4, ARG0))), add(mul(ARG4, ARG0), add(ARG1, ARG3)))), le(sub(ARG1, ARG0), sub(sub(ARG0, ARG4), ARG1))), le(mul(mul(ARG3, ARG4), sub(ARG4, ARG4)), sub(sub(ARG0, ARG1), ARG1))))",
        "and_(eq(mul(ARG4, ARG2), add(sub(mul(ARG2, ARG4), add(ARG4, ARG2)), add(mul(ARG1, ARG2), mul(add(ARG3, ARG0), ARG1)))), and_(lt(mul(ARG4, ARG0), mul(ARG1, ARG0)), eq(mul(ARG0, ARG2), add(sub(mul(ARG2, sub(sub(ARG0, ARG0), mul(ARG0, ARG1))), add(ARG0, ARG2)), add(sub(sub(ARG2, ARG1), add(ARG2, ARG2)), mul(add(ARG3, ARG0), ARG1))))))",
        "ge(add(sub(sub(mul(ARG0, ARG1), mul(ARG4, ARG1)), sub(sub(ARG4, ARG3), sub(ARG2, ARG4))), sub(ARG2, mul(sub(sub(mul(ARG0, ARG1), mul(ARG4, ARG1)), sub(sub(ARG4, ARG4), sub(ARG2, ARG2))), add(ARG2, ARG1)))), mul(mul(add(mul(ARG0, ARG4), mul(ARG4, ARG4)), sub(add(ARG3, ARG4), add(ARG4, ARG1))), add(add(add(ARG1, ARG4), mul(mul(ARG3, ARG4), mul(ARG2, ARG4))), mul(mul(ARG1, mul(ARG1, ARG4)), mul(mul(ARG1, ARG4), sub(mul(ARG0, ARG1), sub(mul(ARG2, ARG3), sub(ARG3, ARG0))))))))",
        "gt(mul(mul(mul(ARG4, ARG3), sub(ARG3, ARG3)), mul(mul(ARG4, ARG3), sub(ARG3, ARG3))), mul(mul(mul(mul(ARG0, ARG2), sub(ARG0, ARG3)), mul(ARG2, ARG3)), add(mul(mul(ARG1, ARG1), ARG2), mul(ARG1, sub(mul(ARG3, ARG1), mul(ARG4, ARG0))))))",
        "lt(mul(mul(ARG0, add(ARG0, ARG2)), mul(add(ARG1, ARG3), add(ARG4, ARG3))), mul(ARG1, sub(add(mul(ARG0, ARG1), add(ARG0, ARG2)), add(mul(ARG1, mul(ARG4, ARG3)), add(ARG3, ARG4)))))",
        "gt(mul(sub(add(add(ARG4, ARG0), sub(ARG1, ARG3)), add(mul(ARG1, ARG3), add(ARG0, ARG2))), mul(sub(mul(ARG2, ARG3), mul(ARG4, ARG1)), add(add(ARG2, ARG1), sub(ARG3, ARG0)))), mul(add(ARG2, sub(add(sub(ARG3, ARG4), mul(ARG4, ARG1)), add(add(ARG2, ARG1), add(ARG2, ARG1)))), mul(add(mul(ARG0, ARG1), mul(ARG2, ARG3)), sub(mul(ARG2, ARG3), add(ARG3, ARG4)))))",
        "gt(add(mul(ARG4, mul(mul(ARG1, mul(sub(ARG4, ARG4), sub(ARG1, ARG1))), add(ARG3, ARG1))), mul(mul(mul(ARG3, ARG2), sub(ARG2, ARG0)), mul(sub(ARG0, ARG1), mul(ARG4, ARG0)))), add(add(mul(mul(ARG0, ARG0), sub(ARG0, ARG2)), mul(sub(mul(ARG3, ARG3), ARG0), mul(ARG3, ARG3))), add(mul(sub(ARG1, ARG4), add(ARG4, ARG2)), mul(sub(ARG3, ARG0), mul(add(ARG4, ARG1), sub(mul(ARG4, ARG4), mul(mul(ARG4, ARG2), add(mul(ARG2, ARG3), mul(ARG1, ARG0)))))))))",
        "eq(add(sub(mul(ARG3, ARG0), add(ARG0, ARG1)), ARG4), mul(mul(mul(ARG0, ARG4), mul(ARG1, ARG0)), add(mul(mul(mul(ARG1, ARG2), mul(ARG2, ARG3)), add(mul(ARG2, mul(ARG1, ARG1)), add(ARG2, ARG3))), add(mul(ARG0, ARG4), mul(mul(ARG3, ARG4), add(mul(ARG0, ARG1), mul(mul(ARG3, ARG2), add(mul(ARG0, ARG4), mul(ARG0, mul(ARG1, ARG2))))))))))",
        "lt(mul(add(add(sub(ARG0, ARG2), add(ARG3, ARG0)), add(mul(ARG4, ARG3), add(ARG3, ARG3))), mul(add(add(ARG2, ARG0), sub(ARG0, ARG4)), sub(add(ARG1, ARG4), add(ARG3, ARG1)))), mul(add(mul(ARG1, ARG2), sub(ARG3, ARG4)), add(mul(ARG0, ARG1), sub(mul(ARG0, sub(ARG4, ARG1)), add(ARG2, ARG3)))))",
        "le(add(sub(sub(mul(ARG4, ARG3), sub(ARG2, ARG3)), mul(add(ARG2, ARG4), sub(ARG1, ARG4))), mul(sub(mul(ARG2, ARG0), add(ARG1, add(ARG1, ARG1))), add(sub(ARG0, ARG4), add(ARG0, ARG1)))), sub(mul(add(sub(ARG2, ARG2), sub(ARG0, ARG1)), mul(ARG2, ARG0)), add(mul(sub(ARG0, ARG0), sub(ARG4, ARG0)), mul(mul(ARG3, ARG0), add(mul(ARG1, ARG4), sub(mul(ARG4, ARG3), mul(mul(ARG3, ARG1), mul(ARG4, mul(mul(ARG4, ARG4), ARG4)))))))))",
        "gt(add(sub(sub(sub(ARG2, ARG1), mul(ARG2, ARG4)), add(sub(ARG4, ARG1), sub(ARG2, ARG3))), sub(sub(sub(ARG4, ARG0), mul(ARG1, mul(ARG1, ARG3))), sub(sub(ARG1, ARG0), sub(ARG3, ARG4)))), add(mul(mul(mul(ARG3, ARG4), add(ARG4, ARG3)), mul(add(ARG4, ARG4), add(ARG2, ARG0))), add(sub(add(ARG0, ARG4), add(ARG0, ARG3)), add(mul(ARG1, ARG1), add(mul(ARG1, ARG1), mul(mul(ARG2, ARG2), mul(ARG2, ARG2)))))))",
        "ge(add(add(mul(mul(ARG1, ARG1), sub(ARG3, ARG3)), sub(sub(ARG4, ARG2), sub(ARG2, ARG0))), mul(sub(sub(ARG0, ARG1), sub(ARG1, ARG2)), mul(sub(ARG1, ARG3), mul(ARG1, ARG0)))), add(add(mul(add(ARG4, ARG3), add(ARG4, ARG0)), sub(mul(ARG1, ARG3), sub(ARG4, ARG1))), add(sub(mul(ARG2, ARG3), sub(ARG3, ARG2)), add(add(mul(add(mul(ARG4, ARG4), sub(ARG3, ARG3)), add(mul(ARG4, ARG4), sub(ARG3, ARG3))), add(mul(ARG4, ARG0), add(ARG0, ARG0))), mul(mul(mul(ARG2, ARG0), mul(ARG2, ARG0)), mul(mul(mul(mul(ARG2, ARG0), mul(ARG2, ARG0)), mul(ARG2, ARG0)), mul(mul(ARG2, ARG0), mul(ARG2, ARG0))))))))",
        "eq(mul(mul(sub(ARG0, ARG3), mul(ARG1, ARG2)), mul(add(ARG2, ARG2), mul(ARG0, ARG3))), mul(mul(sub(ARG3, ARG4), add(ARG3, ARG3)), add(mul(mul(sub(ARG0, ARG3), mul(ARG1, ARG4)), mul(add(ARG2, ARG2), mul(ARG0, ARG3))), ARG1)))",
        "le(mul(mul(ARG1, add(mul(ARG4, ARG2), mul(ARG2, ARG4))), mul(add(add(ARG3, ARG2), add(ARG0, ARG1)), add(mul(ARG0, ARG4), add(ARG0, ARG0)))), add(mul(ARG2, ARG4), mul(ARG1, sub(sub(mul(ARG3, ARG3), mul(ARG3, ARG3)), mul(mul(ARG2, ARG4), mul(add(add(ARG3, ARG2), add(ARG0, ARG1)), mul(ARG1, add(ARG0, ARG1))))))))",
        "gt(mul(mul(sub(sub(ARG1, ARG3), add(ARG1, ARG2)), sub(sub(ARG1, ARG4), sub(ARG4, ARG0))), sub(sub(add(ARG0, ARG4), sub(ARG2, ARG1)), sub(add(ARG4, ARG1), mul(ARG1, ARG2)))), mul(sub(add(add(ARG3, ARG0), mul(ARG3, ARG4)), sub(ARG3, ARG0)), mul(sub(sub(ARG2, ARG4), mul(ARG2, ARG3)), mul(sub(ARG1, ARG3), mul(sub(mul(ARG0, ARG1), mul(ARG4, ARG4)), ARG1)))))",
        "lt(add(mul(ARG0, ARG1), mul(ARG2, ARG4)), sub(mul(mul(mul(ARG0, ARG1), sub(ARG2, ARG1)), mul(ARG4, ARG3)), add(mul(mul(ARG2, ARG2), add(ARG0, ARG1)), mul(ARG0, mul(ARG1, ARG4)))))",
        "lt(mul(add(mul(mul(ARG3, ARG4), add(ARG2, ARG4)), mul(mul(ARG3, ARG1), add(ARG1, ARG0))), sub(add(add(ARG4, ARG1), mul(ARG0, ARG4)), add(add(ARG1, ARG0), add(ARG3, ARG3)))), mul(sub(sub(mul(ARG0, ARG0), sub(ARG4, ARG0)), sub(sub(mul(ARG4, ARG1), mul(ARG3, ARG4)), add(ARG3, ARG0))), sub(mul(mul(ARG0, ARG0), mul(ARG1, ARG4)), mul(mul(ARG0, ARG1), sub(ARG1, ARG4)))))",
        "gt(add(sub(mul(sub(ARG1, ARG1), sub(ARG3, ARG3)), mul(mul(ARG4, ARG3), sub(ARG2, ARG0))), add(ARG0, sub(add(ARG4, ARG2), mul(ARG0, ARG0)))), mul(sub(mul(add(mul(ARG0, ARG4), mul(ARG1, ARG0)), mul(add(ARG0, ARG1), sub(ARG2, ARG3))), add(mul(ARG0, ARG1), mul(ARG0, ARG3))), sub(sub(add(ARG3, ARG2), mul(ARG0, ARG4)), add(add(ARG2, ARG0), mul(mul(ARG3, ARG1), sub(mul(ARG4, ARG2), ARG2))))))",
        "lt(mul(add(mul(ARG3, ARG1), mul(ARG2, ARG0)), mul(sub(ARG1, ARG0), sub(ARG1, ARG3))), mul(add(add(mul(ARG4, ARG3), sub(ARG4, ARG3)), mul(ARG1, ARG3)), mul(mul(ARG1, ARG3), mul(sub(ARG3, ARG2), add(ARG2, ARG2)))))",
        "lt(mul(ARG1, ARG4), mul(sub(mul(ARG2, ARG4), sub(mul(ARG2, ARG4), add(ARG3, ARG4))), sub(add(mul(ARG4, ARG1), mul(ARG1, ARG4)), sub(add(ARG3, ARG2), mul(mul(ARG1, ARG0), add(mul(ARG4, ARG4), add(mul(ARG0, ARG1), mul(ARG2, ARG3))))))))",
        "gt(mul(mul(mul(ARG1, ARG2), mul(ARG3, ARG4)), mul(mul(ARG2, ARG2), add(ARG4, ARG1))), mul(mul(mul(mul(ARG1, ARG2), sub(ARG2, ARG4)), ARG4), sub(mul(mul(ARG3, ARG4), ARG4), mul(mul(add(mul(ARG2, ARG1), ARG1), mul(ARG4, ARG3)), sub(ARG1, ARG1)))))",
        "gt(add(mul(mul(add(ARG2, ARG4), sub(ARG1, ARG3)), sub(sub(ARG4, ARG2), mul(ARG4, ARG0))), mul(sub(add(ARG3, ARG4), sub(ARG1, ARG1)), mul(sub(ARG3, ARG1), add(ARG4, ARG4)))), sub(mul(sub(mul(mul(ARG2, ARG2), mul(sub(add(ARG4, ARG3), sub(ARG2, ARG2)), add(mul(ARG3, ARG3), sub(ARG2, add(ARG2, ARG4))))), sub(ARG2, ARG2)), add(mul(ARG3, ARG3), sub(ARG2, ARG1))), mul(mul(sub(ARG4, ARG1), add(ARG3, ARG0)), add(sub(ARG4, ARG2), add(ARG1, mul(ARG4, mul(ARG4, mul(ARG4, mul(ARG4, mul(ARG4, mul(ARG4, ARG0)))))))))))",
        "le(mul(mul(mul(mul(ARG1, ARG2), mul(ARG4, ARG4)), sub(sub(ARG4, ARG1), mul(ARG4, ARG1))), add(mul(sub(sub(ARG0, ARG0), mul(ARG4, ARG0)), mul(sub(ARG3, ARG2), mul(ARG4, ARG1))), mul(sub(mul(ARG0, ARG0), add(ARG1, ARG1)), sub(add(sub(ARG4, ARG1), add(ARG4, ARG1)), add(ARG2, ARG3))))), add(mul(ARG0, ARG1), sub(ARG2, ARG4)))",
        "lt(mul(mul(ARG2, ARG1), mul(sub(add(ARG0, ARG3), mul(ARG3, mul(ARG4, ARG3))), add(add(add(ARG4, ARG3), ARG4), sub(ARG2, ARG2)))), mul(mul(add(ARG1, add(add(ARG2, ARG0), add(ARG2, ARG4))), mul(ARG2, ARG0)), add(sub(ARG3, ARG2), mul(ARG0, ARG3))))",
        "le(mul(mul(mul(add(ARG3, ARG0), mul(ARG2, ARG0)), mul(mul(ARG0, ARG2), mul(ARG4, ARG3))), add(add(mul(ARG1, ARG3), sub(add(ARG4, ARG2), ARG0)), mul(sub(ARG0, ARG4), mul(ARG2, ARG2)))), mul(mul(ARG4, ARG2), add(ARG4, ARG0)))",
        "lt(mul(sub(add(ARG0, ARG1), sub(ARG0, ARG4)), mul(add(ARG1, ARG3), add(ARG2, ARG0))), mul(mul(mul(ARG4, ARG4), add(ARG0, ARG4)), add(add(ARG1, ARG1), mul(ARG4, ARG4))))",
        "eq(mul(sub(sub(add(ARG0, ARG4), mul(ARG3, ARG1)), sub(add(ARG0, ARG1), add(ARG3, ARG0))), mul(add(mul(ARG2, ARG1), ARG3), mul(mul(ARG1, ARG3), mul(ARG1, ARG4)))), mul(sub(sub(mul(ARG2, ARG1), mul(ARG3, ARG1)), mul(mul(ARG4, ARG3), sub(ARG0, ARG1))), mul(sub(add(mul(ARG4, ARG2), mul(ARG4, ARG0)), add(ARG1, sub(add(ARG3, ARG2), sub(ARG4, ARG2)))), mul(mul(ARG3, ARG1), add(ARG3, ARG4)))))",
        "gt(sub(add(mul(add(ARG3, ARG1), mul(ARG3, ARG0)), mul(sub(ARG0, ARG1), mul(ARG1, ARG3))), mul(sub(add(ARG0, ARG1), add(ARG3, ARG1)), mul(add(ARG2, ARG4), mul(ARG0, ARG0)))), add(mul(sub(mul(ARG0, ARG0), sub(ARG3, ARG4)), mul(mul(ARG4, ARG0), mul(ARG2, ARG3))), add(mul(add(ARG3, ARG4), sub(ARG4, ARG4)), add(add(ARG0, ARG2), mul(ARG2, ARG2)))))",
        "le(add(mul(mul(add(ARG4, ARG2), mul(ARG0, ARG0)), mul(mul(ARG3, ARG1), mul(ARG4, ARG4))), add(mul(mul(ARG4, ARG4), add(ARG3, ARG4)), add(sub(ARG2, ARG3), ARG4))), add(mul(mul(add(ARG4, ARG2), mul(ARG0, ARG0)), mul(mul(ARG3, ARG1), mul(ARG1, ARG4))), add(mul(mul(ARG4, ARG4), add(ARG3, ARG4)), add(sub(ARG2, ARG3), add(ARG4, mul(ARG3, ARG1))))))",
        "lt(mul(add(sub(add(ARG0, ARG2), sub(ARG1, ARG2)), sub(add(ARG0, ARG3), mul(sub(ARG1, ARG4), ARG2))), sub(add(mul(ARG3, ARG0), add(ARG2, ARG3)), sub(add(ARG1, ARG2), add(ARG4, ARG2)))), sub(add(mul(ARG3, ARG0), add(ARG2, ARG3)), sub(add(ARG1, ARG2), add(ARG4, ARG2))))",
        "lt(mul(mul(mul(ARG2, ARG4), sub(ARG2, ARG3)), sub(mul(ARG2, ARG3), mul(ARG0, ARG3))), mul(sub(add(ARG3, ARG0), mul(ARG3, ARG0)), sub(sub(ARG3, ARG4), ARG3)))",
        "lt(mul(mul(mul(ARG1, ARG2), mul(ARG2, ARG3)), sub(sub(ARG1, ARG3), add(ARG3, ARG4))), sub(mul(mul(ARG2, ARG4), mul(ARG1, ARG0)), mul(mul(ARG3, ARG0), mul(ARG2, ARG2))))",
        "gt(mul(add(add(add(ARG4, ARG2), sub(ARG3, ARG3)), mul(mul(ARG2, ARG1), mul(ARG4, mul(mul(ARG1, ARG0), sub(ARG1, ARG1))))), sub(add(sub(ARG3, ARG1), mul(ARG3, ARG2)), sub(mul(ARG3, ARG4), sub(ARG1, ARG1)))), mul(sub(add(mul(ARG3, ARG4), mul(ARG0, ARG2)), add(add(ARG4, ARG4), mul(ARG0, add(ARG2, ARG2)))), add(sub(mul(ARG1, ARG4), ARG3), mul(sub(ARG4, ARG0), add(sub(mul(ARG1, ARG2), add(ARG2, ARG2)), ARG4)))))",
        "lt(add(add(sub(mul(ARG4, ARG4), sub(ARG1, ARG3)), add(mul(ARG1, ARG1), mul(ARG3, ARG3))), mul(add(ARG2, add(ARG2, ARG4)), mul(add(ARG0, ARG2), sub(ARG0, ARG4)))), mul(sub(mul(add(ARG4, ARG0), add(ARG1, ARG1)), add(mul(ARG4, ARG2), sub(ARG4, ARG4))), mul(mul(mul(ARG0, ARG4), ARG2), mul(add(ARG0, ARG0), mul(ARG1, ARG2)))))",
        "gt(mul(ARG2, ARG0), mul(sub(add(add(ARG3, ARG1), ARG0), mul(ARG3, ARG4)), ARG4))",
        "lt(mul(mul(add(add(ARG2, ARG0), sub(ARG3, ARG0)), mul(sub(ARG0, ARG1), add(ARG0, ARG3))), sub(mul(add(ARG3, ARG0), add(ARG3, ARG4)), mul(sub(ARG0, ARG2), mul(ARG3, ARG4)))), sub(mul(mul(mul(ARG2, ARG2), add(ARG1, ARG0)), add(add(ARG2, ARG3), sub(ARG1, ARG2))), mul(sub(add(ARG0, ARG1), mul(ARG3, ARG0)), mul(add(ARG3, ARG0), mul(ARG3, ARG3)))))",
        "lt(sub(add(add(mul(ARG1, ARG2), mul(ARG3, ARG2)), sub(add(ARG3, ARG1), add(ARG3, ARG1))), mul(mul(add(add(add(ARG4, ARG0), sub(ARG1, ARG1)), ARG4), mul(ARG2, ARG1)), sub(sub(ARG0, ARG0), add(ARG4, ARG2)))), mul(mul(mul(add(ARG4, ARG4), mul(ARG0, ARG2)), ARG3), add(ARG3, sub(ARG4, ARG2))))",
        "lt(mul(ARG1, ARG3), mul(add(sub(ARG4, ARG4), sub(ARG0, ARG4)), sub(mul(ARG3, ARG2), mul(ARG1, ARG2))))",
        "gt(sub(mul(sub(ARG4, ARG3), sub(ARG4, ARG0)), add(add(ARG4, ARG4), mul(ARG3, ARG3))), mul(sub(mul(ARG4, ARG1), add(ARG3, ARG3)), add(sub(ARG4, ARG1), sub(ARG2, ARG3))))",
        "gt(mul(mul(mul(mul(ARG4, ARG3), mul(ARG2, ARG2)), mul(add(ARG2, ARG0), sub(ARG0, ARG1))), mul(add(add(ARG1, ARG3), mul(ARG1, ARG3)), sub(sub(ARG0, ARG1), add(ARG3, ARG3)))), mul(sub(add(mul(ARG3, ARG2), add(ARG4, ARG4)), sub(mul(ARG0, ARG3), add(ARG2, ARG0))), sub(add(sub(ARG3, ARG0), sub(ARG2, ARG0)), mul(add(ARG3, ARG4), add(ARG0, ARG2)))))",
        "eq(mul(mul(mul(ARG0, ARG2), sub(ARG3, ARG2)), mul(ARG3, mul(ARG4, ARG3))), add(ARG2, mul(mul(mul(ARG2, ARG1), sub(ARG3, ARG2)), mul(mul(ARG0, ARG4), mul(ARG4, ARG3)))))",
        "lt(mul(mul(mul(ARG2, ARG3), mul(ARG3, ARG2)), mul(add(ARG0, ARG0), sub(ARG4, ARG0))), sub(add(add(sub(ARG4, ARG0), sub(ARG2, ARG0)), add(sub(add(ARG2, ARG4), ARG3), mul(ARG1, ARG3))), mul(add(add(mul(ARG4, ARG1), ARG0), add(ARG0, ARG2)), sub(sub(ARG0, ARG1), sub(ARG1, ARG2)))))",
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

    solvers = [
        "cvc5", "cvc5", "z3", "z3", "z3", "z3", "cvc5", "cvc5", "z3", "cvc5",
        "cvc5", "cvc5", "mathsat", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "z3", "z3",

        "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "z3", "cvc5", "cvc5",
        "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5",

        "z3", "cvc5", "cvc5", "cvc5", "cvc5", "z3", "cvc5", "z3", "cvc5", "z3",
        "z3", "z3", "z3", "cvc5", "z3", "z3", "cvc5", "cvc5", "cvc5", "cvc5",

        "z3", "cvc5", "z3", "cvc5", "z3", "cvc5", "z3", "cvc5", "cvc5", "cvc5",
        "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "z3", "z3", "cvc5",

        "z3", "cvc5", "cvc5", "z3", "z3", "z3", "z3", "z3", "cvc5", "z3",
        "cvc5", "cvc5", "z3", "cvc5", "z3", "z3", "z3",
        "z3", "z3", "cvc5"
    ]

    assert len(deap_formulas) == len(solvers), \
        f"Mismatch: {len(deap_formulas)} formulas but {len(solvers)} solvers"

    feat_dicts = [extract_tree_features(f) for f in deap_formulas]

    for i, d in enumerate(feat_dicts):
        if d is None:
            print(f"Failed: f{i} — {deap_formulas[i][:80]}...")

    valid_mask = [d is not None for d in feat_dicts]
    feat_dicts = [d for d in feat_dicts if d is not None]
    solvers_v = [s for s, v in zip(solvers, valid_mask) if v]
    formulas_v = [f for f, v in zip(deap_formulas, valid_mask) if v]

    feature_names = list(feat_dicts[0].keys())
    X = np.array([[d[k] for k in feature_names] for d in feat_dicts])
    X = StandardScaler().fit_transform(X)

    root_labels = [re.match(r'[A-Za-z_][A-Za-z0-9_]*', f).group() for f in formulas_v]

    plot_pca_umap_sidebyside(X, solvers_v, root_labels)
