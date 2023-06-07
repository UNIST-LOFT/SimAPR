# Detailed Instruction

## Workflow
In this detailed instruction, we will explain how to reproduce the experiments presented in our paper.

Please note that completing each step in this guide requires a significant amount of time, energy, and disk space. We recommend following this instruction on powerful machines.

For the `Fixminer` tool, we used machines with 128 cores and 1TB RAM. For all other tools, we used machines with 256 cores and 1TB RAM.
- [Detailed Instruction](#detailed-instruction)
  - [Workflow](#workflow)
  - [1. Setting up the environment via docker (~ 10 min)](#1-setting-up-the-environment-via-docker--10-min)
  - [2. Generating the patch space](#2-generating-the-patch-space)
    - [Generate patch space for RQ 1, 2 and 3](#generate-patch-space-for-rq-1-2-and-3)
      - [Template-based APR tools](#template-based-apr-tools)
      - [Learning-based APR tools](#learning-based-apr-tools)
    - [Generate patch space for RQ 4](#generate-patch-space-for-rq-4)
      - [Template-based APR tools for Defects4j v2.0](#template-based-apr-tools-for-defects4j-v20)
      - [Learning-based APR tools for Defects4j v2.0](#learning-based-apr-tools-for-defects4j-v20)
    - [Outputs](#outputs)
  - [3. Running SimAPR](#3-running-simapr)
    - [RQ 1 \& 2: SimAPR for Defects4j v1.2.0](#rq-1--2-simapr-for-defects4j-v120)
    - [RQ 3: SimAPR for ablation study](#rq-3-simapr-for-ablation-study)
    - [RQ 4: SimAPR for Defects4j v2.0](#rq-4-simapr-for-defects4j-v20)
    - [SimAPR Output](#simapr-output)
  - [4. Generating Plots for Paper](#4-generating-plots-for-paper)
    - [RQ 1: Search Efficiency](#rq-1-search-efficiency)
    - [RQ 2: Recall](#rq-2-recall)
      - [Running DiffTGen](#running-difftgen)
      - [Running ODS](#running-ods)
      - [To generate plots for RQ 2](#to-generate-plots-for-rq-2)
    - [RQ 3: Ablation Study](#rq-3-ablation-study)
    - [RQ 4: Generalizability](#rq-4-generalizability)
  - [Details of SimAPR](#details-of-simapr)
    - [Scripts for our experiments](#scripts-for-our-experiments)
    - [To run SimAPR](#to-run-simapr)
      - [Patch generation](#patch-generation)
      - [Output of patch generation](#output-of-patch-generation)
      - [Running SimAPR](#running-simapr)
      - [Outputs of SimAPR](#outputs-of-simapr)
    - [Patch Generators](#patch-generators)
   
## 1. Setting up the environment via docker (~ 10 min)
To run SimAPR using Docker, you need to install the following:
- [docker](https://www.docker.com/)

If you are using learning-based tools, you also need to install GPU utilities:
- [NVIDIA driver](https://www.nvidia.com/download/index.aspx)
- [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)

Please note that our docker images are based on CUDA 12.0.1 and Ubuntu 22.04.

To pull our docker image, use the following command:
```
$ docker pull kyj1411/simapr:0.1-1.2  # for Defects4j v1.2.0
$ docker pull kyj1411/simapr:0.1-2.0  # for Defects4j v2.0
```

Next, create and run the docker containers:
```
$ docker run -d --name simapr-1.2 -p 1001:22 --gpus=all kyj1411/simapr:0.1-1.2  # for Defects4j v1.2.0
$ docker run -d --name simapr-2.0 -p 1002:22 --gpus=all kyj1411/simapr:2.0-1.2  # for Defects4j v2.0
```
Please note that our containers use `openssh-server`.
To access the container, you need to have `openssh-client` installed on your host system.

To install `openssh-client`, use the following commands:
```
$ sudo apt-get update
$ sudo apt-get install openssh-client
```

After that, you can access the container using the following commands:

For Defects4j v1.2.0 (RQ 1, 2 and 3):
```
$ ssh -p 1001 root@localhost
```
For Defects4j v2.0 (RQ 4):
```
$ ssh -p 1002 root@localhost
```
The password is `root` for both container.

## 2. Generating the patch space
SimAPR requires the patch space as input, which is generated using different program repair tools.
The patch space generation process depends on the tool being used.
In the [experiments](./experiments/) directory, we provide Python scripts that automate the patch space generation process.

Please note that generating the patch space requires a significant amount of time, memory, and disk space.
We recommend allocating at least 10TB of disk space for each tool.

### Generate patch space for RQ 1, 2 and 3
#### Template-based APR tools
To generate the patch space for `TBar`, `Avatar`, `kPar`, and `Fixminer`, use the following commands:
```
# cd experiments/<tool>
# python3 gen-patch.py <# of CPU>
```
We recommend using 1/5 of the total number of CPU cores for parallel execution.

For example, to generate the patch space for `TBar` with 30 cores in parallel, run the following commands:
```
# cd experiments/tbar
# python3 gen-patch.py 30
```

#### Learning-based APR tools
To generate the patch space for `AlphaRepair` and `Recoder`, use the following commands:
```
# cd experiments/<tool>
# python3 gen-patch.py <# of GPUs>
```
Please note that for learning-based tools, each process should be assigned a GPU. Therefore, you should assign 1 GPU to 1 process.

For example, to generate the patch space for ```Recoder``` with 4 GPUs in parallel, run the following command:
```
# cd experiments/recoder
# python3 gen-patch.py 4
```

### Generate patch space for RQ 4
#### Template-based APR tools for Defects4j v2.0
To generate the patch space for `TBar`, `Avatar`, `kPar`, and `Fixminer` with Defects4j v2.0, use the following commands inside the `simapr-2.0` container:
```
# cd experiments/<tool>
# python3 gen-patch-d4j2.py <# of CPU>
```
We recommend using 1/5 of the overall CPU cores for parallel execution.

#### Learning-based APR tools for Defects4j v2.0
To generate the patch space for `AlphaRepair` and `Recoder` with Defects4j v2.0, use the following commands inside the simapr-2.0 container:
```
# cd experiments/<tool>
# python3 gen-patch-d4j2.py <# of GPUs>
```
Please note that for learning-based tools, each process should be assigned a GPU. Therefore, you should assign *1 GPU to 1 process*.

### Outputs
After the patch space generation process is complete, the outputs will be stored in `<tool>/d4j/<version>`.
For example, if you ran `TBar` with `Chart_4`, the outputs will be stored in `TBar/d4j/Chart_4`.

In this directory:
* `switch-info.json` contains the meta-information of the patch space in JSON format.
* The other directories represent patch candidates, and the path to each patched source file corresponds to the patch ID.

## 3. Running SimAPR
Before running SimAPR, make sure you have generated the patch space for each APR tool as mentioned in the previous section.

SimAPR is implemented in Python 3 and is located in the [SimAPR](./SimAPR/) directory. Follow the steps below to set up SimAPR:
```
# cd SimAPR
# python3 -m pip install -r requirements.txt
```

To simplify the process of running SimAPR, we have provided scripts in the [experiments](./experiments/) directory.
These scripts are specific to each tool and version of Defects4j.
For more detailed information, please refer to the [README](./SimAPR/README.md) file in the SimAPR directory.

There are three scripts available for each tool:
* SimAPR for Defects4j v1.2.0
* SimAPR for Defects4j v2.0
* SimAPR for ablation study

Each version and algorithm have a 5-hour timeout. 
However, thanks to the simulation mode in SimAPR, it may not require the full 5 hours for every version, but it still requires a significant amount of time.

In our experiments, we used 30 CPU cores for each tool, and it took approximately 3 days to complete for each tool with Defects4j v1.2.0.
### RQ 1 & 2: SimAPR for Defects4j v1.2.0
To run SimAPR for Defects4j v1.2.0 for each tool, use the following command:
```
# cd experiments/<tool>
# python3 search.py <# of CPU>
```
This will run the original order from the original tools once, followed by the SeAPR algorithm once.
Then, the Casino algorithm and the GenProg algorithm will be performed 50 times each.

The results will be stored in `experiments/<tool>/result`.

For example, to run `TBar` with 30 CPU cores, use the following command:
```
# cd experiments/tbar
# python3 search.py 30
```

### RQ 3: SimAPR for ablation study
To run SimAPR for the ablation study for each tool, use the following command:
```
# cd experiments/<tool>
# python3 search-ablation.py <# of CPU>
```
This will run the Casino algorithm without Vertical search 50 times and the Casino algorithm without Horizontal search 50 times.

The results will be stored in `experiments/<tool>/result`, similar to SimAPR for Defects4j v1.2.0.

### RQ 4: SimAPR for Defects4j v2.0
Similar to SimAPR for Defects4j v1.2.0, to run SimAPR for Defects4j v2.0 for each tool, use the following command:
```
# cd experiments/<tool>
# python3 search-d4j2.py <# of CPU>
```
This will run the original order from the original tools once and the Casino algorithm 50 times with Defects4j v2.0.

The results will be stored in `experiments/<tool>/result`, similar to SimAPR for Defects4j v1.2.0.

### SimAPR Output

The outputs will be stored in `experiments/<tool>/result/<version>-<algorithm>`.

For example, if you ran the Casino algorithm with `TBar` and `Chart_4`, the output will be stored in `experiments/tbar/result/Chart_4-casino-<trial>`,
where `<trial>` ranges from 0 to 49.

Within the output directory, you will find three files:
* `simapr-search.log` contains the logs from SimAPR.
* `simapr-result.json` contains the results from SimAPR for each patch in JSON format.
* `simapr-finished.txt` is created when SimAPR finishes and it contains information such as the overhead by the scheduler, overall test execution time, and overall running time.

**NOTE**: If you are running SimAPR on multiple machines, make sure to copy the `experiments/<tool>/result` directory to the same machine.

## 4. Generating Plots for Paper
Before proceeding with this step, ensure that you have already run the necessary scripts (`search.py`, `search-d4j2.py` and `search-ablation.py`) for each tool and verified that the results are stored in the `experiments/<tool>/result` directory on the same machine.

We have provided scripts to generate the plots used in our paper, which can be found in the [experiments/scripts](./experiments/scripts/) directory.

### RQ 1: Search Efficiency
To generate plots for RQ 1 (Figure 6 in the paper), use the following command:
```
# cd experiments
# python3 scripts/rq1.py
```
This will generate plots for each tool in `experiments/rq1-<tool>.pdf`.

### RQ 2: Recall
For RQ 2 (Figure 7 in the paper), you need to run DiffTGen and ODS first.

#### Running DiffTGen
DiffTGen is used to filter out incorrect patches from valid patches.
To run DiffTGen, use the following commands:
```
# cd DiffTGen
# ant compile
# cd ../experiments
# python3 scripts/difftgen.py
```
The result will be stored in `experiments/<tool>/difftgen.csv`.

#### Running ODS
ODS is used to rank the valid patches.
We have provided a script to run ODS.
To run ODS, use the following command:
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
This will generate plots in `experiments/rq2-top-1.pdf` and `experiments/rq2-top-5.pdf`.

### RQ 3: Ablation Study
To generate a plot for RQ 3 (Figure 8(a) in the paper), use the following command:
```
# cd experiments
# python3 scripts/rq3.py
```
This will generate a plot in `experiments/rq3.pdf`.

### RQ 4: Generalizability
To generate a plot for RQ 4 (Figure 8(b) in the paper), use the following command:
```
# cd experiments
# python3 scripts/rq4.py
```
This will generate a plot in `experiments/rq4.pdf`.

Make sure to execute these commands in the specified directories to generate the desired plots for each research question.

## Details of SimAPR
This section provides detailed instructions for manually running SimAPR. 
The directory structure of the repository is as follows:
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
Here is a breakdown of the key directories:
* `AlphaRepair` to `TBar`: Each directory contains a modified APR tool used to generate the patch space. Refer to the section on [Patch Generators](#patch-generators) for more information.
* `experiments`: This directory contains various scripts that facilitate the execution of SimAPR. Further details are provided in the section on [Scripts for Our Experiments](#scripts-for-our-experiments).
* `SimAPR`: This directory houses the SimAPR engine.
* `dockerfile`: Dockerfiles.
* `DiffTGen` and `ODS`: These directories are used for RQ 2 (Recall) in our paper.

Please refer to the specific sections below for more information on patch generators and scripts.

### Scripts for our experiments
In this section, we provide an overview of the scripts created to facilitate the execution of our experiments within the `experiments/<tool>` directory.
Each script is described along with instructions on how to execute it.

The following scripts are available:
* `d4j_<tool>.py`: Contains benchmark lists of Defects4j v1.2.0 and Defects4j v2.0.
* `seeds.py`: Contains 50 seeds used in our experiments.
* `<tool>.py`: Used for generating the patch space by running each APR tool.
* `search-<tool>-<algorithm>.py`: Used for running SimAPR with each tool and algorithm. `<algorithm>` can be one of the following: `original`, `seapr`, `casino` or `genprog`.
* `search-<tool>-ablation.py`: Used for running SimAPR with each tool and conducting the ablation study for RQ 3 in our paper.

### To run SimAPR
Before running SimAPR, you need to generate the patch space using the provided APR tools.

#### Patch generation
Run `<tool>.py` to generate patch space:
```
# cd experiments/<tool>
# python3 <tool>.py <version>
```
Here, `<version>` should follow the `<subject>_<bug>` format and represents a specific bug version of Defects4j.
For example, to generate the patch space of `Closure-62` using `TBar`, run the following command:
```
# cd experiments/tbar
# python3 tbar.py Closure_62
```

#### Output of patch generation
Outputs will be stored in `<tool>/d4j/<version>`.
For instance, results from running `TBar` with `Closure_62` are saved in `TBar/d4j/Closure_62`.

`switch-info.json` and numerous more directories can be found in this directory.
Each directory is a patch candidate, and `switch-info.json` contains meta-information about the patch space in JSON format.

In `switch-info.json`, there are multiple keys:
* `project_name`: Defects4j version (e.g. `Closure_62`)
* `failing_test_cases`: List of failing test cases
* `passing_test_cases`: List of passing test cases
* `failed_passing_tests`: List of failed test cases that Defects4j marked as passing tests
* `priority`: Descending order of FL result
* `rules`: Patch tree structure
* `func_locations`: Start line and end line of each method (for patch tree)
* `ranking`: Ranking of each patch candidates. SimAPR with `original` algorithm follows this order.

#### Running SimAPR
After generating the patch space, you can proceed to run SimAPR.

Directory should be same as `<tool>.py`.

For `orig` and `seapr` algorithms, run the following command:
```
# python3 search-<tool>-<algorithm>.py <version>
```
Replace `<algorithm>` with either `orig` or `seapr`. 
For example, to run SimAPR with `TBar` and `Closure-62` using the original order, execute the following command:
```
# python3 search-tbar-orig.py Closure_62
```

For `casino` and `genprog` algorithms, run the following command:
```
# python3 search-<tool>-<algorithm>.py <version> <seed>
```
Specify `<seed>` as an integer seed value.
The seeds used in our experiments are stored in seeds.py.
For example, to run SimAPR with `TBar` and `Closure-62` using the `Casino` algorithm and seed 123, execute the following command:
```
# python3 search-tbar-casino.py Closure_62 123
```

#### Outputs of SimAPR
The outputs of SimAPR will be stored in `experiments/<tool>/result/<version>-<algorithm>`.
The output directory will contain three files:
* `simapr-search.log`: Contains the logs from SimAPR.
* `simapr-result.json`: Contains the results from SimAPR by each patch in JSON format.
* `simapr-finished.txt`: Created when SimAPR finished and contains information such as overhead by the scheduler, overall test execution time, and overall running time.

The result of SimAPR is stored in `simapr-result.json`.
This file contains a JSON array of the results of each patch.

Each element contains these keys:
* `execution`: # of actual test execution. If the patch is cached and tests are not executed, this value does not increment.
* `iteration`: # of iteration. It always increments.
* `time`: Time until the patch is tried.
* `result`: True if the patch passed one or more of the failing test cases. False otherwise.
* `pass_result`: True if the patch passed all test cases (valid patch). False if failed test case exist.
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
This patch is selected and tried in 2nd iteration, and it takes about 13.7 seconds until this patch.
This patch failed all failing tests (`result` is false) and also invalid patch (`pass_result` is false) because SimAPR only tries passing tests if a patch passed all failing tests.
However, this patch is compilable (`compilable` is true).

Until this patch, there is no valid patch (`total_plausible` is 0).

### Patch Generators

The patch generators are located in the `SimAPR/<tool>` directory.
We have modified each tool to generate patch candidates and meta-information about the patch space.
Additionally, we removed the patch validation part from each tool because SimAPR handles the patch validation.

The template-based APR tools (`Avatar`, `TBar`, `kPar`, and `Fixminer`) are written in Java with Maven.
To compile them, navigate to each directory and run `./compile.sh`.
For example, to compile `TBar`, use the following commands:
```
# cd TBar
# ./compile.sh
```

On the other hand, the learning-based APR tools (`AlphaRepair` and `Recoder`) are written in Python, so there is no need to compile them.

We have provided scripts in the [experiments](./experiments/) directory to generate the patch space easily for each tool.