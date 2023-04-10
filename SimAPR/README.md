# SimAPR

## 1. Environment & Setup
SimAPR required Python >= 3.8. To install dependencies:
```
python3 -m pip install -r requirements.txt
```

## 2. Run

To run SimAPR, do the following:
```
python3 simapr.py [options] -- <commands to run tests...>
```
`<commands to run tests...>` can be multiple arguments.

### Options
* `--outdir/-o <output_dir>`: Directory for outputs. (required)
  
  It will be `SimAPR/experiments/<APR tool>/<bug_id>-<algorithm>` if you use experiment scripts.

* `--workdir/-w <path_to_inputs>`: Directory of generated patches. (required)

  It will be `/root/SimAPR/<APR tool>/d4j/<bug_id>` if you use Dockerfile.

* `--mode/-m <mode>`: Search algorithm. Described in below. (required)

  guided: Casino algorithm\
  seapr: SeAPR algorithm\
  tbar: sequence from original APR tools, for template-based APR tools\
  recoder: sequence from original APR tools, for learning-based APR tools\
  genprog: GenProg family algorithm

* `--tbar-mode` or `--recoder-mode`: Specify APR tool is template- or learning-based. (required)

  Template-based APR tools (`--tbar-mode`): `TBar`, `Avatar`, `kPar`, `Fixminer`\
  Learning-based APR tools (`--recoder-mode`): `AlphaRepair`, `Recoder`

* `--timeout/-t <millisecond>`: Timeout for each single test. (optional, default: 60,000)
  
  Timeout for each tests. If single test expires timeout, it will be killed and considered as failure.

* `--cycle-limit/-E <iteration>`: Maximum number of trial. (optional, default: infinite)
* `--time-limit/-T <second>`: Maximum time to run. (optional, default: infinite)
  
  Maximum trial/time. When the limit is reached, SimAPR will be terminated.\
  If boths are specified, SimAPR terminates when one of the limits is reached.\
  These options are optional, but one of these options are strongly recommended.

* `--correct-patch/-c <correct_patch_id>`: ID of correct patch. (optional, default: None)
  
  Specify patch ID of correct patch(es).\
  It prints more logs for debugging. Also, it is required for `--finish-correct-patch` option.
  Multiple IDs are seperated by comma (`,`).

* `--finish-correct-patch`: Finish when correct patch is found. (optional, default: false)

  `--correct-patch/-c` option should be specified.

* `--use-pattern`: In `seapr` mode, use `SeAPR++` instead of defaule `SeAPR`. (optional, default: false)
  
  `SeAPR++` uses patch pattern(template) additionally for `SeAPR`.\
  No effect in other modes.

* `--use-full-validation` : Use full validation matrix for `SeAPR`. (optional, default: false)
  
  Use full validation matrix for `SeAPR` instead of using partial validation matrix.\
  It runs all tests always, even if the patch failed failing tests. It takes much more time.\
  No effect in other modes.
  
* `--seed <int>`: Use seed for pseudo-random. (optional, default: default seed from Python and NumPy)

  Specify seed for random number generator.\
  Seeds for our experiments are in [experiments/README.md](experiments/README.md).\
  Seed should be unsigned integer and lower than 2^32 (requirement from NumPy).
  Default seed is an initial value from Python and NumPy.

* `--ignore-compile-error`: Do not update result for non-compilable patch candidates. (optional, default: false)
  
  If patch candidate is not compilable, it will be ignored and does not affect patch tree.\
  If this option is not specified, it will be counted as failure.\
  If you want to run default `SeAPR` algorithm, you should specify this option.

* `--count-compile-fail`: Do not count iteration for non-compilable patch candidates. (optional, default: false)
  
  It this option is true, non-compilable patch candidates are not considered as trial.
  This behavior is also default for `SeAPR`, but we do not use this option.

* `--not-use-<guide/epsilon>`: Do not use vertical/horizontal search. (optional, default: false for both)
  
    If this option is specified, SimAPR does not use vertical/horizontal search for Casino algorithm.\
    This option is used for ablation study.\
    Using both options is not allowed.\
    No effect for other modes.