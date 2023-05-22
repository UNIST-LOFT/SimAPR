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


## How to Add and Run a New Patch Scheduling Algorithm

To add a new scheduling algorithm, extend the `Mode` class in [core.py](./core.py) with a new mode number.

```
class Mode(Enum):
  casino = 1
  seapr = 2
  orig = 3
  genprog = 4
```

After that, you can add your own algorithm to the SimAPR easily by modifing [select_patch.py](./select_patch.py) file.

### Template-based tools
For template-based tools, implements your own algorithm in `select_patch_tbar_mode` function.
```
def select_patch_tbar_mode(state: GlobalState) -> TbarPatchInfo:
  if state.mode == Mode.tbar:
    return select_patch_tbar(state)
  elif state.mode==Mode.genprog:
    return select_patch_tbar_genprog(state)
  elif state.mode == Mode.seapr:
    return select_patch_tbar_seapr(state)
  else:
    if use_stochastic(state): 
      return select_patch_tbar_guided(state)
    else:
      return select_patch_tbar(state)
```
We already implemented 4 algorithms: `original tool`, `GenProg` family, `SeAPR` and `Casino`.

To implements new algorithm, parameter should be `state`, contains all global information.
Then, new algorithm should select one `TbarCaseInfo`, create `TbarPatchInfo` and return it.

For example, the signature of the new function should be: `def select_patch_tbar_<new_algorithm>(state: GlobalState) -> TbarPatchInfo`.

Implementation of `original tool` algorithm will be a good example.
```
def select_patch_tbar(state: GlobalState) -> TbarPatchInfo:
  loc = state.patch_ranking.pop(0)
  caseinfo = state.switch_case_map[loc]
  caseinfo.parent.parent.parent.case_rank_list.pop(0)
  return TbarPatchInfo(caseinfo)
```
In line 2, SimAPR gets ID of the first patch from `state.patch_ranking`. `state.patch_ranking` saves the original sequence from original tool. Note that it removes selected patch from `state.patch_ranking`.

In line 3, SimAPR gets actual location of patched file from `state.switch_case_map`. `state.switch_case_map` is the mapping of patch ID and actual location of patched file.

In line 4, SimAPR removes selected patch from the remaining patch list in method level. Actually this line is for handling SeAPR algorithm, but you should insert this line just before the return.

In line 5, create `TbarPatchInfo` and return it.

### Learning-based tools
For learning-based tools, similar as template-based tools, implements new algorithm in `select_patch_recoder_mode` function.
```
def select_patch_recoder_mode(state: GlobalState) -> RecoderPatchInfo:
  if state.mode == Mode.recoder:
    return select_patch_recoder(state)
  elif state.mode==Mode.genprog:
    return select_patch_recoder_genprog(state)
  elif state.mode == Mode.seapr:
    return select_patch_recoder_seapr(state)
  else:
    if use_stochastic(state):
      return select_patch_recoder_guided(state)
    else:
      return select_patch_recoder(state)
```
Same as template-based tools, we already implements 4 algorithms.
everything is same as template-based tools, but new function should select one `RecoderCaseInfo` instead of `TbarCaseInfo` and return `RecoderPatchInfo` instead of `TbarPatchInfo`.

Therefore, the header should be: `def select_patch_tbar_<new_algorithm>(state: GlobalState) -> RecoderPatchInfo`.

### Implementation of Patch Tree
The data structures of Patch Tree are implemented in [core.py](./core.py). If you need additional data structures (e.g. list or dict), just add them in these classes.

The root of the tree is `GlobalState`. Every files are stored in `GlobalState.file_info_map`. The keys are file name, and the values are `FileInfo`.

```
class FileInfo:
  def __init__(self, file_name: str) -> None:
    self.file_name = file_name                          # Name of the patched file
    self.func_info_map: Dict[str, FuncInfo] = dict()    # Methods: f"{func_name}:{func_line_begin}-{func_line_end}"
```
`FileInfo` represents each patched file. File name is stored in `FileInfo.file_name`. Every methods/functions are stored in `FileInfo.func_info_map`. The keys are unique IDs of methods/functions, contain method name and start/end line number. The values are `FuncInfo`.

```
class FuncInfo:
  def __init__(self, parent: FileInfo, func_name: str, begin: int, end: int) -> None:
    self.parent = parent                                      # Parent node (FileInfo)
    self.func_name = func_name                                # Method/function name
    self.begin = begin                                        # Start line number
    self.end = end                                            # End line number
    self.id = f"{self.func_name}:{self.begin}-{self.end}"     # Method ID
    self.line_info_map: Dict[uuid.UUID, LineInfo] = dict()    # Patched lines
```
`FuncInfo` represents each patched method/function. Method/function name is stored in `FuncInfo.func_name` and start/end line number are stored in `FuncInfo.begin/end`. Every lines are stored in `FuncInfo.line_info_map`. The keys are random UUID that identifies each method/function. The values are `LineInfo`.

```
class LineInfo:
  def __init__(self, parent: FuncInfo, line_number: int) -> None:
    self.parent = parent                                                 # Parent node (FuncInfo)
    self.uuid = uuid.uuid4()                                             # Random UUID
    self.line_number = line_number                                       # Patched line
    self.tbar_type_info_map: Dict[str, TbarTypeInfo] = dict()            # Templates, if template-based
    self.recoder_case_info_map: Dict[int, RecoderCaseInfo] = dict()      # Patches, if learning-based
```
`LineInfo` represents each patched line. Line number is stored in `LineInfo.line_number`. If the APR tool is template-based (e.g. `TBar`), Templates are stored in `LineInfo.tbar_type_info_map`. If the APR tool is learning-based (e.g. `Recoder`), Actual patches are stored in `LineInfo.recoder_case_info_map`. For `tbar_type_info_map`, the keys are the names of the templates and the values are `TbarTypeInfo`. For `recoder_case_info_map`, the keys are the ID of the patches and the values are `RecoderCaseInfo`.
* Note: we do not use template level for learning-based tools.

```
class TbarTypeInfo:
  def __init__(self, parent: LineInfo, mutation: str) -> None:
    self.parent = parent                                        # Parent node (LineInfo)
    self.mutation = mutation                                    # Template name
    self.tbar_case_info_map: Dict[str, TbarCaseInfo] = dict()   # Patches
```
`TbarTypeInfo` represents each template for template-based APR tools. Template name is stored in `TbarTypeInfo.mutation`. Every patches are stored in `TbarTypeInfo.tbar_case_info_map`. The keys are the patch IDs and the values are `TbarCaseInfo`.

```
class TbarCaseInfo:
  def __init__(self, parent: TbarTypeInfo, location: str, start: int, end: int) -> None:
    self.parent = parent      # Parent node (TbarTypeInfo)
    self.location = location  # Patch ID and relational path of the actual patched file
```
`TbarCaseInfo` represents each actual patches for template-based APR tools (e.g. `TBar`).

```
class RecoderCaseInfo:
  def __init__(self, parent: LineInfo, location: str, case_id: int) -> None:
    self.parent = parent        # Parent node (LineInfo)
    self.location = location    # Relational path of the actual patched file
    self.case_id = case_id      # Patch ID
```
`RecoderCaseInfo` represents each actual patches for learning-based APR tools (e.g. `Recoder`).

The nodes of patch treee are removed in `TbarPatchInfo/RecoderPatchInfo.remove_patch`. In default, each selected nodes are removed after the test execution. After the selected patch is tried, the results of failing tests are updated in `TbarPatchInfo/RecoderPatchInfo.update_result` and the results of passing tests are updated in `TbarPatchInfo/RecoderPatchInfo.update_result_positive` (e.g. vertical search).