# MSV-search

## 1. Setup
```
pip install virtualenv
virtualenv venv
source venv/bin/activate
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

## 3. Options
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
* `--use-fl` : Use fault localization result
* `--use-hierarchical-selection` n : Use p2, p3
* `--use-pass-test` : Use pass test for p3
* `--use-multi-line` n : Use multi-line patch
* `--max-parallel-cpu` procs : 
    Set how many test to run in parallel, for p3
* `--skip-valid` : Skip initial validation