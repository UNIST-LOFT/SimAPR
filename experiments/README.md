# How to Reproduce Our Experiment

## Preparing the Patch Space

The steps that should be taken to prepare the patch space are described in the README for each tool such as [TBar/README.md](TBar/README.md). We provide scripts that automate those steps. The usage is slithgly different between template-based tools and learning-based tools.


### Template-Based Tools (TBar, AVATAR, KPar, FixMiner)

The patch space can be constructed by the following:

```
$ cd <tool>
$ python3 <tool>.py <project>
```

The following is a concrete example for Avatar.
```
$ cd avatar
$ python3 avatar.py Chart_4
```
The above commands generate the patch space of Avatar for Chart 4.

### Learning-Based Tools (Recoder, AlphaRepair)


```
cd <tool>
conda activate recoder # or alpha
python3 <tool>.py <project>
```

## Running SimAPR

To run SimAPR with a chosen scheduling algorithm, use `search-<tool>-<algorithm>.py` available under the `<tool>` directory where `<tools>` is one of the following:

- `alphareapir`
- `avatar`
- `fixminer`
- `kpar`
- `recoder`
- `tbar`

and `<algorithm>` is one of the following:

- `orig`
- `casino`
- `seapr` 
- `genprog`

The usage of the script is slightly different depending on which scheduling algoriothm is used.

### Original order and SeAPR
Usage:
```
$ cd <tool>
$ python3 search-<tool>-<orig|seapr>.py <project>
```
* `<project>` is the subject project under consideration

For example, the following uses the original scheduling algorithm of avatar to explore the patch space for Chart 4.

```
$ cd avatar
$ python3 search-avatar-orig.py Chart_4
```

### Casino and GenProg
Since `Casino` and `GenProg` use stochastic approaches, we add an option for random seed.

Usage:
```
$ cd <tool>
$ python3 search-<tool>-<casino|genprog>.py <project> <seed>
```

For example,
```
$ cd avatar
$ python3 search-avatar-casino.py Chart_4 12345678
```


### 50 Seeds we used
We used 50 seeds in our experiments:

```
1812569871, 173066011, 3746108763, 3615336259, 2832411886,
993492328, 621082573, 119179181, 2809525537, 294562554,
343025126, 1218634673, 247518014, 1374654724, 3955729546,
1080441297, 2255798909, 1613363779, 3703518893, 322346823,
2251715956, 3197545572, 3705441198, 3770592464, 261348308,
3077341779, 319352914, 303077664, 1606862434, 992183463,
3036737114, 2593826176, 2577498044, 2421983174, 2504120438,
2071072915, 3234733127, 1994417143, 815481689, 1720353985,
3544204002, 2329962614, 2099923602, 3975296858, 327396666,
2654897829, 178583286, 4094437226, 309772218, 1337657131
```
We put this list in `seeds.py`. If you want to use our seeds, just import `seeds.py`.

### Ablation Study
For ablation study, we run `casino` once without the vertical navigation and the other time without the horizontal navigation. To run the script for our ablation study, do the following:

```
$ cd <tool>
$ python3 search-<tool>-ablation.py <project> <vertical|horizontal> <seed>
```
* `<project>` is the project that you want to run.
* `<vertical|horizontal>`: use `vertical` to run without vertical navigation and `horizontal` to run without the horizontal navigation.
* `<seed>`: random seed number

For example, the following runs Avatar for Chart_4 without the vertical navigation.
```
$ cd avatar
$ python3 search-avatar-ablation.py Chart_4 vertical 12345678
```

## Output
Outputs are saved in `<tool>/result/<project>-<algorithm>`. In this directory, logs are saved in `msv-search.log` and final results are saved in `msv-result.json` for each validated patch.

The following is an example of `msv-result.json`. 
```
{
  "execution": 0,
  "iteration": 1,
  "time": 0.16263937950134277,
  "result": false,
  "pass_result": false,
  "output_distance": -1.0,
  "out_diff": false,
  "pass_all_neg_test": false,
  "compilable": false,
  "total_searched": 1,
  "total_passed": 0,
  "total_plausible": 0,
  "config": [
    {
      "location": "/0_0_1_0_OperatorMutator/Option.java"
    }
  ]
}
```

* `iteration` is the rank of the patch.
* `time` is the time that the patch is tried.
* `result` is the result of failing tests. If `result` is true, then this patch is HQ patch.
* `pass_result` is the result of passing tests. If `pass_result` is true, then this patch is valid patch.
* `pass_all_neg_test` is the result of all failing tests. If `pass_all_neg_test` is true, then this patch passes all failing tests.
* `compilable` is the result of compilation. If `compilable` is false, then this patch is not compilable.
* `total_searched` is the number of searched patches.
* `total_passed` is the number of HQ patches.
* `total_plausible` is the number of valid patches.
* `config` is the ID of this patch.

## Simulation Mode
SimAPR uses the simulation mode by default. Under this mode, SimAPR caches the results of test execution and reuses them at later execution.

Our scripts save cached information in `<tool>/<project>-cache.json` such as the following:
```
"/0_0_1_0_OperatorMutator/Option.java": {
  "basic": false,
  "plausible": false,
  "pass_all_fail": false,
  "compilable": false,
  "fail_time": 0.16263937950134277,
  "pass_time": 0
}
```
`"/0_0_1_0_OperatorMutator/Option.java"` is a key representing a patch ID. The value of `basic` is true if the patch is an "interesting" patch. The value of `plausible` is true if the patch is valid. `pass_all_fail` is true if the patch passes all failing tests. `compilable` is true if the patch is compilable. `fail_time` shows the time taken to run the originally failing tests, and `pass_time` the time taken to run the originally passing tests. Note that if the patch fails the originally failing tests, the originally passing tests are not run and the value of `"pass_time"` is 0.
