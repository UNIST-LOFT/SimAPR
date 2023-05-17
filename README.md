# SimAPR
SimAPR is patch scheduling framework for patch searching problem.
It supports sequential algorithm from original APR tools, SeAPR, GenProg family algoritm and Casino.

## About this repository
![Overview of SimAPR](./overview.png)
Figure: Overview of SimAPR

This repository contains (1) implementation of SimAPR, (2) modified APR tools to generate patch space and (3) scripts to reproduce our experiments. 

Implementation of SimAPR is in [SimAPR](./SimAPR/). Detailed descriptions are also in this directory.

Our scripts are prepared in [experiments](./experiments/). Detailed descriptions include how to run the scripts are also in this directory.

We prepared 6 APR tools to run SimAPR: `TBar`, `Avatar`, `kPar` and `Fixminer` as template-based APR and `AlphaRepair` and `Recoder` as learning-based APR.

Note: We already run GZoltar v1.7.3 and put every FL results in this repository.

Note: in our implementation, we provide every locations to APR tool before running SimAPR and APR tool generates every patch candidates for every location.

## Getting Started
This section describes how to run SimAPR in docker container.
If you want to reproduce our experiments, we already prepared scripts to reproduce our experiments easily.
Please see [Detailed Instruction](#detailed-instruction).

To run SimAPR, you should follow these steps:
1. Build docker image and create container
2. Generate patch space via running APR tools modified by us
3. Run SimAPR

In this section, we will describe how to run SimAPR with TBar and Closure-62 benchmark.
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
$ cd SimAPR/experiments/tbar
$ python3 tbar.py Closure_62
```

This will take about 2-3 minutes.

Generated patch space is stored in `~/SimAPR/TBar/d4j/Closure_62`.
Meta-information of patch space is stored in `~/SimAPR/TBar/d4j/Closure_62/switch-info.json`.

### 3. Run SimAPR engine
After generating patch space, run SimAPR. To do that, run the following command:
```
python3 ~/SimAPR/SimAPR/simapr.py -o ~/SimAPR/experiments/tbar/result/Closure_62-out -m <orig/casino/seapr/genprog> -k template -w ~/SimAPR/TBar/d4j/Closure_62 -t 180000 --use-simulation-mode ~/SimAPR/experiments/tbar/result/cache/Closure_62-cache.json -T 1200 -- python3 ~/SimAPR/SimAPR/script/d4j_run_test.py ~/SimAPR/TBar/buggy
```

SimAPR provides various scheduling algorithms: original, Casino, SeAPR and GenProg.
Original algorithm follows the sequence generated by the original APR tool.
Set `-m` option as proper scheduling algorithm.

This command sets overall timeout as 20 minutes (It will take slightly more than 20 minutes).
If you want to set timeout for each patch candidate, set `-T` option in seconds.

### The outputs
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

Each result contains these information:
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

Each cached result contains these information:
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

### Workflow
Workflow is same as Getting Started, but we will describe more details.
1. Setup environment
2. Generate patch space
3. Run SimAPR, a patch scheduler
   
### 1. Environment
Skip this section and go to Using Docker if you use our Dockerfile.

- Python >= 3.8
- JDK 1.8
- [Defects4j](https://github.com/rjust/defects4j) 1.2.0 or 2.0.0
- Maven
- [Anaconda](https://www.anaconda.com/)

IMPORTANT: Defects4j should be installed in `/defects4j/` to use the scripts we already prepared. If you use Dockerfiles that we prepared, Defects4j is already installed in `/defects4j/`.

Original Defects4j v1.2.0 supports JDK 1.7, but we run at JDK 1.8.

You should setup conda environment for `Recoder` and `AlphaRepair`. This is also already prepared in Dockerfile.
```bash
apt install build-essential git python3 openjdk-8-jdk maven unzip perl cpanminus

git clone https://github.com/rjust/defects4j.git /defects4j
pushd /defects4j 
git checkout v1.2.0 && cpanm --installdeps . && ./init.sh
popd

wget https://repo.anaconda.com/archive/Anaconda3-2022.10-Linux-x86_64.sh
sh ./Anaconda3-2022.10-Linux-x86_64.sh -b
export PATH="/defects4j/framework/bin:/root/anaconda3/bin:$PATH"
echo 'export PATH=/defects4j/framework/bin:/root/anaconda3/bin:$PATH' > /root/.bash_aliases
conda init bash
pushd Recoder
conda env create -f data/env.yaml
popd
pushd AlphaRepair
conda env create -f data/env.yaml
popd
```

#### Using Docker
To run SimAPR via Docker, install 
- [docker](https://www.docker.com/)

#### GPU for learning-based tools (optional)
For learning-based tools (`Recoder` and `AlphaRepair`), you should install the following to utilize GPU.
- [NVIDIA driver](https://www.nvidia.com/download/index.aspx)
- [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)

Before you build docker image, find proper CUDA image for your CUDA version:
- [CUDA images](https://hub.docker.com/r/nvidia/cuda/tags)

And change `FROM ubuntu:22.04` in [Dockerfile](./dockerfile/) to proper CUDA image.

Then, build the docker image
```
$ cd dockerfile
$ docker build -t simapr:1.2 -f D4J-1.2-Dockerfile ..  # for Defects4j v1.2.0
$ docker build -t simapr:2.0 -f D4J-2.0-Dockerfile ..  # for Defects4j v2.0
```

Next, create and run the docker container
```
$ docker run -d --name simapr-<1.2/2.0> -p 1001:22 [--gpus=all] simapr:<1.2/2.0>
```
Note that our container uses openssh-server. To use a container, openssh-client should be installed in host system.

`--gpus` option is required for learning-based tools. If you don't want to use GPU, remove `--gpus=all` option.

### 2. Generating the patch space
SimAPR takes the patch space as input to explore patch space and use different patch search algorithm. Regarding the patch space, SimAPR currently provides an option to use the patch space of one of the following six program repair tools:

1. ```Tbar```
2. ```Avatar```
3. ```kPar```
4. ```Fixminer```
5. ```AlphaRepair```
6. ```Recoder```

Patch space construction process is tool-specific. 
We provide a Python script in [experiments](./experiments/) directory that automates patch space preparation.

Run following commands to prepare patch space for template-based tools (```Tbar```, ```Avatar```, ```kPar``` and ```Fixminer```):
```
$ cd experiments/<tool>
$ python3 <tool>.py <version>
```
For example, to prepare patch space for ```Tbar``` on ```Chart_4``` version, run the following command:
```
$ cd experiments/tbar
$ python3 tbar.py Chart_4
```

For learning-based tools (`Recoder` and `AlphaRepair`), we used Conda virtual environment and GPU.
To run these tools, you should run the following commands:
```
$ cd experiments/<tool>
$ python3 <tool>.py <version> <GPU core ID>
```
`<GPU core ID>` is the ID of GPU core to use (starts from 1).
For example,
```
$ cd experiments/recoder
$ python3 recoder.py Chart_4 1
```
This will run `Recoder` on `Chart_4` version with GPU core 1.

If you assign same core to multiple processes, GPU can stop and become unavailable until you reboot the system. So, you must assign core to single process at a time.

#### Outputs
After this process finished, outputs will be stored in `<tool>/d4j/<version>`.
For example, if you run `TBar` with `Chart_4`, then outputs are stored in `TBar/d4j/Chart_4`.

In this directory,
* `switch-info.json` contains the meta-information of patch space in JSON format.
* The other directories are patch candidates. Path to each patched source file is patch ID.

To construct the patch space without provided scripts, see the README file for each tool. For example, the README file of ```Tbar``` is available at [TBar/README.md](TBar/README.md).

### 3. Run SimAPR
After patch space in prepared, you can run SimAPR.

SimAPR is implemented in Python3 and stored in the [SimAPR](./SimAPR/) directory.

To set up SimAPR, do the following:
```
$ cd SimAPR
$ python3 -m pip install -r requirements.txt
```

We prepared scripts to run SimAPR easily. Those scripts are stored in [experiments](./experiments/) directory, same directory as [patch preparation](#generating-the-patch-space). You can check the [SimAPR's README file](./SimAPR/README.md) for more detailed explaination.

We prepared 5 scripts for each tools: 
* Original order from original APR tools
* SeAPR algorithm
* GenProg algorithm
* Casino algorithm
* Ablation Study

To run original order and SeAPR algorithm, run following commands:
```
$ cd experiments/<tool>
$ python3 search-<tool>-<orig/seapr>.py <version>
```
For example, to run original order with `TBar` and `Chart_4`:
```
$ cd expeirments/tbar
$ python3 search-tbar-orig.py Chart_4
```

To run GenProg and Casino algorithm, run following commands:
```
$ cd experiments/<tool>
$ python3 search-<tool>-<genprog/casino>.py <version> <seed>
```
In this case, we need a seed for random library.
Seeds used in our experiments are in [experiments/seeds.py](./experiments/seeds.py).

For example, to run Casino algorithm with `TBar` and `Chart_4`:
```
$ cd expeirments/tbar
$ python3 search-tbar-casino.py Chart_4 1812569871
```
This will initialize random library with seed `1812569871`.

Note that we run Casino and GenProg 50 times for each version.

To run ablation study, run following commands:
```
$ cd experiments/<tool>
$ python3 search-<tool>-ablation.py <version> <vertical/horizontal> <seed>
```
In this case, set `vertical` or `horizontal` to specify which ablation study to run.
If it is `vertical`, SimAPR runs without vertical search. If it is `horizontal`, SimAPR runs without horizontal search.

It also needs a seed because it will run SimAPR with Casino algorithm.

Note that we also run ablation study 50 times for each version.

### SimAPR Output
Outputs will be stored in `experiments/<tool>/result/<version>-<algorithm>`.

For example, if you run Casino algorithm with `TBar` and `Chart_4`, output will be stored in `experiments/tbar/result/Chart_4-casino`.

There are 3 files in output directory: `simapr-search.log`, `simapr-result.json` and `simapr-finished.txt`.
* `simapr-search.log` contains logs from SimAPR.
* `simapr-result.json` contains the results from SimAPR by each patches in JSON format.
* `simapr-finished.txt` is created when SimAPR finished and it contains overhead by scheduler, overall test execution time and overall running time.