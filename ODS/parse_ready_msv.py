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

## Run Coming tool
def run_coming(coming_path, pairs_path, output):
    command = f"java -classpath {coming_path}/target/coming-0-SNAPSHOT-jar-with-dependencies.jar fr.inria.coming.main.ComingMain -input files -mode features -location {pairs_path} -output {output}/out_features"
    process = subprocess.Popen(shlex.split(command), stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(stderr)
        print("Something wrong with Coming")

    print(stdout)

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
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--coming_tool_path")

    args = parser.parse_args()

    coming_representation = args.output + "/" + "coming_rep"
    run_coming(args.coming_tool_path, args.input, args.output)
    test_path = args.output + "/test.csv"
    run_ods(test_path, args.output)
