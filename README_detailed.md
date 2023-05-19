## Detailed Instruction

### Workflow
Workflow is same as Getting Started, but we will describe more details.
1. Setup environment via docker
2. Generate patch space
3. Run SimAPR, a patch scheduler
4. Run scripts to generate plots used in our paper
   
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

Running time will be about 35 hours for each tools without parallel running.
It takes about 5 minutes for each version.

**NOTE**: This will take a lot of time, memory and disk space. We recommend to make **10TB** for disk space for each tools.
**NOTE**: We highly recommend to run each tools in different machine and copy only final result after SimAPR to same machine.

#### Template-based APR tools
Run following commands to generate patch spaces for `TBar`, `Avatar`, `kPar` and `Fixminer`:
```
$ cd experiments/<tool>
$ python3 gen-patch.py <# of CPU>
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
$ python3 gen-patch.py <# of GPUs>
```
**NOTE**: For learning-based tools, you should assign **GPU** to each process. So, you should assign *1 GPU to 1 process*.

For example, to prepare patch space for ```Recoder``` with 4 GPUs in parallel, run the following command:
```
$ cd experiments/recoder
$ python3 gen-patch.py 4
```

#### Template-based APR tools for Defects4j v2.0
Run these commands in simapr-2.0 container to run with Defects4j v2.0.

Run following commands to generate patch spaces for `TBar`, `Avatar`, `kPar` and `Fixminer` with Defects4j v2.0:
```
$ cd experiments/<tool>
$ python3 gen-patch-d4j2.py <# of CPU>
```
We recommend to use 1/5 of overall CPU cores for parallel run.

#### Learning-based APR tools for Defects4j v2.0
Run these commands in simapr-2.0 container to run with Defects4j v2.0.

Run following commands to generate patch spaces for `AlphaRepair` and `Recoder` with Defects4j v2.0:
```
$ cd experiments/<tool>
$ python3 gen-patch.py <# of GPUs>
```
**NOTE**: For learning-based tools, you should assign **GPU** to each process. So, you should assign *1 GPU to 1 process*.

#### Outputs
After this process finished, outputs will be stored in `<tool>/d4j/<version>`.
For example, if you run `TBar` with `Chart_4`, then outputs are stored in `TBar/d4j/Chart_4`.

In this directory,
* `switch-info.json` contains the meta-information of patch space in JSON format.
* The other directories are patch candidates. Path to each patched source file is patch ID.


### 3. Run SimAPR
Before run SimAPR, you should generate every patch spaces for every APR tools.

SimAPR is implemented in Python3 and stored in the [SimAPR](./SimAPR/) directory.

To set up SimAPR, do the following:
```
$ cd SimAPR
$ python3 -m pip install -r requirements.txt
```

We prepared scripts to run SimAPR easily. Those scripts are stored in [experiments](./experiments/) directory, same directory as [patch preparation](#generating-the-patch-space). You can check the [SimAPR's README file](./SimAPR/README.md) for more detailed explaination.

We prepared 3 scripts for each tools: 
* SimAPR for Defects4j v1.2.0
* SimAPR for Defects4j v2.0
* SimAPR for ablation study

#### SimAPR for Defects4j v1.2.0
To run SimAPR for Defects4j v1.2.0 for each tool, run the following command:
```
$ cd experiments/<tool>
$ python3 search.py <# of CPU>
```
This will run original order from original tools once, SeAPR algorithm once, Casino algorithm 50 times and GenProg algorithm 50 times.

The results will be stored in `experiments/<tool>/result`.

For example, for `TBar` with 30 CPU cores, run the following command:
```
$ cd experiments/tbar
$ python3 search.py 30
```

#### SimAPR for Defects4j v2.0
Similar with SimAPR for Defects4j v1.2.0, to run SimAPR for Defects4j v2.0 for each tool, run the following command:
```
$ cd experiments/<tool>
$ python3 search-d4j2.py <# of CPU>
```
This will run same as SimAPR for Defects4j v1.2.0, but with Defects4j v2.0.

The results will be stored in `experiments/<tool>/result`, same as SimAPR for Defects4j v1.2.0.

#### SimAPR for ablation study
To run SimAPR for ablation study for each tool, run the following command:
```
$ cd experiments/<tool>
$ python3 search-ablation.py <# of CPU>
```
This will run Casino algorithm without Vertical search 50 times and Casino algorithm without Horizontal search 50 times.

The results will be stored in `experiments/<tool>/result`, same as SimAPR for Defects4j v1.2.0.

#### SimAPR Output
Outputs will be stored in `experiments/<tool>/result/<version>-<algorithm>`.

For example, Casino algorithm with `TBar` and `Chart_4`, output will be stored in `experiments/tbar/result/Chart_4-casino-<trial>`.
`<trial>` will be 0 to 49 in this case.

There are 3 files in output directory: `simapr-search.log`, `simapr-result.json` and `simapr-finished.txt`.
* `simapr-search.log` contains logs from SimAPR.
* `simapr-result.json` contains the results from SimAPR by each patches in JSON format.
* `simapr-finished.txt` is created when SimAPR finished and it contains overhead by scheduler, overall test execution time and overall running time.

**NOTE**: If you run SimAPR in multiple machine, copy `experiments/<tool>/result` to same machine.


### 4. Run scripts to generate plots used in our paper
Before this step, you should run every scripts (`search.py`, `search-d4j2.py` and `search-ablation.py`) for every tools and check every results are stored in `experiments/<tool>/result` in same machine.

We prepared scripts to generate plots used in our paper.
Those scripts are stored in [experiments/scripts](./experiments/scripts) directory.

#### RQ 1: Search Efficiency
We prepared a script to generate plots for RQ 1 (Figure 6 in the paper).
To generate plots for RQ 1, run the following command:
```
# cd experiments
# python3 scripts/rq1.py
```
This will generate plots for each tools in `experiments/rq1-<tool>.pdf`.

#### RQ 2: Recall

#### RQ 3: Ablation Study
We prepared a script to generate a plot for RQ 3 (Figure 8(a) in the paper).
To generate a plot for RQ 3, run the following command:
```
# cd experiments
# python3 scripts/rq3.py
```
This will generate a plot in `experiments/rq3.pdf`.

#### RQ 4: Generalizability
We prepared a script to generate a plot for RQ 4 (Figure 8(b) in the paper).
To generate a plot for RQ 4, run the following command:
```
# cd experiments
# python3 scripts/rq4.py
```
This will generate a plot in `experiments/rq4.pdf`.