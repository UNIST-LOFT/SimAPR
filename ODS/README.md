```
To use it install Coming and try to run parse_msv Jupyter Notebook file
```

```
Run parse_msv.py to get hte scores

arguments:
 - output : output directory
 - coming_tool_path: path to coming tool
 - buggy_projects_path: path to D4J directory containing buggy projects
 - patches_path: path to directory containing list of patches generated from program repair tool
 - msv_results_path: path to MSV results from iterations

Example:
python3 parse_msv.py --msv_results_path test_env/result-tbar-220830 --patches_path test_env/result_part --buggy_projects_path test_env/buggy_part --output tbar --coming_tool_path /root/projects/coming
```


## ODS Feature Extraction

We have integrated ODS feature extraction with an open source tool [Coming](https://github.com/SpoonLabs/coming).
To extract code features, you can parse a pair of source and target files in Source folder.
Use the feature mode of Coming to obtain ODS features.

# How to use ODS to predict new and unseen patches:

## checkout Coming repository and build it with maven command. Please note the Java version is 1.8.
```
https://github.com/SpoonLabs/coming.git
mvn install -DskipTests
```

## execute the following script with the demo samples in Coming project. You will get a generated csv file called test.csv and the code features in Json format in output path.
```
java -classpath ./target/coming-0-SNAPSHOT-jar-with-dependencies.jar fr.inria.coming.main.ComingMain -input files -mode features -location ./src/main/resources/pairsD4j -output ./out
```
Please be noted that Coming project requires the specific structures of input source and target files:
```
<location_arg>
├── <diff_folder>
│   └── <modif_file>
│       ├── <diff_folder>_<modif_file>_s.java
│       └── <diff_folder>_<modif_file>_t.java
```
## get the test.csv ready and predict it with the following code. You will find the prediction result generated in prediction.csv.
```
python3 predict.py

You may also need the dependecies:
python3 -m pip install  xgboost
python3 -m pip install scikit-learn
python3 -m pip install imblearn
python3 -m pip install matplotlib
```

