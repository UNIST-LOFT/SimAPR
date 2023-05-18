## Detailed Instruction

### Workflow
Workflow is same as Getting Started, but we will describe more details.
1. Setup environment via docker
2. Generate patch space
3. Run SimAPR, a patch scheduler
   
### 1. Setup environment via docker (~ 10 min)
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
Ubuntu 22.04 is recommended.

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

#### Template-based APR tools
Run following commands to generate patch spaces for `TBar`, `Avatar`, `kPar` and `Fixminer`:
```
$ cd experiments/<tool>
$ python3 gen-patch.py <# of CPU for parallel run>
```
We recommend to use 1/5 of overall CPU cores for parallel run.

For example, to prepare patch space for ```Tbar``` with 30 cores in parallel, run the following command:
```
$ cd experiments/tbar
$ python3 gen-patch.py 30
```

#### Learning-based APR tools
Run following commands to generate patch spaces for `AlphaRepair` and `Recoder`:
```
$ cd experiments/<tool>
$ python3 gen-patch.py <# of GPUs for parallel run>
```
**NOTE**: For learning-based tools, you should assign **GPU** to each process. So, you should assign *1 GPU to 1 process*.

For example, to prepare patch space for ```Recoder``` with 4 GPUs in parallel, run the following command:
```
$ cd experiments/recoder
$ python3 gen-patch.py 4
```

#### Outputs
After this process finished, outputs will be stored in `<tool>/d4j/<version>`.
For example, if you run `TBar` with `Chart_4`, then outputs are stored in `TBar/d4j/Chart_4`.

In this directory,
* `switch-info.json` contains the meta-information of patch space in JSON format.
* The other directories are patch candidates. Path to each patched source file is patch ID.

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