# SimAPR

## 1. Setup
```
python3 -m pip install -r requirements.txt
```

## 2. Run

Run SimAPR
```
simapr.py -o out-dir -w work-dir -m mode -t timeout -p path-to-msv -- php-test.py src tests workdir
```

## 3. Mode
* guided: default
* seapr: using SeAPR
* original: run original program
* genprog: run GenProg family algorithm