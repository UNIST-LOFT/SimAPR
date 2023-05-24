# SimAPR
SimAPR is patch scheduling framework for patch searching problem.
It supports sequential algorithm from original APR tools, SeAPR, GenProg family algorithm and Casino.

## Why this repository is reusable?
### This repository is highly automated and easy to use
SimAPR is highly automated--pull docker image, create container, and run two scripts. That's it!
See [To run SimAPR](./README_detailed.md#to-run-simapr) section for detailed description.

Also, we prepared various scripts in [experiments](./experiments/) directory to help you to run SimAPR easily.

### This repository contains all necessary that others can extend it
This repository contains every implementation used in SimAPR.

First, we modified 6 APR tools to generate patch space.
They are in [TBar](./TBar), [Avatar](./Avatar), [kPar](./kPar), [Fixminer](./Fixminer), [AlphaRepair](./AlphaRepair) and [Recoder](./Recoder) directories.

Actual implementation of SimAPR is in [SimAPR](./SimAPR) directory and it is written in Python.

Also, this repository contains tools used in our experiments: [DiffTGen](./DiffTGen/) and [ODS](./ODS/).

For our docker image, build new image with [dockerfile](./dockerfile/) or pull docker image from DockerHub!

### README contains details beyond the scope of the paper
We prepared detailed READMEs for each tools.
For example, for TBar, we prepared [README](./TBar/README.md) to describe what we modified and how to compile and run our TBar.

We prepared detailed README of SimAPR in [SimAPR](./SimAPR/) directory.
This README contains how to run SimAPR, detailed inputs, outputs, and options.
It also explains how to add new algorithm to SimAPR.

We also prepared READMEs for [DiffTGen](./DiffTGen/README.md) and [ODS](./ODS/README.md), used in our experiments.

### The artifact is comprehensively documented
First, we explained how to reproduce our experiments in [README_detailed.md](./README_detailed.md).
Just follow 1-4 steps in [README_detailed.md](./README_detailed.md)!

Also, we explained how to run SimAPR for single APR tool and single bug in [To run SimAPR](./README_detailed.md#to-run-simapr).
Just run two scripts!

SimAPR is also extensible. In [SimAPR/README.md](./SimAPR/README.md#How-to-Add-and-Run-a-New-Patch-Scheduling-Algorithm), we explained how to add new algorithm to SimAPR.

## About this repository
<!-- <img src="./overview.png" alt="overview" width="600" title="Overview of SimAPR">

Figure: Overview of SimAPR -->

This repository contains (1) implementation of SimAPR, (2) modified APR tools to generate patch space and (3) scripts and tools to reproduce our experiments. 

### Getting Started
This section describes how to run SimAPR in docker container.
If you want to reproduce our experiments, we already prepared scripts to reproduce our experiments easily.
Please see [Detailed Instruction](#detailed-instruction).

To run SimAPR, you should follow these steps:
- [SimAPR](#simapr)
  - [Why this repository is reusable?](#why-this-repository-is-reusable)
    - [This repository is highly automated and easy to use](#this-repository-is-highly-automated-and-easy-to-use)
    - [This repository contains all necessary that others can extend it](#this-repository-contains-all-necessary-that-others-can-extend-it)
    - [README contains details beyond the scope of the paper](#readme-contains-details-beyond-the-scope-of-the-paper)
    - [The artifact is comprehensively documented](#the-artifact-is-comprehensively-documented)
  - [About this repository](#about-this-repository)
    - [Getting Started](#getting-started)
    - [1. Build docker image and create container](#1-build-docker-image-and-create-container)
    - [2. Generate patch spaces via running APR tools](#2-generate-patch-spaces-via-running-apr-tools)
    - [3. Run SimAPR engine](#3-run-simapr-engine)
    - [The outputs of SimAPR](#the-outputs-of-simapr)
      - [simapr-finished.txt](#simapr-finishedtxt)
      - [simapr-result.json](#simapr-resultjson)
    - [About simulation mode](#about-simulation-mode)
  - [Detailed Instruction](#detailed-instruction)

In this section, we will describe how to run SimAPR with `TBar` and `Closure-62` benchmark.
If you want to run different APR tools and version, change the `tbar` and `TBar` to proper APR tool and `Closure_62` to proper version.

### 1. Build docker image and create container
First, clone our repository:
```
$ git clone https://github.com/FreddyYJ/SimAPR.git
$ cd SimAPR
```

To build docker image, run the following command:
```
$ cd dockerfile
$ docker build -t simapr:1.2 -f D4J-1.2-Dockerfile ..
```

After that, create container with the following command:
```
$ docker run -d --name simapr-1.2 -p 1001:22 simapr:1.2
```

Next, access to the container with the following command:
```
$ ssh -p 1001 root@localhost
```

### 2. Generate patch spaces via running APR tools
Before you run SimAPR, every patch space and patch candidates should be created. To do that, run the following command:
```
# cd SimAPR/experiments/tbar
# python3 tbar.py Closure_62
```

This will take about 2-3 minutes.

Generated patch space is stored in `~/SimAPR/TBar/d4j/Closure_62`.
Meta-information of patch space is stored in `~/SimAPR/TBar/d4j/Closure_62/switch-info.json`.

### 3. Run SimAPR engine
After generating patch space, run SimAPR. To do that, run the following command:
```
# python3 ~/SimAPR/SimAPR/simapr.py -o ~/SimAPR/experiments/tbar/result/Closure_62-out -m <orig/casino/seapr/genprog> -k template -w ~/SimAPR/TBar/d4j/Closure_62 -t 180000 -T 1200 -- python3 ~/SimAPR/SimAPR/script/d4j_run_test.py ~/SimAPR/TBar/buggy
```

SimAPR provides various scheduling algorithms: original, Casino, SeAPR and GenProg.
Original algorithm follows the order generated by the original APR tool.
Set `-m` option as proper scheduling algorithm.

This command sets overall timeout as 20 minutes (It will take slightly more than 20 minutes).
If you want to set timeout for each patch candidate, set `-T` option in seconds.

### The outputs of SimAPR
The outputs of SimAPR are stored in `~/SimAPR/experiments/tbar/result/Closure_62-out`.
This directory contains three files: `simapr-finished.txt`, `simapr-result.json` and `simapr-search.log`.
#### simapr-finished.txt
`simapr-finished.txt` is generated after SimAPR finishes.
It contains overall time information.
* `Running time` is overall time.
* `Select time` is the time to select patch candidates. This time is an overhead from each scheduling algorithm.
* `Test time` is the time to execute test cases for each patch candidate.

Note that `select time` for original algorithm is 0 because original algorithm does not use dynamic scheduling.

#### simapr-result.json
`simapr-result.json` contains the results of each patch candidate in JSON format.
It is a JSON array that contains each result of patch candidates.

Each result contains this information:
* `execution`: Actual test execution. We will describe this later.
* `iteration`: The number of iteration. It will increment by each result.
* `time`: Overall time until this result in second.
* `result`: True if the patch passes at least one failing test. False if the patch fails all failing tests.
* `pass_result`: True if the patch passes all test cases (valid patch).
* `pass_all_neg_test`: True if the patch passes all failing test cases.
* `compilable`: True if the patch is compilable.
* `total_searched`: # of tried patch candidates. It may same with `iteration`.
* `total_passed`: # of patch candidates whose `result` is true.
* `total_plausible`: # of patch candidates whose `pass_result` is true. (# of valid patches)
* `config`: Patch ID.

### About simulation mode
SimAPR provides simulation mode to reduce the overall time.
After SimAPR finished, cached results are stored in `~/SimAPR/experiments/tbar/result/cache/Closure_62-cache.json` in JSON format.
It is a JSON object that its key is patch ID and its value is the result of test execution.

Each cached result contains this information:
* `basic`: True if the patch passes at least one failing test. False if the patch fails all failing tests. Same as `result` in `simapr-result.json`.
* `plausible`: True if the patch passes all test cases (valid patch). Same as `pass_result` in `simapr-result.json`.
* `pass_all_fail`: True if the patch passes all failing test cases. Same as `pass_all_neg_test` in `simapr-result.json`.
* `compilable`: True if the patch is compilable. Same as `compilable` in `simapr-result.json`.
* `fail_time`: The time to execute failing tests.
* `pass_time`: The time to execute passing tests.

Note that `pass_time` is 0 if the patch fails failing tests.

If selected patch candidate is already cached, SimAPR does not execute test cases and use cached result.
Therefore, `execution` in `simapr-result.json` is not incremented.

## Detailed Instruction
Detailed instructions are in [README_detailed.md](./README_detailed.md).