# SimAPR

## 1. Environment & Setup
SimAPR required Python >= 3.8. To install dependencies:
```
python3 -m pip install -r requirements.txt
```

## 2. Run

See [Readme in experiments](../experiments/README.md) to reproduce our experiments!
We prepared scripts to run SimAPR easier.

To run SimAPR, do the following:
```
python3 simapr.py [options] -- <commands to run tests...>
```
`<commands to run tests...>` can be multiple arguments.

### Options
* `--outdir/-o <output_dir>`: Directory for outputs. (required)
  
  It will be `SimAPR/experiments/<APR tool>/<bug_id>-<algorithm>` if you use experiment scripts.

* `--workdir/-w <path_to_inputs>`: Directory of generated patches. (required)

  It will be `SimAPR/<APR tool>/d4j/<bug_id>` if you use experiment scripts.

* `--mode/-m <mode>`: Search algorithm. (required)

  casino: Casino algorithm\
  seapr: SeAPR algorithm\
  orig: original sequence from original APR tools\
  genprog: GenProg family algorithm

* `--tool-type/-k <type>`: Type of APR tool. (required)

  template: Template-based APR tools (`TBar`, `Avatar`, `kPar` or `Fixminer`)\
  learning: Learning-based APR tools (`AlphaRepair` or `Recoder`)\
  prapr: `PraPR`

* `--timeout/-t <millisecond>`: Timeout for each single test. (optional, default: 60,000)
  
  Timeout for each tests. If single test expires timeout, it will be killed and considered as failure.

* `--cycle-limit/-E <iteration>`: Maximum number of trial. (optional, default: infinite)
* `--time-limit/-T <second>`: Maximum time to run. (optional, default: infinite)
  
  Maximum trial/time. When the limit is reached, SimAPR will be terminated.\
  If boths are specified, SimAPR terminates when one of the limits is reached.\
  These options are optional, but one of these options are strongly recommended.

* `--use-simulation-mode <cache file>`: Cache and simulate the patch validation results. (optional, default: None)
  
  Use `<cache file>` as simulation file.\
  Saves the result of the patch validation results if the patch is not tried before.\
  If the patch is tried previously, SimAPR do not run the tests and decide the result with cached result.\
  This option is recommended for multiple executions.

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

* `--skip-valid`: Skip validating passing tests before applying patch. (optional, default: false)
  
  In default, SimAPR runs all passing tests before applying patch to prune failed passing tests.

* `--params <parameters>`: Change default parameters. (optional, default: default parameters)
  
  Parameters are `key=value` pairs, and seperated by semicolon (`,`).\
  Here are the list of parameters:
  * ALPHA_INCREASE: Increase factor for alpha for beta-distribution. (default: 1)
  * BETA_INCREASE: Increase factor for beta for beta-distribution. (default: 0)
  * ALPHA_INIT: Initial value of alpha for beta-distribution. (default: 2)
  * BETA_INIT: Initial value of beta for beta-distribution. (default: 2)
  * EPSILON_A and EPSILON_B: parameter for sigmoid function forepsilon-greedy algorithm. (default: 10 and 3)
  
* `--no-exp-alpha`: Increase alpha value of beta-distribution linearly instead of exponentially. (optional, default: false)
  
  Only effects for `casino` mode.

* `--no-pass-test`: Do not run passing tests. (optional, default: false)
  
  Do not run passing tests and do not decide the patch is valid or not.

* `--seapr-mode <seapr layer>`: Specify the layer that SeAPR is applied. (optional, default: function)
  
  Apply SeAPR to specified layer.\
  Should be one of `file`, `function`, `line`, `type`.\
  Default for SimAPR or `SeAPR` is `function`.

* `--top-fl <top fl>`: Finish if the top n locations by FL are tried. (optional, default: infinite)
  
  Finish SimAPR if the top n locations are tried.\
  For example, if `--top-fl 10` is specified, SimAPR will terminate if all patch candidates in the top 10 locations are tried.\

* `--ignore-compile-error`: Do not update result for non-compilable patch candidates. (optional, default: false)
  
  If patch candidate is not compilable, it will be ignored and does not affect patch tree.\
  If this option is not specified, it will be counted as failure.\
  If you want to run default `SeAPR` algorithm, you should specify this option.

* `--not-count-compile-fail`: Do not count iteration for non-compilable patch candidates. (optional, default: false)
  
  It this option is true, non-compilable patch candidates are not considered as trial.
  This behavior is also default for `SeAPR`, but we do not use this option.

* `--not-use-<guide/epsilon>`: Do not use vertical/horizontal search. (optional, default: false for both)
  
    If this option is specified, SimAPR does not use vertical/horizontal search for Casino algorithm.\
    This option is used for ablation study.\
    Using both options is not allowed.\
    No effect for other modes.

## 3. Output
There are 3 files in output directory: `simapr-search.log`, `simapr-result.json` and `simapr-finished.txt`.
`simapr-search.log` contains logs from SimAPR.
`simapr-result.json` contains the results from SimAPR by each patches.
`simapr-finished.txt` is created when SimAPR finished and it contains total patch selecting, total test execution and overall time.

### simapr-result.json
`simapr-result.json` contains the results from SimAPR by each patches in JSON format.

