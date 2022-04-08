from enum import Enum
import json
import os


class Key(Enum):
    PASS_ITER=0
    PASS_TIME=1
    PLAUSIBLE_ITER=2
    PLAUSIBLE_TIME=3

def parse(output_file):
    file=open(output_file,'r')
    root=json.load(file)
    file.close()

    result=dict()
    for res in root:
        current_iter=res['iteration']
        current_time=res['time']
        current_result=res['result']
        current_pass_result=res['pass_result']

        if current_result:
            if Key.PASS_ITER not in result:
                result[Key.PASS_ITER]=current_iter
                result[Key.PASS_TIME]=current_time
            if current_pass_result:
                if Key.PLAUSIBLE_ITER not in result:
                    result[Key.PLAUSIBLE_ITER]=current_iter
                    result[Key.PLAUSIBLE_TIME]=current_time

    if Key.PASS_ITER not in result:
        result[Key.PASS_ITER]=0
        result[Key.PASS_TIME]=0
    if Key.PLAUSIBLE_ITER not in result:
        result[Key.PLAUSIBLE_ITER]=0
        result[Key.PLAUSIBLE_TIME]=0
    return result

if __name__=='__main__':
    dir_list=os.listdir(os.getcwd())
    for dir in dir_list:
        if dir[:3]=='out':
            result_file=dir+'/msv-result.json'
            result=parse(result_file)
            print(f'{dir}: pass iter: {result[Key.PASS_ITER]}/time: {result[Key.PASS_TIME]}, plausible iter: {result[Key.PLAUSIBLE_ITER]}/time: {result[Key.PLAUSIBLE_TIME]}')