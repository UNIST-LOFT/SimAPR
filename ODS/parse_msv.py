import json, shutil, os, sys, shlex, subprocess
from pandas import DataFrame, read_excel
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn import svm
from sklearn.metrics import roc_auc_score
from sklearn.metrics import accuracy_score
from sklearn.metrics import fbeta_score
from sklearn.metrics import recall_score
from sklearn.model_selection import GridSearchCV
from sklearn.decomposition import PCA
from sklearn.metrics import recall_score
from sklearn.metrics import f1_score
from sklearn.metrics import precision_score
from sklearn.metrics import accuracy_score
from imblearn.over_sampling import SMOTE
import matplotlib.pyplot as plt
import itertools
from sklearn.utils import shuffle
from sklearn.impute import SimpleImputer
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from imblearn.pipeline import make_pipeline as imbalanced_make_pipeline
from sklearn.model_selection import GridSearchCV, cross_val_score, StratifiedKFold, learning_curve
from sklearn import svm
from sklearn.utils import shuffle
import xgboost as xgb
import argparse
import glob

def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_plausible_results(msv_results_path, output):
    mkdir(output)
    for directory in os.listdir(f'{msv_results_path}/cache'):
        plausibles = []
        with open(f"{msv_results_path}/cache/{directory}") as f:
            history = json.load(f)
            for patch in history.keys():
                if history[patch]["plausible"]:
                    plausibles.append({patch: history[patch]})

        with open(f"{output}/{directory}", "w+") as f:
            json.dump(plausibles, f)

def copy_patches(msv_results_path_parsed, patch_results_path, output):
    for project in os.listdir(msv_results_path_parsed):
        project_name = project.split("-")[0]
        candidates = json.load(open(f"{msv_results_path_parsed}/{project}"))

        if project_name not in os.listdir(patch_results_path):
            continue

        mkdir(f"{output}/{project_name}")

        for candidate in candidates:
            path = next(iter(candidate.keys()))
            path = path.split("/")[1]

            for patch in os.listdir(f"{patch_results_path}/{project_name}"):
                if patch != path:
                    continue
                shutil.copytree(f"{patch_results_path}/{project_name}/{patch}",
                           f"{output}/{project_name}/{patch}", dirs_exist_ok=True)

def parse_for_coming(plausible_patches, output):
    for project in os.listdir(plausible_patches):
        for file_path in glob.glob(f"{plausible_patches}/{project}/**/*.java", recursive=True):
            rel_file_path = os.path.relpath(file_path, f"{plausible_patches}/{project}")
            print(rel_file_path)
            diff_folder = project + "#" + "-".join(rel_file_path.split("/")[:-1])

            file = file_path.split("/")[-1]
            modif_file = file.split(".")[0]

            mkdir(f"{output}/{diff_folder}/{modif_file}")

            shutil.copyfile(file_path,
                            f"{output}/{diff_folder}/{modif_file}/{diff_folder}_{modif_file}_t.java")

        # for idx in os.listdir(f"{plausible_patches}/{project}"):

        #     diff_folder = project + "-" + idx[:idx.rfind("_")].replace("_", "-")

        #     file = os.listdir(f"{plausible_patches}/{project}/{idx}")[0]
        #     modif_file = os.listdir(f"{plausible_patches}/{project}/{idx}")[0].split(".")[0]

        #     mkdir(f"{output}/{diff_folder}/{modif_file}")

        #     shutil.copyfile(f"{plausible_patches}/{project}/{idx}/{file}",
        #                     f"{output}/{diff_folder}/{modif_file}/{diff_folder}_{modif_file}_t.java")

def get_src_path(project):
    project_name, bug_id = project.split("_")
    if len(bug_id)>=4: bug_id=bug_id[:-3]
    bug_id = int(bug_id)
    if project_name == "Math":
        if bug_id < 85:
            return "/src/main/java/"
        return "/src/java/"
    elif project_name == "Time":
        return "/src/main/java/"
    elif project_name == "Lang":
        if bug_id <= 35:
            return "/src/main/java/"
        return "/src/java/"
    elif project_name == "Chart":
        return "/source/"
    elif project_name == "Closure":
        return "/src/"
    elif project_name == "Mockito":
        return "/src/"
    elif project_name=='Cli':
        if 30 <= bug_id <= 40:
            return '/src/main/java/'
        else:
            return '/src/java/'
    elif project_name=='Codec':
        if bug_id<=10:
            return '/src/java/'
        else:
            return '/src/main/java/'
    elif project_name=='Collections':
        return '/src/main/java/'
    elif project_name=='Compress':
        return '/src/main/java/'
    elif project_name=='Csv':
        return '/src/main/java/'
    elif project_name=='Gson':
        return '/gson/src/main/java/'
    elif project_name=='JacksonCore':
        return '/src/main/java/'
    elif project_name=='JacksonDatabind':
        return '/src/main/java/'
    elif project_name=='JacksonXml':
        return '/src/main/java/'
    elif project_name=='Jsoup':
        return '/src/main/java/'
    elif project_name=='JxPath':
        return '/src/java/'
    return None

def fetch_buggy_files(buggy_projects_path, coming_rep):
    for project in os.listdir(coming_rep):
        project_name = project.split("#")[0]
        src_path = get_src_path(project_name)
        src_file = os.listdir(f"{coming_rep}/{project}")[0]
        target_file = os.listdir(f"{coming_rep}/{project}/{src_file}")[0]

        mid_path = None
        with open(f"{coming_rep}/{project}/{src_file}/{target_file}") as f:
            for line in f.readlines():
                if line.startswith("package "):
                    mid_path = line[8:].strip()[:-1].replace(".", "/")
                    break

        if mid_path is None:
            print("Fail for", project)
            continue

        buggy_file = f"{buggy_projects_path}/{project_name}/{src_path}/{mid_path}/{src_file}.java"

        shutil.copyfile(buggy_file, f"{coming_rep}/{project}/{src_file}/{project}_{src_file}_s.java")

def parse_msv(msv_results_path, patch_results_path, buggy_projects_path, output):
    msv_results_path_parsed = msv_results_path + "-parsed"
    get_plausible_results(msv_results_path, msv_results_path_parsed)
    plausible_output = output + "/" + "plausible_patches"
    copy_patches(msv_results_path_parsed, patch_results_path, plausible_output)
    coming_representation = output + "/" + "coming_rep"
    parse_for_coming(plausible_output, coming_representation)
    fetch_buggy_files(buggy_projects_path, coming_representation)


## Run Coming tool
def run_coming(coming_path, pairs_path, output):
    command = f"java -classpath {coming_path}/coming-0-SNAPSHOT-jar-with-dependencies.jar fr.inria.coming.main.ComingMain -input files -mode features -location {pairs_path} -output {output}/out_features"
    process = subprocess.Popen(shlex.split(command), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(stderr.decode('utf-8'))
        print("Something wrong with Coming")

    print(stdout.decode('utf-8'))

    shutil.move(f"test.csv", f"{output}/test.csv")


def run_ods(test_path, output):
    training_list= "./train.csv"
    testing_list= test_path

    training = pd.read_csv(training_list, encoding='latin1',index_col=False)
    testing = pd.read_csv(testing_list, encoding='latin1',index_col=False)

    X_train = training.iloc[:,2:]
    Y_train = training.iloc[:,1]
    X_test = testing.iloc[:,1:]
    id_test = testing.iloc[:,0]

    X_train, Y_train = shuffle(X_train, Y_train, random_state=0)
    X_train, Y_train = X_train.values, Y_train.values
    model = xgb.XGBClassifier(random_state=42, max_depth=6, gamma=0.5)
    eval_set=[(X_train,Y_train)]
    model.fit(X_train,Y_train, early_stopping_rounds=30, eval_metric="mae", eval_set=eval_set)
    Y_pred = model.predict_proba(X_test)[:, 0]
    result={'patch':id_test,'prediction_label':Y_pred}
    resultDF = pd.DataFrame(result)
    resultDF.to_csv(f'{output}/prediction.csv')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        prog = 'test',
                        description = '=',
                        epilog = '=')
    parser.add_argument("--msv_results_path")
    parser.add_argument("--patches_path")
    parser.add_argument("--buggy_projects_path")
    parser.add_argument("--output")
    parser.add_argument("--coming_tool_path")

    args = parser.parse_args()

    parse_msv(args.msv_results_path, args.patches_path, args.buggy_projects_path, args.output)

    coming_representation = args.output + "/" + "coming_rep"
    run_coming(args.coming_tool_path, coming_representation, args.output)
    test_path = args.output + "/test.csv"
    run_ods(test_path, args.output)
