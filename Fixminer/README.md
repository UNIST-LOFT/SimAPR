# Preparing the Patch Space of FixMiner

This document describes how the patch candidates of FixMiner can be pre-generated.

## How to run our script to pre-generate patches

First, build FixMiner:
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
java -Xmx<memory-to-use> -cp ./lib/JavaCodeParser-1.0.jar:./target/FixMiner-0.0.1-SNAPSHOT-jar-with-dependencies.jar edu.lu.uni.serval.fixminer.main.Main [option] <test_info_dir> <FL_result_dir> <project_dir> <d4j_dir> <version>
```
where
* ```<test_info_dir>```: Direcotry of test information of each version. Usually it may be ```./FailedTestCases/```.
* ```<FL_result_dir>```: Directory of fault localization result. Usually it may be ```./BugPositions/```.
* ```<project_dir>```: Location of projects. If your project is in ```./buggy/Chart_1/```, then it should be ```./buggy/```.
* ```<d4j_dir>```: Location of Defects4j. If Defects4j is installed in ```/defects4j```, then it should be ```/defects4j/```.
* ```<version>```: Version name to run. Format should be ```<project>_<version>```. (e.g. ```Chart_24```)
#### Important: last character of every paths in arguments should be slash(/).
For example:
```
java -Xmx100G -cp ./lib/JavaCodeParser-1.0.jar:./target/FixMiner-0.0.1-SNAPSHOT-jar-with-dependencies.jar edu.lu.uni.serval.fixminer.main.Main  ./FailedTestCases/ ./BugPositions/ ./buggy/ /defects4j/ Chart_4
```
  
### Options
* ```--max-loc <loc_number>``` or ```-l <loc_number>```: Use only top-```<loc_number>``` ranked locations in FL result.

## Output
Output files are in ```./d4j/<version>/0/```.

In each directory:
* ```switch-info.json```: Meta-information of patch candidates
* ```<FL_rank>/<template>/<id>/<patched_file>```: Patched files 

The fix templates are located in: ```src/main/java/edu/uni/lu/serval/fixminer/fixtemplate```.
