# Preparing the Patch Space of TBar

This document describes how the patch candidates of TBar can be pre-generated.

## How to run our script to pre-generate patches
First, build TBar:
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

Next, run our script to generate the patch candidates of TBar:
```
$ ./TBarFixRunner.sh <project_dir> <version> <d4j_dir> <output_dir>
```
where 
* ```<project_dir>```: If your subject project is in ```./buggy/Chart_1/```, then you should give ```./buggy/```.
* ```<version>```: The Defects4J version name to run. The format should be ```<project>_<version>```. (e.g. ```Chart_24```)
* ```<d4j_dir>```: The location of Defects4j. If Defects4j is installed in ```/defects4j```, then it should be ```/defects4j/```.
* `<output_dir>`: The location of the output.

#### Important: in each dir argument, the last character of the path should end with a slash mark (/).

For example:
```
$ ./TBarFixRunner.sh buggy/ Chart_4 /defects4j/ d4j/
```

## Output
Output files are stored in ```./d4j/<version>/```.

Each `<version>` directory contains the following:

* ```switch-info.json```: Meta-information of patch candidates
* Generated patched files