# Detailed Instruction

## Workflow
In detailed instruction, we will explain how to reproduce our experimens in our paper.

Following every steps in here will take a lot of time, resources and disk space.
We recommend to follow this instruction in powerful machines.

In our case, we use 256-core and 1TB RAM machine *for each tools* except `Fixminer` and 128-core and 1TB RAM machine for `Fixminer`.
- [Detailed Instruction](#detailed-instruction)
  - [Workflow](#workflow)
  - [1. Setup environment via docker (~ 10 min)](#1-setup-environment-via-docker--10-min)
  - [2. Generating the patch space](#2-generating-the-patch-space)
    - [Generate patch space for RQ 1, 2 and 3](#generate-patch-space-for-rq-1-2-and-3)
      - [Template-based APR tools](#template-based-apr-tools)
      - [Learning-based APR tools](#learning-based-apr-tools)
    - [Generate patch space for RQ 4](#generate-patch-space-for-rq-4)
      - [Template-based APR tools for Defects4j v2.0](#template-based-apr-tools-for-defects4j-v20)
      - [Learning-based APR tools for Defects4j v2.0](#learning-based-apr-tools-for-defects4j-v20)
    - [Outputs](#outputs)
  - [3. Run SimAPR](#3-run-simapr)
    - [RQ 1 \& 2: SimAPR for Defects4j v1.2.0](#rq-1--2-simapr-for-defects4j-v120)
    - [RQ 3: SimAPR for ablation study](#rq-3-simapr-for-ablation-study)
    - [RQ 4: SimAPR for Defects4j v2.0](#rq-4-simapr-for-defects4j-v20)
    - [SimAPR Output](#simapr-output)
  - [4. Run scripts to generate plots used in our paper](#4-run-scripts-to-generate-plots-used-in-our-paper)
    - [RQ 1: Search Efficiency](#rq-1-search-efficiency)
    - [RQ 2: Recall](#rq-2-recall)
      - [To run DiffTGen](#to-run-difftgen)
      - [To run ODS](#to-run-ods)
      - [To generate plots for RQ 2](#to-generate-plots-for-rq-2)
    - [RQ 3: Ablation Study](#rq-3-ablation-study)
    - [RQ 4: Generalizability](#rq-4-generalizability)
  - [Details of SimAPR](#details-of-simapr)
    - [Scripts for our experiments](#scripts-for-our-experiments)
    - [To run SimAPR](#to-run-simapr)
      - [Patch generation](#patch-generation)
      - [Output of patch generation](#output-of-patch-generation)
      - [Run SimAPR](#run-simapr)
      - [Outputs of SimAPR](#outputs-of-simapr)
    - [Patch Generators](#patch-generators)
   
## 1. Setup environment via docker (~ 10 min)
We assumed that you already cloned our repository. If not, look at Getting Started in [README.md](./README.md).

To run SimAPR via Docker, install 
- [docker](https://www.docker.com/)

For learning-based tools, install GPU utilities:
- [NVIDIA driver](https://www.nvidia.com/download/index.aspx)
- [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)

Before you build docker image, find proper CUDA image for your CUDA version at:
- [CUDA images](https://hub.docker.com/r/nvidia/cuda/tags)

And change `FROM` in [Dockerfile](./dockerfile/) to proper CUDA image.
The default is `nvidia/cuda:12.1.1-base-ubuntu22.04`.

**NOTE**: Image should be Ubuntu. Ubuntu 22.04 is recommended.

Then, build the docker image
```
$ cd dockerfile
$ docker build -t simapr:1.2 -f D4J-1.2-Dockerfile ..  # for Defects4j v1.2.0
$ docker build -t simapr:2.0 -f D4J-2.0-Dockerfile ..  # for Defects4j v2.0
```

Next, create and run the docker container
```
$ docker run -d --name simapr-1.2 -p 1001:22 --gpus=all simapr:1.2  # for Defects4j v1.2.0
$ docker run -d --name simapr-2.0 -p 1002:22 --gpus=all simapr:2.0  # for Defects4j v2.0
```
Note that our container uses openssh-server.
To use a container, openssh-client should be installed in host system.

To install openssh-client, run the following command:
```
$ sudo apt-get update
$ sudo apt-get install openssh-client
```

After that, access to the container with the following command:
```
$ ssh -p 1001 root@localhost
```
for Defects4j v1.2.0 and
```
$ ssh -p 1002 root@localhost
```
for Defects4j v2.0.

## 2. Generating the patch space
SimAPR takes the patch space as input to explore patch space and use different patch search algorithm. Regarding the patch space, SimAPR currently provides an option to use the patch space of one of the following six program repair tools:

1. ```Tbar```
2. ```Avatar```
3. ```kPar```
4. ```Fixminer```
5. ```AlphaRepair```
6. ```Recoder```

Patch space generation is tool-specific. 
We provide a Python script in [experiments](./experiments/) directory that automates patch space generation.

Running time will be about 35 hours for each tools without parallel running.
It takes about 5 minutes for each version.

**NOTE**: This will take a lot of time, memory and disk space. We recommend to make **10TB** for disk space for each tools.

**NOTE**: We highly recommend to run each tools in different machine and copy only final result after SimAPR to same machine.

### Generate patch space for RQ 1, 2 and 3
#### Template-based APR tools
Run following commands to generate patch spaces for `TBar`, `Avatar`, `kPar` and `Fixminer`:
```
# cd experiments/<tool>
# python3 gen-patch.py <# of CPU>
```
We recommend to use 1/5 of overall CPU cores for parallel run.

For example, to prepare patch space for ```Tbar``` with 30 cores in parallel, run the following command:
```
# cd experiments/tbar
# python3 gen-patch.py 30
```

#### Learning-based APR tools
Run following commands to generate patch spaces for `AlphaRepair` and `Recoder`:
```
# cd experiments/<tool>
# python3 gen-patch.py <# of GPUs>
```
**NOTE**: For learning-based tools, you should assign **GPU** to each process. So, you should assign *1 GPU to 1 process*.

For example, to prepare patch space for ```Recoder``` with 4 GPUs in parallel, run the following command:
```
# cd experiments/recoder
# python3 gen-patch.py 4
```

### Generate patch space for RQ 4
#### Template-based APR tools for Defects4j v2.0
Run these commands in simapr-2.0 container to run with Defects4j v2.0.

Run following commands to generate patch spaces for `TBar`, `Avatar`, `kPar` and `Fixminer` with Defects4j v2.0:
```
# cd experiments/<tool>
# python3 gen-patch-d4j2.py <# of CPU>
```
We recommend to use 1/5 of overall CPU cores for parallel run.

#### Learning-based APR tools for Defects4j v2.0
Run these commands in simapr-2.0 container to run with Defects4j v2.0.

Run following commands to generate patch spaces for `AlphaRepair` and `Recoder` with Defects4j v2.0:
```
# cd experiments/<tool>
# python3 gen-patch.py <# of GPUs>
```
**NOTE**: For learning-based tools, you should assign **GPU** to each process. So, you should assign *1 GPU to 1 process*.

### Outputs
After this process finished, outputs will be stored in `<tool>/d4j/<version>`.
For example, if you run `TBar` with `Chart_4`, then outputs are stored in `TBar/d4j/Chart_4`.

In this directory,
* `switch-info.json` contains the meta-information of patch space in JSON format.
* The other directories are patch candidates. Path to each patched source file is patch ID.


## 3. Run SimAPR
Before run SimAPR, you should generate every patch spaces for every APR tools.

SimAPR is implemented in Python3 and stored in the [SimAPR](./SimAPR/) directory.

To set up SimAPR, do the following:
```
# cd SimAPR
# python3 -m pip install -r requirements.txt
```

We prepared scripts to run SimAPR easily. Those scripts are stored in [experiments](./experiments/) directory, same directory as [patch preparation](#generating-the-patch-space). You can check the [SimAPR's README file](./SimAPR/README.md) for more detailed explaination.

We prepared 3 scripts for each tools: 
* SimAPR for Defects4j v1.2.0
* SimAPR for Defects4j v2.0
* SimAPR for ablation study

Timeout for each version and each algorithm is 5 hours.
Thanks for the *simulation* mode in SimAPR, it does not take 5 hours for every version, but it still needs a lot of time.

In our experiments, we used 30 CPU cores for each tools and it takes about 3 days for each tools with Defects4j v1.2.0.

### RQ 1 & 2: SimAPR for Defects4j v1.2.0
To run SimAPR for Defects4j v1.2.0 for each tool, run the following command:
```
# cd experiments/<tool>
# python3 search.py <# of CPU>
```
This will run original order from original tools once, SeAPR algorithm once, Casino algorithm 50 times and GenProg algorithm 50 times.

The results will be stored in `experiments/<tool>/result`.

For example, for `TBar` with 30 CPU cores, run the following command:
```
# cd experiments/tbar
# python3 search.py 30
```

### RQ 3: SimAPR for ablation study
To run SimAPR for ablation study for each tool, run the following command:
```
# cd experiments/<tool>
# python3 search-ablation.py <# of CPU>
```
This will run Casino algorithm without Vertical search 50 times and Casino algorithm without Horizontal search 50 times.

The results will be stored in `experiments/<tool>/result`, same as SimAPR for Defects4j v1.2.0.

### RQ 4: SimAPR for Defects4j v2.0
Similar with SimAPR for Defects4j v1.2.0, to run SimAPR for Defects4j v2.0 for each tool, run the following command:
```
# cd experiments/<tool>
# python3 search-d4j2.py <# of CPU>
```
This will run original order from original tools once and Casino algorithm 50 times with Defects4j v2.0.

The results will be stored in `experiments/<tool>/result`, same as SimAPR for Defects4j v1.2.0.

### SimAPR Output
Outputs will be stored in `experiments/<tool>/result/<version>-<algorithm>`.

For example, Casino algorithm with `TBar` and `Chart_4`, output will be stored in `experiments/tbar/result/Chart_4-casino-<trial>`.
`<trial>` will be 0 to 49 in this case.

There are 3 files in output directory: `simapr-search.log`, `simapr-result.json` and `simapr-finished.txt`.
* `simapr-search.log` contains logs from SimAPR.
* `simapr-result.json` contains the results from SimAPR by each patches in JSON format.
* `simapr-finished.txt` is created when SimAPR finished and it contains overhead by scheduler, overall test execution time and overall running time.

**NOTE**: If you run SimAPR in multiple machine, copy `experiments/<tool>/result` to same machine.


## 4. Run scripts to generate plots used in our paper
Before this step, you should run every scripts (`search.py`, `search-d4j2.py` and `search-ablation.py`) for every tools and check every results are stored in `experiments/<tool>/result` in same machine.

We prepared scripts to generate plots used in our paper.
Those scripts are stored in [experiments/scripts](./experiments/scripts) directory.

### RQ 1: Search Efficiency
We prepared a script to generate plots for RQ 1 (Figure 6 in the paper).
To generate plots for RQ 1, run the following command:
```
# cd experiments
# python3 scripts/rq1.py
```
This will generate plots for each tools in `experiments/rq1-<tool>.pdf`.

### RQ 2: Recall
We prepared a script to generate plots for RQ 2 (Figure 7 in the paper).

Before you run this script, you should run DiffTGen and ODS.
#### To run DiffTGen
DiffTGen is used to filter out invalid patches from plausible patches.

To run DiffTGen, run the following command:
```bash
cd DiffTGen
python3 script/extract-candidates.py <tool> /root/SimAPR patches/<tool>

python3 script/driver.py <tool> /root/SimAPR/<tool-dir> patches/<tool>

python3 script/check-results.py <tool> patches/<tool>
```
Result is in `DiffTGen/out/<tool>/<tool>.csv` file. Copy that file to `experiments/difftgen-<tool>.csv`.


#### To run ODS
ODS is used for rank between the valid patches. For easier use, we prepared a script to run ODS.

To run ODS, run the following command:
```
# cd experiments
# python3 scripts/ods.py
```
This will generate outputs in `scripts/ods-<tool>.csv`.

#### To generate plots for RQ 2
To generate plots for RQ 2, run the following command:
```
# cd experiments
# python3 scripts/rq2.py
```
This will generate a plot in `experiments/rq2-top-1.pdf` and `experiments/rq2-top-5.pdf`.

### RQ 3: Ablation Study
We prepared a script to generate a plot for RQ 3 (Figure 8(a) in the paper).
To generate a plot for RQ 3, run the following command:
```
# cd experiments
# python3 scripts/rq3.py
```
This will generate a plot in `experiments/rq3.pdf`.

### RQ 4: Generalizability
We prepared a script to generate a plot for RQ 4 (Figure 8(b) in the paper).
To generate a plot for RQ 4, run the following command:
```
# cd experiments
# python3 scripts/rq4.py
```
This will generate a plot in `experiments/rq4.pdf`.

## Details of SimAPR
This section explains how to run SimAPR and the outputs in detail.

Directory structure of this repository is as follows:
```
SimAPR
├── AlphaRepair
├── Avatar
├── Fixminer
├── kPar
├── Recoder
├── TBar
├── experiments
│   ├── alpharepair
│   ├── avatar
│   ├── fixminer
│   ├── kpar
│   ├── recoder
│   ├── tbar
│   └── scripts
├── SimAPR
├── dockerfile
├── DiffTGen
└── ODS
```

* `AlphaRepair` to `TBar` contains each modified APR tools to generate patch space. See [Patch Generators](#patch-generators) for more details.
* `experiments` contains various scripts to run SimAPR easily. See [Scripts for our experiments](#scripts-for-our-experiments) for more details.
* `SimAPR` contains SimAPR engine.
* `dockerfile` contains Dockerfile to build docker image.
* `DiffTGen` and `ODS` are used for RQ 2 (Recall) in our paper.

### Scripts for our experiments
We prepared various scripts to run our experiments easily in `experiments/<tool>`.
In this section, we will explain about each scripts and how to run them.

* `d4j_<tool>.py` contains benchmark lists of Defects4j v1.2.0 and Defects4j v2.0.
* `seeds.py` contains 50 seeds used in our experiments.
* `<tool>.py` is for generating patch space by running each APR tools.
* `search-<tool>-<algorithm>.py` is for running SimAPR with each tools and each algorithm. `<algorithm>` is `original`, `seapr`, `casino` or `genprog`.
* `search-<tool>-ablation.py` is for running SimAPR with each tools and ablation study for RQ 3 in our paper.

### To run SimAPR
Before run SimAPR, you should generate patch space with modified APR tools.

#### Patch generation
To run SimAPR, first run `<tool>.py` to generate patch space:
```
# cd experiments/<tool>
# python3 <tool>.py <version>
```
`<version>` is a bug version of Defects4j and should follow `<subject>_<bug>` format.
For example, to generate patch space of `Closure-62` with `TBar`, run the following command:
```
# cd experiments/tbar
# python3 tbar.py Closure_62
```

#### Output of patch generation
Outputs will be stored in `<tool>/d4j/<version>`.
For example, if you run `TBar` with `Closure_62`, then outputs are stored in `TBar/d4j/Closure_62`.

In this directory, there are a lot of directories and `switch-info.json` file.
The directories are each patch candidates, and `switch-info.json` contains meta-information of patch space in JSON format.

In `switch-info.json`, there are multiple keys:
* `project_name`: Defects4j version (e.g. `Closure_62`)
* `failing_test_cases`: List of failing test cases
* `passing_test_cases`: List of passing test cases
* `failed_passing_tests`: List of failed test cases that Defects4j marked as passing tests
* `priority`: Descending order of FL result
* `rules`: Patch tree structure
* `func_locations`: Start line and end line of each methods (for patch tree)
* `ranking`: Ranking of each patch candidates. SimAPR with `original` algorithm follows this order.

#### Run SimAPR
Then, run `search-<tool>-<algorithm>.py` to run SimAPR.
Directory should be same as `<tool>.py`.
`<algorithm>` should be one of the following: `orig`, `seapr`, `casino` or `genprog`.

For `orig` and `seapr`, run the following command:
```
# python3 search-<tool>-<algorithm>.py <version>
```
`<version>` is same as `<tool>.py`.
For example, to run SimAPR with `TBar` and `Closure-62` with original order, run the following command:
```
# python3 search-tbar-orig.py Closure_62
```

For `casino` and `genprog`, run the following command:
```
# python3 search-<tool>-<algorithm>.py <version> <seed>
```
`<version>` is same as `<tool>.py`.
Because `casino` and `genprog` algorithms are stochastic and they contain randomness, you should provide seed to SimAPR.
Seed should be integer and smaller than 2^32-1 because of the requirements of NumPy.
Seeds used in our experiments are stored in `seeds.py`.

For example, to run SimAPR with `TBar` and `Closure-62` with Casino algorithm and seed 123, run the following command:
```
# python3 search-tbar-casino.py Closure_62 123
```

#### Outputs of SimAPR
After SimAPR, outputs will be stored in `experiments/<tool>/result/<version>-<algorithm>`.

There are three files in output directory: `simapr-search.log`, `simapr-result.json` and `simapr-finished.txt`.
* `simapr-search.log` contains logs from SimAPR.
* `simapr-result.json` contains the results from SimAPR by each patches in JSON format.
* `simapr-finished.txt` is created when SimAPR finished and it contains overhead by scheduler, overall test execution time and overall running time.

The result of SimAPR is stored in `simapr-result.json`.
This file contains a JSON array of the results of each patches.

Each elements contains these keys:
* `execution`: # of actual test execution. If the patch is cached and tests are not executed, this value does not increment.
* `iteration`: # of iteration. It always increment.
* `time`: Time until the patch is tried.
* `result`: True if the patch passed one or more of the failing test cases. False otherwise.
* `pass_result`: True if the patch passed all test cases (valid patch). False if failed test case is exist.
* `pass_all_neg_test`: True if the patch passed all failing tests. False otherwise.
* `compilable`: True if the patch is compilable.
* `total_searched`: # of tried patches (same as `iteration`).
* `total_passed`: # of patches that `result` is true.
* `total_plausible`: # of valid patches.
* `config`: Patch ID.

For example, `TBar` with `Closure-62`, `simapr-result.json` file contains this element:
```
  {
    "execution": 2,
    "iteration": 2,
    "time": 14.69991660118103,
    "result": false,
    "pass_result": false,
    "output_distance": -1.0,
    "out_diff": false,
    "pass_all_neg_test": false,
    "compilable": true,
    "total_searched": 2,
    "total_passed": 0,
    "total_plausible": 0,
    "config": [
      {
        "location": "/0_0_2_1_VariableReplacer/LightweightMessageFormatter.java"
      }
    ]
  },
```
In this case, patch ID is `/0_0_2_1_VariableReplacer/LightweightMessageFormatter.java`.
This patch is selected and tried in 2nd iteration and it takes about 13.7 seconds until this patch.
This patch failed all failing tests (`result` is false) and also invalid patch (`pass_result` is false) because SimAPR only tries passing tests if a patch passed all failing tests.
However, this patch is compilable (`compilable` is true).

Until this patch, there is no valid patch (`total_plausible` is 0).

### Patch Generators
Patch generators are stored `SimAPR/<tool>` directory.

We modified each tools to generate patch candidates and meta-information of patch space.
Also, we removed patch validation part from each tools because SimAPR will run patch validation.

`Avatar`, `TBar`, `kPar` and `Fixminer` are template-based APR tools and they are written in Java with Maven.
To compile them, just move to each directory and run `./compile.sh`.
For example, for `TBar`, run the following command:
```
# cd TBar
# ./compile.sh
```

However, `AlphaRepair` and `Recoder` are learning-based APR tools and they are written in Python.
You don't need to compile them.

We prepared scripts to generate patch space easily for each tools in `experiments` directory.