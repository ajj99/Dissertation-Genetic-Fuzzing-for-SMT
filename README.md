# Dissertation Project

This repository contains the code developed for my dissertation project.

## Requirements

- Python 3.12 (recommended)
- All required Python packages are listed in `requirements.txt`

Install dependencies using:
```
pip install -r requirements.txt
```
## Running the Fuzzers

There are two main entry points depending on the type of fuzzer:

### 1. Genetic Fuzzers

```
Run: GeneticFuzzerForSMT.py
```

This file contains:
- Baseline fuzzer
- Join fuzzer (commented out)

### 2. LLM-Based Fuzzers

```
Run: LLMFuzzerForSMT.py
```

This file contains:
- LLM-guided Mutation
- LLM-guided Crossover
- LLM-guided Mutation and Crossover

### How to Execute
For both files, simply run the `main` function:

```
python GeneticFuzzerForSMT.py
```

or

```
python LLMFuzzerForSMT.py
```

## Feature Analysis and Visualisation

### Bag of Words Features

```
BagOfWords.py
```

- Generates plots for the Bag-of-Words feature set  
- Uses PCA and UMAP for dimensionality reduction  

### Tree-Based Features

```
TreeFeatures.py
```

- Generates plots for the hypothesis-driven depth feature set  
- Uses PCA and UMAP for dimensionality reduction  

### General Graph Plotting

```
GraphPlotting.py
```

- Produces all remaining graphs used in the analysis  

## Notes

- All scripts are self-contained and can be run independently depending on the required experiment or analysis.
- Ensure dependencies are installed before running any file.
- The remaining Python files 