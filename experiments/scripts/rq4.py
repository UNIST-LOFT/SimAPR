from typing import Dict, List
import json
import matplotlib.pyplot as plt
import numpy as np
import seaborn
import pandas as pd

import d4j

orig_result:List[int]=[]
casino_result:List[List[int]]=[[] for _ in range(50)]

def plot_patches_ci_java(mode='tbar'):
    global orig_result,casino_result
    dl = mode in {'recoder', 'alpharepair'}

    # Casino
    for i in range(50):
        for result in d4j.D4J_2_LIST:
            try:
                if dl:
                    result = result.replace('_', '-')
                result_file=open(f'{mode}/result/{result}-casino-{i}/simapr-result.json','r')
            except:
                continue
            root=json.load(result_file)
            result_file.close()

            prev_time=0.
            for res in root:
                is_hq=res['result']
                is_plausible=res['pass_result']
                iteration=res['iteration']
                time=res['time']
                loc=res['config'][0]['location']

                if is_plausible:
                    casino_result[i].append(round((time)/60))

                # if time>3600:
                #     break

    # Original
    for result in d4j.D4J_2_LIST:
        try:
            if dl:
                result = result.replace('_', '-')
            result_file=open(f'{mode}/result/{result}-orig/simapr-result.json','r')
        except:
            continue
        root=json.load(result_file)
        result_file.close()

        prev_time=0.
        for res in root:
            is_hq=res['result']
            is_plausible=res['pass_result']
            iteration=res['iteration']
            time=res['time']
            loc=res['config'][0]['location']

            if is_plausible:
                orig_result.append(round((time)/60))

            # if time>3600:
            #     break

plot_patches_ci_java('tbar')
plot_patches_ci_java('avatar')
plot_patches_ci_java('kpar')
plot_patches_ci_java('fixminer')
plot_patches_ci_java('recoder')
plot_patches_ci_java('alpharepair')
# Plausible patch plot
plt.clf()
fig=plt.figure(figsize=(4,3))

# Original
results=sorted(orig_result)
other_list=[0]
for i in range(0,300):
    if i in results:
        other_list.append(other_list[-1]+results.count(i))
    else:
        other_list.append(other_list[-1])
plt.plot(list(range(0,301)),other_list,'-.b',label='Orig')

# Casino
guided_list:List[List[int]]=[]
guided_x=[]
guided_y=[]
temp_=[[],[],[],[],[]]
for j in range(50):
    cur_result=sorted(casino_result[j])
    guided_list.append([0])
    for i in range(0,300):
        if i in cur_result:
            guided_list[-1].append((50*guided_list[-1][-1]+cur_result.count(i))/50)
            guided_x.append(i)
            guided_y.append((50*guided_list[-1][-1]+cur_result.count(i))/50)
        else:
            guided_list[-1].append(guided_list[-1][-1])
            guided_x.append(i)
            guided_y.append(guided_list[-1][-1])
        if i%60==0:
            temp_[i//60].append(guided_list[-1][-1])
guided_df=pd.DataFrame({'Time':guided_x,'Number of valid patches':guided_y})
seaborn.lineplot(data=guided_df,x='Time',y='Number of valid patches',color='r',label='Casino')
for i in range(5):
    print(f'{i*60}: {np.std(temp_[i])}')

plt.legend(fontsize=12)
plt.xlabel('Time (min)',fontsize=15)
plt.ylabel('# of Valid Patches',fontsize=15)
plt.xticks(fontsize=15)
plt.yticks(fontsize=15)
plt.savefig(f'rq4.pdf',bbox_inches='tight')