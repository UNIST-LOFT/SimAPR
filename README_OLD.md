# SimAPR
SimAPR is patch scheduling framework for patch searching problem.
It supports sequential algorithm from original APR tools, SeAPR, GenProg family algoritm and Casino.

## About this repository
This repository contains implementation of SimAPR, modified APR tools to generate all patch candidates and scripts to run them easily. 

Implementation of SimAPR is in [SimAPR](./SimAPR/). Detailed descriptions are also in this directory.

Our scripts are prepared in [experiments](./experiments/). Detailed descriptions include how to run the scripts are also in this directory.

We prepared 6 APR tools to run SimAPR: `TBar`, `Avatar`, `kPar` and `Fixminer` as template-based APR and `AlphaRepair` and `Recoder` as learning-based APR.

## Environments & Setup

### Environment
- Python >= 3.8
- JDK 1.8
- [Defects4j](https://github.com/rjust/defects4j) 1.2.0 or 2.0.0
- Maven

IMPORTANT: Defects4j should be installed in `/defects4j/` to use the scripts we already prepared. If you use Dockerfiles that we prepared, Defects4j is already installed in `/defects4j/`.

Original Defects4j v1.2.0 supports JDK 1.7, but we run at JDK 1.8.

### Preparing the patch space
SimAPR takes as input the patch space to explore and the patch-scheduling algorithm to use. Regarding the patch space, SimAPR currently provides an option to use the patch space of one of the following six program repair tools:

1. ```Tbar```
2. ```Avatar```
3. ```kPar```
4. ```Fixminer```
5. ```AlphaRepair```
6. ```Recoder```

To construct the patch space provided by one of the above tools, see the README file for the tool. For example, the README file of ```Tbar``` is available at [TBar/README.md](TBar/README.md). We also provide a Python script that automates patch-space preparation. See [experiments](./experiments/).

### Seting up SimAPR
SimAPR is implemented in Python3. SimAPR is in the [SimAPR](./SimAPR/) directory. To set up SimAPR, do the following:
```
$ cd SimAPR
$ python3 -m pip install -r requirements.txt
```

## How to reproduce our experiment
All reproduction scripts and their descriptions are available in the [experiments](./experiments/) directory.

## Running SimAPR
The implementation of SimAPR is available in the [SimAPR](./SimAPR) directory. To run SimAPR, do the following:
```
$ cd SimAPR
$ python3 simapr.py [options] -- {test_command}
```
More details are available in [Readme in SimAPR](./SimAPR/README.md) directory.

### Running SimAPR via Docker
To run SimAPR via Docker, install 
- [docker](https://www.docker.com/)

Plus, you should install the following to utilize GPU for learning-based tools.
- [NVIDIA driver](https://www.nvidia.com/download/index.aspx)
- [nvidia-docker](https://github.com/NVIDIA/nvidia-docker)

Then, build the docker image
```
$ cd dockerfile
$ docker build -t simapr:<1.2/2.0> -f D4J-<1.2/2.0>-Dockerfile .
```

Next, create and run the docker container
```
$ docker run -d --name simapr-<1.2/2.0> -p 1001:22 [--gpus=all] simapr:<1.2/2.0>
```
Note that our container uses openssh-server. To use a container, openssh-client should be installed in host system.

`--gpus` option is required for learning-based tools. If you don't want to use GPU, remove `--gpus=all` option.

To use the container, do the following:
```
$ ssh -p 1001 root@localhost
```

## How to Add and Run a New Patch Scheduling Algorithm

With SimAPR, a new patch-scheduling algorithm can be easily added and evaluated as described in [SimAPR](./SimAPR/README.md).