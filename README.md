# SimAPR
SimAPR is a patch scheduling framework for the patch searching problem.
It supports SeAPR, the GenProg family of algorithms, Casino, and the sequential algorithm from the original APR tools.

## Why this repository is reusable?
### This repository is highly automated and easy to use
SimAPR is highly automated.
You only need to pull the Docker image, create a container, and run two scripts. That's it!
For a detailed description, see the [To run SimAPR](./README_detailed.md#to-run-simapr) section.

Additionally, we have provided various scripts in the [experiments](./experiments/) directory to help you run SimAPR easily.

### This repository contains all the necessary components for others to extend it
This repository contains all the implementations used in SimAPR.

First, we have modified six APR tools to generate the patch space.
You can find them in the following directories: [TBar](./TBar), [Avatar](./Avatar), [kPar](./kPar), [Fixminer](./Fixminer), [AlphaRepair](./AlphaRepair) and [Recoder](./Recoder).

The actual Python implementation of SimAPR can be found in the [SimAPR](./SimAPR) directory.
If you want to add your own algorithm, refer to [SimAPR/README.md](./SimAPR/README.md#How-to-Add-and-Run-a-New-Patch-Scheduling-Algorithm) for instructions.

Additionally, this repository provides the [DiffTGen](./DiffTGen/) and [ODS](./ODS/) that we used in our experiments.

You can build a new image for our Docker image using the [dockerfile](./dockerfile/) or pull it from DockerHub.

### README contains details beyond the scope of the paper
We have prepared detailed READMEs for each tool.
For example, we created a [TBar/README](./TBar/README.md) for TBar that explains what we changed and how to build and execute our version of TBar.

A comprehensive [README](./SimAPR/README.md) for SimAPR can be found in the SimAPR directory.
It includes detailed information on inputs, outputs, and parameters for running SimAPR.
It also explains how to upgrade SimAPR with a new algorithm.

We have also provided READMEs for [DiffTGen](./DiffTGen/README.md) and [ODS](./ODS/README.md), which were used in our experiments.

### The artifact is comprehensively documented
We have provided instructions on how to reproduce our experiments in [README_detailed.md](./README_detailed.md).
Simply follow steps 1-4 outlined in [README_detailed.md](./README_detailed.md)!

We have also explained how to run SimAPR for a single APR tool and a single bug in the [To run SimAPR](./README_detailed.md#to-run-simapr) section.
It only requires running two scripts.

SimAPR can also be expanded to include new algorithms. We have described how to add a new algorithm to SimAPR in [SimAPR/README.md](./SimAPR/README.md#How-to-Add-and-Run-a-New-Patch-Scheduling-Algorithm).

## About this repository
This repository contains the implementation of SimAPR, modified APR tools to generate patch space, and scripts and tools to reproduce our experiments.

To reproduce our experiments, please refer to [Detailed Instruction](./README_detailed.md).

### Getting Started
This section explains how to run SimAPR in a Docker container.
We have already provided scripts to simplify the replication of our experiments.
Please refer to the [Detailed Instruction](./README_detailed.md).

- [SimAPR](#simapr)
  - [Why this repository is reusable?](#why-this-repository-is-reusable)
    - [This repository is highly automated and easy to use](#this-repository-is-highly-automated-and-easy-to-use)
    - [This repository contains all the necessary components for others to extend it](#this-repository-contains-all-the-necessary-components-for-others-to-extend-it)
    - [README contains details beyond the scope of the paper](#readme-contains-details-beyond-the-scope-of-the-paper)
    - [The artifact is comprehensively documented](#the-artifact-is-comprehensively-documented)
  - [About this repository](#about-this-repository)
    - [Getting Started](#getting-started)
    - [1. Pull docker image and create container](#1-pull-docker-image-and-create-container)
    - [2. Generate patch spaces via running APR tools](#2-generate-patch-spaces-via-running-apr-tools)
    - [3. Run SimAPR engine](#3-run-simapr-engine)
    - [The outputs of SimAPR](#the-outputs-of-simapr)
      - [simapr-finished.txt](#simapr-finishedtxt)
      - [simapr-result.json](#simapr-resultjson)
    - [About simulation mode](#about-simulation-mode)
  - [Detailed Instruction](#detailed-instruction)

In this section, we'll explain how to use the `TBar` and `Closure-62` benchmarks with SimAPR.
If you want to run various APR tools and versions, make sure to change `tbar` and `TBar` to the appropriate APR tool, and `Closure_62` to the appropriate version.

### 1. Pull docker image and create container
To pill our docker image, run the following command:
```bash
$ docker pull kyj1411/simapr:0.1-1.2
```

After that, create a container with the following command:
```bash
$ docker run -d --name simapr-1.2 -p 1001:22 kyj1411/simapr:0.1-1.2
```

Next, access the container with the following command:
```bash
$ ssh -p 1001 root@localhost
```

### 2. Generate patch spaces via running APR tools
Before running SimAPR, you need to create patch spaces and patch candidates. To do that, run the following command:
```
# cd SimAPR/experiments/tbar
# python3 tbar.py Closure_62
```

This will take about 2-3 minutes.

The generated patch space will be stored in ~/SimAPR/TBar/d4j/Closure_62, and the meta-information of the patch space will be stored in ~/SimAPR/TBar/d4j/Closure_62/switch-info.json.

### 3. Run SimAPR engine
After generating the patch space, run SimAPR by executing the following command:
```
# python3 ~/SimAPR/SimAPR/simapr.py -o ~/SimAPR/experiments/tbar/result/Closure_62-out -m <orig/casino/seapr/genprog> -k template -w ~/SimAPR/TBar/d4j/Closure_62 -t 180000 -T 600 -- python3 ~/SimAPR/SimAPR/script/d4j_run_test.py ~/SimAPR/TBar/buggy
```

SimAPR provides various scheduling algorithms: original, Casino, SeAPR and GenProg.
'Original' algorithm follows the order generated by the original APR tool.
Set `-m` option as appropriate scheduling algorithm.

This command sets overall timeout as 10 minutes (It will take slightly more than 10 minutes).
If you want to change timeout, set `-T` option in seconds.

### The outputs of SimAPR
The outputs of SimAPR are stored in `~/SimAPR/experiments/tbar/result/Closure_62-out`.
This directory contains three files: `simapr-finished.txt`, `simapr-result.json` and `simapr-search.log`.
#### simapr-finished.txt
`simapr-finished.txt` is generated after SimAPR finishes.
It contains overall time information.
* `Running time`: The overall time.
* `Select time` The time taken to select patch candidates. This time is an overhead for each scheduling algorithm.
* `Test time`: The time taken to execute test cases for each patch candidate.

Note that the `select time` for the original algorithm is 0 because the original algorithm does not use dynamic scheduling.

#### simapr-result.json
`simapr-result.json` contains the results of each patch candidate in JSON format.
It is a JSON array that contains the results of each patch candidate.

Each result contains the following information:
* `execution`: Actual test execution. (More details will be described later)
* `iteration`: The number of iterations. It increments with each result.
* `time`: The overall time until this result in seconds.
* `result`: True if the patch passes at least one failing test. False if the patch fails all failing tests.
* `pass_result`: True if the patch passes all test cases (valid patch).
* `pass_all_neg_test`: True if the patch passes all failing test cases.
* `compilable`: True if the patch is compilable.
* `total_searched`: The number of tried patch candidates. It may be the same as `iteration`.
* `total_passed`: The number of patch candidates whose `result` is true.
* `total_plausible`: The number of patch candidates whose `pass_result` is true (number of valid patches).
* `config`: Patch ID.

### About simulation mode
SimAPR provides a simulation mode to reduce the running time.
Cached results are kept in `experiments/tbar/result/cache/Closure_62-cache.json` in JSON format after SimAPR finishes.
It is a JSON object where the patch ID serves as the key, and the test execution result serves as the value.

Each cached result contains the following information:
* `basic`: True if the patch passes at least one failing test. False if the patch fails all failing tests (Same as `result` in `simapr-result.json`).
* `plausible`: True if the patch passes all test cases (valid patch) (Same as `pass_result` in `simapr-result.json`).
* `pass_all_fail`: True if the patch passes all failing test cases (Same as `pass_all_neg_test` in `simapr-result.json`).
* `compilable`: True if the patch is compilable (Same as `compilable` in `simapr-result.json`).
* `fail_time`: The time taken to execute failing tests.
* `pass_time`: The time taken to execute passing tests.

Note that 'pass_time' is 0 if the patch fails the failing tests.

SimAPR does not run test cases and instead uses the cached result if the chosen patch candidate has already been cached.
As a result, the value of `execution` in `simapr-result.json` is not increased.

## Detailed Instruction
To reproduce our experiments, please refer to [README_detailed.md](./README_detailed.md).