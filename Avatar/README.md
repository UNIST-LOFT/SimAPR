# Preparing the Patch Space of Avatar

This document describes how the patch candidates of Avatar can be pre-generated.

## How to run our script to pre-generate patches

First, build AVatar
```
$ ./compile.sh
```

Then, check out the subject project in `buggy/` using the [Defects4J](https://github.com/rjust/defects4j) command:
```
$ defects4j checkout -p <subject> -v <id>b -w buggy/<project>
```
For example,
```
$ defects4j checkout -p Chart -v 4b -w buggy/Chart_4
```

Next, run our script to generate patch candidates:
```
./FLFix.sh <bug_id>
```
Note that `<bug_id>` should be `<subject>_<id>` (e.g. `Chart_4`)

Before running `FLFix.sh`, you should open `FLFix.sh` and adjust variable values.

## Output
Output files are in ```./d4j/<version>/0/```.

Each `<version>` directory contains the following:

* ```switch-info.json```: Meta-information of patch candidates
* Generated patched files