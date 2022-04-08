# MSV-search

## 1. Setup
```
pip install -r requirements.txt
```

## 2. Run

Run msv-search
```
msv-search.py -o out-dir -w work-dir -m mode -t timeout -p path-to-msv -- php-test.py src tests workdir
```

Make plot from result
```
plot.py -i input-dir -o out-file.png -t title -c correct-patch
```

## 3. Mode
* guided: default
* prophet: using prophet method
* spr: using spr method
* random: random
* seapr: using SeAPR
* original: run original program
* validation: validation


## 4. Options
* `-p` path-to-msv (`--msv-path`)
* `-o` output-directory (`--outdir`)
* `-w` work-directory (`--workdir`)
* `-M` fuzzer-name (`--main-node`)
* `-S` fuzzer-name (`--sub-node`)
* `-t` timeout (`--timeout`)
* `-m` mode (`--mode`)
* `-E` cycle-limit (`--cycle-limit`)
* `-T` time-limit (`--time-limit`)
* `-c` correct-patch (`--correct-patch`)
* `--use-condition-synthesis` : 
    Apply probabilistic approach for constants
* `--use-fl` : (deprecated) Use fault localization result
* `--use-hierarchical-selection` n : (deprecated) Use p2, p3
* `--use-pass-test` : Use pass test for p3
* `--use-multi-line` n : Use multi-line patch
* `--max-parallel-cpu` procs : 
    Set how many test to run in parallel, for p3
* `--skip-valid` : Skip initial validation
* `--use-simulation-mode` previous/msv-result.json : Use result of previous experiment instead of actually run the test.
* `--use-pattern`: Only in `seapr` mode, use `SeAPR++`.
* `--use-full-validation` : Use full validation.
* `--params` params : Use alternative parameters for guided algorithm.

## 5. Project Structure
```
.
├── msv-search.py
├── core.py
├── msv.py
├── select_patch.py
├── run_test.py
├── condition.py
├── msv_result_handler.py
├── plot.py
├── requirements.txt
├── .gitignore
├── README.md
├── cpr/
└── venv/
```

* msv-search.py: Entry point, read config files.
* core.py: Most of data structures are defined
* msv.py: Run MSV
* select_patch.py: Algorithms to select patch from patch space.
* run_test.py: Run test and get result.
* condition.py: Need by conditional patches.
* msv_result_handler.py: Update data using result, remove used patches.
* plot.py: Plot graph from result.
