import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
import numpy as np

def boxplot():
    #1 - baseline, 2 - join, 3 - LLM mutation, 4 - LLM crossover, 5 - LLM mut+cx
    data = {
        "Baseline": [
        33789.96878,32856.41667,225.7004881,71.977323,36748.6955,93.63309934,32385.36381,24704.55943,91.31770239,2592.31843,
        979.673208,2470.699298,175.4621786,2116.226516,37524.08648,6903.898608,37151.25652,176.341899,110.0638096,86.26841318,
    ],
        "Join": [
        48577.92055,48153.11875,2203.947257,44380.82107,18046.67532,30613.61278,6148.323469,570.2428866,1265.015455,1692.613245,
        40087.92712,40153.17165,1545.940179,27852.21747,2726.497167,1224.203968,38967.44844,39387.34736,24386.14254, 1358.183422
    ],
        "LLM Mut.": [
        90.07047604,29327.06265,31942.21618,20252.36928,21573.52806,91.78333651,7755.183613,99.8847762,34793.50827,126.7247023,
        209.9884239,155.5614371,226.4785543,34659.27133,112.6512647,140.5933084,25307.05527,28360.29061, 3552.967904,25302.72932
    ],
        "LLM Cx.": [
        82.3847352,1010.423582,47.65895886,1673.343889,230.687028,31154.46147,262.2784065,6226.344852,32674.24994,34961.24507,
        25629.7661,29259.54461,16834.82777,5042.84015,37038.61262,4127.94209,4688.964294,321.2953495,95.37104847,31203.52336
    ],
        "LLM Mut.+Cx.": [
        237.5777261,1017.850675,15746.21112,92.06107894,137.0403007,97.90399714,61.77324157,42.36252279,2557.161114,86.89553296,
        27338.29821,25585.98579,84.80359785,29449.93505,112.6185318,81.01940323,145.8082395,220.8096065,163.6181226,20452.70048
    ]
    }
    df = pd.DataFrame(data)

    # ---- Create Boxplot ----
    ax = df.boxplot(whis=[0, 100], grid=False)

    means = df.mean()
    for i, mean in enumerate(means):
        ax.plot([i + 0.75, i + 1.25], [mean, mean], color='red', linewidth=1.5)

    # Dummy lines for legend
    ax.plot([], [], color='red', linewidth=1.5, label='Mean')
    ax.plot([], [], color='green', linewidth=1.5, label='Median')
    ax.tick_params(axis='both', labelsize=10)
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1), borderaxespad=1, fontsize=10)

    plt.ylabel("Relative Runtime Difference", fontsize=13)
    plt.xlabel("Fuzzer Configuration", fontsize=13)
    plt.yscale('log')
    plt.tight_layout()
    plt.show()

def stacked_bar_plot():

    configs = ["Baseline", "Join", "LLM Mut.", "LLM Cx.", "LLM Mut.+Cx."]

    # --- Raw solver results for each config (20 runs each) ---
    baseline = [
        "cvc5","cvc5","z3","z3","z3","z3","cvc5","cvc5","z3","cvc5","cvc5","cvc5","mathsat","cvc5","cvc5","cvc5","cvc5","cvc5","z3","z3"
    ]

    join = [
        "cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","z3","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5"
    ]

    llm_mut = [
        "z3","cvc5","cvc5","cvc5","cvc5","z3","cvc5","z3","cvc5","z3","z3","z3","z3","cvc5","z3","z3","cvc5","cvc5","cvc5","cvc5"
    ]

    llm_cx = [
        "z3","cvc5","z3","cvc5","z3","cvc5","z3","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","cvc5","z3","z3","cvc5"
    ]

    llm = [
        "z3","cvc5","cvc5","z3","z3","z3","z3","z3","cvc5","z3","cvc5","cvc5","z3","cvc5","z3","z3","z3","z3","z3","cvc5"
    ]

    all_data = [baseline, join, llm_mut, llm_cx, llm]

    # Count occurrences
    cvc5_counts = []
    z3_counts = []
    mathsat_counts = []

    for config in all_data:
        counts = Counter(config)
        mathsat_counts.append(counts["mathsat"])
        z3_counts.append(counts["z3"])
        cvc5_counts.append(counts["cvc5"])

    cvc5_counts = np.array(cvc5_counts)
    z3_counts = np.array(z3_counts)
    mathsat_counts = np.array(mathsat_counts)
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.bar(configs, cvc5_counts, label="cvc5")
    ax.bar(configs, z3_counts, bottom=cvc5_counts, label="Z3")
    ax.bar(configs, mathsat_counts, bottom=cvc5_counts + z3_counts, label="MathSAT")

    ax.set_ylabel("Number of Runs", fontsize=16)
    ax.set_xlabel("Fuzzer Configuration", fontsize=16)
    ax.set_ylim(0, 21)
    ax.set_yticks([0, 5, 10, 15, 20])
    ax.tick_params(axis='both', labelsize=14)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], fontsize=14)

    fig.tight_layout()
    plt.show()

def shaded_linegraph_combined():


    # --- (keep your DataFrame definitions exactly as they are) ---
    baseline_df = pd.DataFrame({
        "generation": range(31),
        "avg": [
            3.87887, 5.28031, 7.54005, 9.41768, 14.2096, 17.995, 20.9699, 24.5057,
            27.1723, 29.8134, 32.9854, 37.3232, 44.1082, 50.6017, 54.9734, 59.8551,
            64.63, 68.5376, 71.707, 75.2945, 80.3428, 80.4868, 82.3375, 93.3361,
            94.9114, 95.0206, 95.0501, 95.0501, 95.0501, 95.5257, 95.8601
        ],
        "min": [
            0, 0, 0, 0, 0, 10.5931, 12.9919, 16.9392, 18.0281, 18.8271, 20.1878, 21.8402,
            26.4956, 38.8173, 42.634, 49.5036, 51.7036, 53.5839, 56.6493, 58.3353,
            64.9626, 67.1356, 71.8451, 81.0071, 81.5957, 82.4734, 82.9814, 82.9814,
            82.9814, 83.3133, 83.5582
        ],
        "max": [
            21.8735, 22.8259, 28.1415, 28.1415, 37.9705, 37.9705, 56.3244, 56.3244,
            56.3244, 56.3244, 56.3244, 85.382, 85.382, 85.382, 85.382, 85.382, 85.382,
            92.6332, 92.6332, 94.2503, 103.984, 103.984, 103.984, 171.678, 171.678,
            171.678, 171.678, 171.678, 171.678, 171.678, 171.678
        ]
    })

    llm_df = pd.DataFrame({
        "generation": range(31),
        "min": [
            0, 0, 0, 0,
            7.331227977, 10.39120505, 15.43359318,
            20.61321844, 24.76184916, 30.64458393,
            35.98141355, 37.2595698, 42.32989056,
            45.68949529, 47.49133938, 50.32048329,
            51.51994184, 52.36245259, 53.347126,
            56.31915168, 56.33404903, 60.55129339,
            60.55129339, 60.55281802, 60.58600546,
            61.92269113, 61.92269113, 62.7779931,
            63.37350025, 63.37350025, 64.43830796
        ],
        "avg": [
            3.739851081, 4.988971006, 10.36734328,
            13.02555077, 20.56641877, 26.08835483,
            31.29934272, 34.66726705, 39.86720886,
            43.8335166, 46.73710902, 48.65694499,
            50.33215826, 54.09624064, 55.84621722,
            57.83500136, 59.14434122, 60.17298253,
            61.99398835, 64.0151858, 65.20652675,
            67.56491007, 67.56491007, 68.02449447,
            68.37031014, 68.5759466, 68.5759466,
            69.48044006, 70.79414598, 70.79414598,
            71.79509461
        ],
        "max": [
            43.899389, 43.899389, 50.32048329,
            50.32048329, 55.374452, 55.374452,
            55.374452, 55.374452, 60.4102847,
            60.4102847, 60.4102847, 60.58600546,
            60.58600546, 73.83468596, 73.83468596,
            73.83468596, 73.83468596, 74.84001134,
            74.84001134, 74.84001134, 86.10267559,
            86.10267559, 86.10267559, 86.10267559,
            86.10267559, 86.10267559, 86.10267559,
            86.10267559, 86.10267559, 86.10267559,
            86.93767893
        ]
    })

    join_df = pd.DataFrame({
        "generation": range(31),
        "min": [
            0, 0, 0,
            13.61183558, 31.91331365, 37.26700376,
            39.27489939, 42.4760845, 51.70130552,
            58.54808441, 63.66461246, 66.42562251,
            68.80292982, 70.25927425, 73.68363563,
            75.77577725, 77.74925334, 1178.522043,
            1216.885432, 1230.198239, 1238.714201,
            1245.642936, 1249.869177, 1252.258616,
            1253.367967, 1254.08321, 1256.701919,
            1256.947242, 1257.87615, 1258.0729,
            1260.040919
        ],
        "avg": [
            6.32006801, 12.16720801, 20.78096075,
            36.50008196, 43.07588265, 99.65973087,
            103.0587088, 109.2228048, 113.0268388,
            116.011334, 119.2051897, 167.758436,
            168.1743107, 261.3044363, 400.5491876,
            673.7708777, 945.6885922, 1224.938352,
            1244.054044, 1251.195503, 1254.290712,
            1256.981443, 1260.312684, 1260.745398,
            1261.737548, 1262.168481, 1263.54269,
            1264.23776, 1265.418282, 1267.119452,
            1268.903294
        ],
        "max": [
            44.6380132, 44.6380132, 44.6380132,
            75.60328626, 75.60328626, 1252.301103,
            1252.301103, 1252.301103, 1252.301103,
            1252.301103, 1252.301103, 1253.367967,
            1253.367967, 1263.802659, 1263.802659,
            1263.802659, 1263.802659, 1263.802659,
            1276.81886, 1276.81886, 1276.81886,
            1276.81886, 1276.81886, 1276.81886,
            1276.81886, 1276.81886, 1276.81886,
            1276.81886, 1276.81886, 1291.582943,
            1291.582943
        ]
    })
    llm_df_solo = pd.DataFrame({
        "generation": range(31),
        "min": [
        0, 0, 0, 0, 0,
        14.79717079, 21.03621856, 25.77160873, 33.25793293, 36.9092387,
        38.99430421, 41.70796409, 42.03117374, 44.69471454, 47.96623002,
        58.36387998, 65.97294109, 67.07035653, 82.76377201, 95.98570134,
        108.901524, 115.337868, 116.5517942, 116.5517942, 125.2261036,
        1114.358505, 1124.174862, 1137.736736, 1149.670421, 1154.596802,
        1176.770485
        ],
        "avg": [
            51.0688608, 98.84366901, 148.2409315, 153.5220341, 160.3143895,
            212.8726261, 308.5703867, 359.2001487, 364.5285076, 365.5104964,
            372.1855625, 419.6933624, 465.7602399, 471.0856313, 477.2542836,
            570.7958814, 616.8218303, 618.0223407, 754.5861305, 795.8677197,
            836.2346679, 878.2385717, 1001.870553, 1001.870553, 1088.186701,
            1178.436619, 1182.986579, 1189.192248, 1192.464152, 1196.038579,
            1199.935632
        ],
        "max": [
            1223.28418, 1223.28418, 1223.28418, 1223.28418, 1223.28418,
            1223.28418, 1223.28418, 1223.28418, 1223.28418, 1223.28418,
            1223.28418, 1223.28418, 1223.28418, 1223.28418, 1223.28418,
            1224.009229, 1224.009229, 1224.009229, 1231.996106, 1231.996106,
            1231.996106, 1231.996106, 1231.996106, 1231.996106, 1231.996106,
            1231.996106, 1231.996106, 1239.647126, 1239.647126, 1239.647126,
            1239.647126
        ]
    })

    fig, axs = plt.subplots(1, 2, figsize=(20, 6), sharey=True)

    ax = axs[0]

    ax.fill_between(
        baseline_df["generation"],
        baseline_df["min"],
        baseline_df["max"],
        color="blue",
        alpha=0.2
    )
    ax.plot(baseline_df["generation"], baseline_df["avg"], color="blue")

    ax.fill_between(
        llm_df["generation"],
        llm_df["min"],
        llm_df["max"],
        color="orange",
        alpha=0.2
    )
    ax.plot(llm_df["generation"], llm_df["avg"], color="orange")

    ax.fill_between(
        join_df["generation"],
        join_df["min"],
        join_df["max"],
        color="green",
        alpha=0.2
    )
    ax.plot(join_df["generation"], join_df["avg"], color="green")

    ax = axs[1]

    ax.fill_between(
        llm_df_solo["generation"],
        llm_df_solo["min"],
        llm_df_solo["max"],
        color="orange",
        alpha=0.2
    )
    ax.plot(llm_df_solo["generation"], llm_df_solo["avg"], color="orange")

    #ax.set_title("LLM Mutation + Crossover")
    axs[0].set_xlabel("Generation", fontsize=20)
    axs[1].set_xlabel("Generation", fontsize=20)
    axs[0].set_ylabel("Fitness", fontsize=20)
    # =====================
    # LEGEND IN MIDDLE
    # =====================
    handles = [
        plt.Line2D([0], [0], color="blue", lw=2),
        plt.Line2D([0], [0], color="green", lw=2),
        plt.Line2D([0], [0], color="orange", lw=2)
    ]

    labels = ["Baseline", "Join", "LLM Mut.+Cx."]

    axs[0].legend(
        handles,
        labels,
        loc="center right",
        frameon=True,
        facecolor='white',
        framealpha=0.8,
        fontsize=13
    )
    axs[0].tick_params(axis='both', labelsize=16)
    axs[1].tick_params(axis='both', labelsize=16)
    axs[1].tick_params(axis='y', left=False, labelleft=False)
    plt.subplots_adjust(wspace=0.05)
    plt.show()


def shaded_linegraph_LLM():
    llm_df = pd.DataFrame({
        "generation": range(31),
        "min": [
        0, 0, 0, 0, 0,
        14.79717079, 21.03621856, 25.77160873, 33.25793293, 36.9092387,
        38.99430421, 41.70796409, 42.03117374, 44.69471454, 47.96623002,
        58.36387998, 65.97294109, 67.07035653, 82.76377201, 95.98570134,
        108.901524, 115.337868, 116.5517942, 116.5517942, 125.2261036,
        1114.358505, 1124.174862, 1137.736736, 1149.670421, 1154.596802,
        1176.770485
        ],
        "avg": [
            51.0688608, 98.84366901, 148.2409315, 153.5220341, 160.3143895,
            212.8726261, 308.5703867, 359.2001487, 364.5285076, 365.5104964,
            372.1855625, 419.6933624, 465.7602399, 471.0856313, 477.2542836,
            570.7958814, 616.8218303, 618.0223407, 754.5861305, 795.8677197,
            836.2346679, 878.2385717, 1001.870553, 1001.870553, 1088.186701,
            1178.436619, 1182.986579, 1189.192248, 1192.464152, 1196.038579,
            1199.935632
        ],
        "max": [
            1223.28418, 1223.28418, 1223.28418, 1223.28418, 1223.28418,
            1223.28418, 1223.28418, 1223.28418, 1223.28418, 1223.28418,
            1223.28418, 1223.28418, 1223.28418, 1223.28418, 1223.28418,
            1224.009229, 1224.009229, 1224.009229, 1231.996106, 1231.996106,
            1231.996106, 1231.996106, 1231.996106, 1231.996106, 1231.996106,
            1231.996106, 1231.996106, 1239.647126, 1239.647126, 1239.647126,
            1239.647126
        ]
    })

    plt.figure(figsize=(8, 6))

    plt.fill_between(
        llm_df["generation"],
        llm_df["min"],
        llm_df["max"],
        color="orange",
        alpha=0.2
    )

    plt.plot(llm_df["generation"], llm_df["avg"], color="orange", linewidth=1, alpha=0.8)
    plt.plot([], [], color="orange", label="LLM Mut.+Cx.")

    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.tight_layout()
    plt.show()

def shaded_linegraph():


    baseline_df = pd.DataFrame({
        "generation": range(31),
        "avg": [
            3.87887, 5.28031, 7.54005, 9.41768, 14.2096, 17.995, 20.9699, 24.5057,
            27.1723, 29.8134, 32.9854, 37.3232, 44.1082, 50.6017, 54.9734, 59.8551,
            64.63, 68.5376, 71.707, 75.2945, 80.3428, 80.4868, 82.3375, 93.3361,
            94.9114, 95.0206, 95.0501, 95.0501, 95.0501, 95.5257, 95.8601
        ],
        "min": [
            0, 0, 0, 0, 0, 10.5931, 12.9919, 16.9392, 18.0281, 18.8271, 20.1878, 21.8402,
            26.4956, 38.8173, 42.634, 49.5036, 51.7036, 53.5839, 56.6493, 58.3353,
            64.9626, 67.1356, 71.8451, 81.0071, 81.5957, 82.4734, 82.9814, 82.9814,
            82.9814, 83.3133, 83.5582
        ],
        "max": [
            21.8735, 22.8259, 28.1415, 28.1415, 37.9705, 37.9705, 56.3244, 56.3244,
            56.3244, 56.3244, 56.3244, 85.382, 85.382, 85.382, 85.382, 85.382, 85.382,
            92.6332, 92.6332, 94.2503, 103.984, 103.984, 103.984, 171.678, 171.678,
            171.678, 171.678, 171.678, 171.678, 171.678, 171.678
        ]
    })

    llm_df = pd.DataFrame({
        "generation": range(31),
        "min": [
            0, 0, 0, 0,
            7.331227977, 10.39120505, 15.43359318,
            20.61321844, 24.76184916, 30.64458393,
            35.98141355, 37.2595698, 42.32989056,
            45.68949529, 47.49133938, 50.32048329,
            51.51994184, 52.36245259, 53.347126,
            56.31915168, 56.33404903, 60.55129339,
            60.55129339, 60.55281802, 60.58600546,
            61.92269113, 61.92269113, 62.7779931,
            63.37350025, 63.37350025, 64.43830796
        ],
        "avg": [
            3.739851081, 4.988971006, 10.36734328,
            13.02555077, 20.56641877, 26.08835483,
            31.29934272, 34.66726705, 39.86720886,
            43.8335166, 46.73710902, 48.65694499,
            50.33215826, 54.09624064, 55.84621722,
            57.83500136, 59.14434122, 60.17298253,
            61.99398835, 64.0151858, 65.20652675,
            67.56491007, 67.56491007, 68.02449447,
            68.37031014, 68.5759466, 68.5759466,
            69.48044006, 70.79414598, 70.79414598,
            71.79509461
        ],
        "max": [
            43.899389, 43.899389, 50.32048329,
            50.32048329, 55.374452, 55.374452,
            55.374452, 55.374452, 60.4102847,
            60.4102847, 60.4102847, 60.58600546,
            60.58600546, 73.83468596, 73.83468596,
            73.83468596, 73.83468596, 74.84001134,
            74.84001134, 74.84001134, 86.10267559,
            86.10267559, 86.10267559, 86.10267559,
            86.10267559, 86.10267559, 86.10267559,
            86.10267559, 86.10267559, 86.10267559,
            86.93767893
        ]
    })

    join_df = pd.DataFrame({
        "generation": range(31),
        "min": [
            0, 0, 0,
            13.61183558, 31.91331365, 37.26700376,
            39.27489939, 42.4760845, 51.70130552,
            58.54808441, 63.66461246, 66.42562251,
            68.80292982, 70.25927425, 73.68363563,
            75.77577725, 77.74925334, 1178.522043,
            1216.885432, 1230.198239, 1238.714201,
            1245.642936, 1249.869177, 1252.258616,
            1253.367967, 1254.08321, 1256.701919,
            1256.947242, 1257.87615, 1258.0729,
            1260.040919
        ],
        "avg": [
            6.32006801, 12.16720801, 20.78096075,
            36.50008196, 43.07588265, 99.65973087,
            103.0587088, 109.2228048, 113.0268388,
            116.011334, 119.2051897, 167.758436,
            168.1743107, 261.3044363, 400.5491876,
            673.7708777, 945.6885922, 1224.938352,
            1244.054044, 1251.195503, 1254.290712,
            1256.981443, 1260.312684, 1260.745398,
            1261.737548, 1262.168481, 1263.54269,
            1264.23776, 1265.418282, 1267.119452,
            1268.903294
        ],
        "max": [
            44.6380132, 44.6380132, 44.6380132,
            75.60328626, 75.60328626, 1252.301103,
            1252.301103, 1252.301103, 1252.301103,
            1252.301103, 1252.301103, 1253.367967,
            1253.367967, 1263.802659, 1263.802659,
            1263.802659, 1263.802659, 1263.802659,
            1276.81886, 1276.81886, 1276.81886,
            1276.81886, 1276.81886, 1276.81886,
            1276.81886, 1276.81886, 1276.81886,
            1276.81886, 1276.81886, 1291.582943,
            1291.582943
        ]
    })

    import numpy as np

    plt.figure(figsize=(8, 6))

    all_baseline_avg = []
    all_baseline_min = []
    all_baseline_max = []

    baseline_dfs = [baseline_df]

    for df in baseline_dfs:
        all_baseline_avg.append(df["avg"].values)
        all_baseline_min.append(df["min"].values)
        all_baseline_max.append(df["max"].values)

    baseline_min_avg = np.min(all_baseline_min, axis=0)
    baseline_max_avg = np.max(all_baseline_max, axis=0)
    plt.fill_between(
        baseline_df["generation"],  # fixed
        baseline_min_avg,
        baseline_max_avg,
        color="blue",
        alpha=0.2
    )

    for avg in all_baseline_avg:
        plt.plot(baseline_df["generation"], avg, color="blue", linewidth=1, alpha=0.8)  # fixed

    all_llm_avg = []
    all_llm_min = []
    all_llm_max = []

    llm_dfs = [llm_df]

    for df in llm_dfs:
        all_llm_avg.append(df["avg"].values)
        all_llm_min.append(df["min"].values)
        all_llm_max.append(df["max"].values)

    llm_min_avg = np.min(all_llm_min, axis=0)
    llm_max_avg = np.max(all_llm_max, axis=0)
    plt.fill_between(
        llm_df["generation"],  # fixed
        llm_min_avg,
        llm_max_avg,
        color="orange",
        alpha=0.2
    )

    for avg in all_llm_avg:
        plt.plot(llm_df["generation"], avg, color="orange", linewidth=1, alpha=0.8)  # fixed

    all_join_avg = []
    all_join_min = []
    all_join_max = []

    join_dfs = [join_df]

    for df in join_dfs:
        all_join_avg.append(df["avg"].values)
        all_join_min.append(df["min"].values)
        all_join_max.append(df["max"].values)

    join_min_avg = np.min(all_join_min, axis=0)
    join_max_avg = np.max(all_join_max, axis=0)
    plt.fill_between(
        join_df["generation"],
        join_min_avg,
        join_max_avg,
        color="green",
        alpha=0.2
    )

    for avg in all_join_avg:
        plt.plot(join_df["generation"], avg, color="green", linewidth=1, alpha=0.8)  # fixed

    # Legend and labels
    plt.plot([], [], color="blue", label="Baseline")
    plt.plot([], [], color="green", label="Join")
    plt.plot([], [], color="orange", label="LLM Mut.+Cx.")


    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.tight_layout()
    plt.show()

def depth_scatter_solver_vs_depth():
    solver_map = {'z3': 0, 'cvc5': 1, 'mathsat': 2}
    x = [solver_map[s] for s in solvers]

    x_jittered = np.array(x) + np.random.normal(0, 0.05, size=len(x))

    plt.figure(figsize=(8, 6))
    plt.scatter(
        x_jittered,
        depths,
        alpha=0.7,
        s=25,
        c=['red' if s == 'z3' else 'blue' if s == 'cvc5' else 'green' for s in solvers]
    )

    plt.xticks([0, 1,2], ['z3', 'cvc5', 'mathsat'])
    plt.xlabel('Solver')
    plt.ylabel('Formula Depth')
    plt.title('Solver vs Formula Depth')
    plt.grid(True, alpha=0.3)

    plt.show()

def runtime_vs_depths_by_solver():
    baseline_relative_difference = [
        # Rand (20)
        33789.96878, 32856.41667, 225.7004881, 71.977323, 36748.6955,
        93.63309934, 32385.36381, 24704.55943, 91.31770239, 2592.31843,
        979.673208, 2470.699298, 175.4621786, 2116.226516, 37524.08648,
        6903.898608, 37151.25652, 176.341899, 110.0638096, 86.26841318]

    join_relative_difference = [
        # Join (20)
        48577.92055, 48153.11875, 2203.947257, 44380.82107, 18046.67532,
        30613.61278, 6148.323469, 570.2428866, 1265.015455, 1692.613245,
        40087.92712, 40153.17165, 1545.940179, 27852.21747, 2726.497167,
        1224.203968, 38967.44844, 39387.34736, 24386.14254, 1358.183422]

    llm_mut_relative_difference = [
        # LLM Mut. (20)
        90.07047604, 29327.06265, 31942.21618, 20252.36928, 21573.52806,
        91.78333651, 7755.183613, 99.8847762, 34793.50827, 126.7247023,
        209.9884239, 155.5614371, 226.4785543, 34659.27133, 112.6512647,
        140.5933084, 25307.05527, 28360.29061, 3552.967904, 25302.72932]

    llm_cx_relative_difference = [
        # LLM Cx. (20)
        82.3847352, 1010.423582, 47.65895886, 1673.343889, 230.687028,
        31154.46147, 262.2784065, 6226.344852, 32674.24994, 34961.24507,
        25629.7661, 29259.54461, 16834.82777, 5042.84015, 37038.61262,
        4127.94209, 4688.964294, 321.2953495, 95.37104847, 31203.52336]

    llm_full_depth_relative_difference = [
        # LLM (20)
        237.5777261, 1017.850675, 15746.21112, 92.06107894, 137.0403007,
        97.90399714, 61.77324157, 42.36252279, 2557.161114, 86.89553296,
        27338.29821, 25585.98579, 84.80359785, 29449.93505, 112.6185318,
        81.01940323, 145.8082395, 220.8096065, 163.6181226, 20452.70048,
    ]

    baseline_depth = [
        5, 5, 6, 7, 6, 7, 7, 9, 10, 6,
        7, 7, 13, 7, 6, 4, 4, 5, 6, 9]
    join_depth = [
        8, 8, 9, 9, 10, 10, 11, 8, 6, 10,
        10, 16, 9, 5, 9, 5, 9, 8, 9, 8]
    llm_mut_depth = [
        8, 6, 6, 6, 9, 10, 6, 10, 7, 9,
        6, 8, 7, 5, 6, 7, 5, 8, 7, 11]
    llm_cx_depth = [
        7, 6, 6, 4, 7, 5, 6, 6, 4, 4,
        7, 5, 5, 5, 7, 4, 4, 5, 5, 6]
    llm_full_depth = [
        6, 7, 5, 9, 10, 11, 5, 9, 6, 10,
        5, 6, 10, 6, 7, 8, 7, 8, 9, 7]

    baseline_solvers = ["cvc5", "cvc5", "z3", "z3", "z3", "z3", "cvc5", "cvc5", "z3", "cvc5",
    "cvc5", "cvc5", "mathsat", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "z3", "z3"]

    join_solvers = ["cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "z3", "cvc5", "cvc5",
    "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5"]

    llm_mut_solvers = ["z3", "cvc5", "cvc5", "cvc5", "cvc5", "z3", "cvc5", "z3", "cvc5", "z3",
    "z3", "z3", "z3", "cvc5", "z3", "z3", "cvc5", "cvc5", "cvc5", "cvc5"]

    llm_cx_solvers = ["z3", "cvc5", "z3", "cvc5", "z3", "cvc5", "z3", "cvc5", "cvc5", "cvc5",
    "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "cvc5", "z3", "z3", "cvc5"]

    llm_full_solvers = ["z3", "cvc5", "cvc5", "z3", "z3", "z3", "z3", "z3", "cvc5", "z3",
    "cvc5", "cvc5", "z3", "cvc5", "z3", "z3", "z3", "z3", "z3", "cvc5"]

    #solvers_list = ["z3", "cvc5", "mathsat"]

    configs = {
        "Baseline": {
            "runtime": baseline_relative_difference,
            "depth": baseline_depth,
            "solvers": baseline_solvers,
            #"marker": "o",
            "color": "blue"
        },
        "Join": {
            "runtime": join_relative_difference,
            "depth": join_depth,
            "solvers": join_solvers,
            #"marker": "s",
            "color": "green"
        },
        "LLM Mutation": {
            "runtime": llm_mut_relative_difference,
            "depth": llm_mut_depth,
            "solvers": llm_mut_solvers,
            #"marker": "^",
            "color": "purple"
        },
        "LLM Crossover": {
            "runtime": llm_cx_relative_difference,
            "depth": llm_cx_depth,
            "solvers": llm_cx_solvers,
            #"marker": "D",
            "color": "red"
        },
        "LLM Mutation & Crossover": {
            "runtime": llm_full_depth_relative_difference,
            "depth": llm_full_depth,
            "solvers": llm_full_solvers,
            #"marker": "P",
            "color": "orange"
        },
    }

    from matplotlib.lines import Line2D

    solvers_list = ["z3", "cvc5"]

    legend_handles = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=conf_data["color"],
               markeredgecolor='k', markersize=8, label=name)
        for name, conf_data in configs.items()
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True, sharex=True)

    for ax, solver in zip(axes, solvers_list):
        for config_name, conf_data in configs.items():

            d_list = np.array(conf_data["depth"]).flatten()
            r_list = np.array(conf_data["runtime"]).flatten()
            s_list = np.array(conf_data["solvers"])

            mask = (s_list == solver)

            if np.any(mask):
                depths_filt = d_list[mask]
                runtimes_filt = r_list[mask]
                x_jittered = depths_filt + np.random.uniform(-0.15, 0.15, size=len(depths_filt))

                ax.scatter(x_jittered, runtimes_filt, c=conf_data["color"],
                           marker="o", alpha=0.7, s=60, edgecolor='k', linewidths=0.5)

        ax.set_yscale('log')
        if solver == "z3":
            ax.set_title("Z3", fontsize=18)
        else:
            ax.set_title("cvc5", fontsize=18)
        ax.set_xlabel("Formula Depth", fontsize=16)
        ax.grid(True, which="both", ls="--", alpha=0.5)
        ax.tick_params(axis="both", labelsize=14)

    axes[0].set_ylabel("Relative Runtime Difference", fontsize=16)
    axes[1].legend(handles=legend_handles, title="Configurations", fontsize=10)
    plt.tight_layout()
    plt.show()

def depth_distribution():

    # Count how many formulas at each depth
    depth_counts = Counter(depths)

    # Sort depths numerically
    sorted_depths = sorted(depth_counts.keys())
    counts = [depth_counts[d] for d in sorted_depths]

    # Plot bar chart
    plt.figure(figsize=(10,6))
    plt.bar(sorted_depths, counts)

    plt.xlabel("Formula Depth")
    plt.ylabel("Number of Formulas")
    plt.title("Distribution of Formula Depths")
    plt.xticks(sorted_depths)
    plt.yticks([0,2,4,6,8,10,12,14,16,18,20])
    plt.grid(axis='y', linestyle='--', alpha=0.5)

    plt.show()

runtimes = [
        600, 600, 2.845657825, 1.03042984, 600, 1.173126221, 600, 600, 1.137291908, 58.02577686,
        19.17037416, 35.92602634, 5.404509306, 37.4006145, 600, 103.5890198, 600, 3.646196365, 1.366112947, 0.960195065,
        600, 600, 28.94453788, 600, 235.4977775, 600, 104.9810188, 12.79932594, 22.14672232, 23.10883665,
        600, 600, 18.49628687, 438.4339151, 33.62954044, 15.04899454, 600, 526.3982828, 600, 24.37182093,
        1.13161087, 600, 600, 600, 600, 1.158933401, 165.591949, 1.248316526, 600, 1.460444689,
        2.598581314, 1.753741741, 6.02774477, 599.9742365, 2.368592739, 3.177280188, 600, 600, 64.89037752, 600,
        1.27632618, 22.0384655, 0.796712399, 35.42373848, 3.07915926, 600, 2.911859035, 126.6595273, 600, 600,
        600, 600, 256.3404162, 148.2846463, 600, 63.9506495, 86.15088201, 8.431861639, 1.074250221, 600,
        2.934225082, 55.88503456, 257.0731735, 1.04219079, 2.565079451, 1.120288372, 0.898143053, 0.930086613,
        70.94204664, 0.976713896,
        600, 600, 1.050762177, 600, 1.583067656, 1.173101425, 2.546276808, 2.953968287, 3.063150883, 600
    ]

relative_differences = [
    # Rand (20)
    33789.96878, 32856.41667, 225.7004881, 71.977323, 36748.6955,
    93.63309934, 32385.36381, 24704.55943, 91.31770239, 2592.31843,
    979.673208, 2470.699298, 175.4621786, 2116.226516, 37524.08648,
    6903.898608, 37151.25652, 176.341899, 110.0638096, 86.26841318,

    # Join (20)
    48577.92055, 48153.11875, 2203.947257, 44380.82107, 18046.67532,
    30613.61278, 6148.323469, 570.2428866, 1265.015455, 1692.613245,
    40087.92712, 40153.17165, 1545.940179, 27852.21747, 2726.497167,
    1224.203968, 38967.44844, 39387.34736, 24386.14254, 1358.183422,

    # LLM Mut. (20)
    90.07047604, 29327.06265, 31942.21618, 20252.36928, 21573.52806,
    91.78333651, 7755.183613, 99.8847762, 34793.50827, 126.7247023,
    209.9884239, 155.5614371, 226.4785543, 34659.27133, 112.6512647,
    140.5933084, 25307.05527, 28360.29061, 3552.967904, 25302.72932,

    # LLM Cx. (20)
    82.3847352, 1010.423582, 47.65895886, 1673.343889, 230.687028,
    31154.46147, 262.2784065, 6226.344852, 32674.24994, 34961.24507,
    25629.7661, 29259.54461, 16834.82777, 5042.84015, 37038.61262,
    4127.94209, 4688.964294, 321.2953495, 95.37104847, 31203.52336,

    # LLM (20)
    237.5777261, 1017.850675, 15746.21112, 92.06107894, 137.0403007,
    97.90399714, 61.77324157, 42.36252279, 2557.161114, 86.89553296,
    27338.29821, 25585.98579, 84.80359785, 29449.93505, 112.6185318,
    81.01940323, 145.8082395, 220.8096065, 163.6181226, 20452.70048,
]

depths = [
        5, 5, 6, 7, 6, 7, 7, 9, 10, 6,
        7, 7, 13, 7, 6, 4, 4, 5, 6, 9,

        8, 8, 9, 9, 10, 10, 11, 8, 6, 10,
        10, 16, 9, 5, 9, 5, 9, 8, 9, 8,

        8, 6, 6, 6, 9, 10, 6, 10, 7, 9,
        6, 8, 7, 5, 6, 7, 5, 8, 7, 11,

        7, 6, 6, 4, 7, 5, 6, 6, 4, 4,
        7, 5, 5, 5, 7, 4, 4, 5, 5, 6,

        6, 7, 5, 9, 10, 11, 5, 9, 6, 10,
        5, 6, 10, 6, 7, 8, 7, 8, 9, 7
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

        "z3", "cvc5", "cvc5", "z3", "z3", "z3", "z3", "z3", "cvc5", "z3"
        "cvc5", "cvc5", "z3", "cvc5", "z3", "z3", "z3", "z3", "z3", "cvc5"
    ]



def main():
    boxplot()
    stacked_bar_plot()
    shaded_linegraph_combined()
    runtime_vs_depths_by_solver()
    depth_distribution()

if __name__ == "__main__":
    main()