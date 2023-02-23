# Preparing the Patch Space of kPar
This document describes how the patch candidates of kPar can be pre-generated.

## How to run our script to pre-generate patches
First, build kPar:
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
$ ./KParFixRunner.sh <project_dir> <version> <d4j_dir> <output_dir>
```
where
* ```<project_dir>```: Location of projects. If your project is in ```./buggy/Chart_1/```, then it should be ```./buggy/```.
* ```<version>```: Version name to run. Format should be ```<project>_<version>```. (e.g. ```Chart_24```)
* ```<d4j_dir>```: Location of Defects4j. If Defects4j is installed in ```/defects4j```, then it should be ```/defects4j/```.
* `<output_dir>`: Location of output. This should be `d4j/`.
  
For example:
```
$ ./KParFixRunner.sh buggy/ Chart_4 /defects4j/ d4j/
```
#### Important: last character of every paths in arguments should be slash(/).
## Output
Output files are in ```./d4j/<version>/```.

In each directory:
* ```switch-info.json```: Meta-information of patch candidates.
* Generated patched files