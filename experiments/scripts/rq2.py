from typing import Dict, List, Tuple
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn

import d4j

def parse_ods(mode='tbar'):
    ods_result:Dict[str,List[Tuple[int,str]]]=dict()  # {project: [(score, patch id), ...]}
    with open(f'scripts/ods-{mode}.csv','r') as f:
        for line in f:
            _,patch,score=line.split(',')
            score=float(score.strip())
            patch=patch.strip()

            project,patch_id=patch.split('#')
            if mode=='tbar' or mode=='kpar':
                patch_id='/'+patch_id
            if project not in ods_result:
                ods_result[project]=[]
            ods_result[project].append((score,patch_id))

    for project in ods_result:
        ods_result[project]=sorted(ods_result[project],reverse=True)
    
    return ods_result

casino_result:List[List[Tuple(int,int)]]=[[] for _ in range(50)]
orig_result:List[Tuple(int,int)]=[]
seapr_result:List[Tuple(int,int)]=[]
genprog_result:List[List[Tuple(int,int)]]=[[] for _ in range(50)]

def get_ranking_info_tbar(mode='tbar'):
    with open(f'difftgen-{mode}.csv','r') as f:
        lines=f.readlines()
        correct:Dict[str,List[str]]=dict()
        for line in lines:
            if line[0]!='#':
                cur_line=line.split(',')
            else:
                continue
            cur_ver=cur_line[0].strip().replace('-','_')
            correct[cur_ver]=[]
            for i in range(1,len(cur_line)):
                correct[cur_ver].append(cur_line[i].strip())

    ods_result=parse_ods(mode)

    # Casino
    for i in range(50):
        for result in d4j.D4J_1_2_LIST:
            try:
                simapr_result=open(f'{mode}/result/{result}-casino-{i}/simapr-result.json','r')
            except:
                continue
            root=json.load(simapr_result)
            simapr_result.close()

            cur_result:Dict[str,int]=dict()
            for res in root:
                is_plausible=res['pass_result']
                time=res['time']
                loc=res['config'][0]['location']
                if is_plausible:
                    cur_result[loc]=round(time/60)

            result_file=ods_result[result]

            cur_rank=0
            for res in result_file:
                if res[1] in cur_result.keys():
                    cur_rank+=1
                    is_correct=False
                    if result in correct:
                        if res[1] in correct[result]:
                            is_correct=True
                    
                    if is_correct:
                        casino_result[i].append((cur_result[res[1]],cur_rank))
                        break

    # GenProg
    for i in range(50):
        for result in d4j.D4J_1_2_LIST:
            try:
                simapr_result=open(f'{mode}/result/{result}-genprog-{i}/simapr-result.json','r')
            except:
                continue
            root=json.load(simapr_result)
            simapr_result.close()

            cur_result:Dict[str,int]=dict()
            for res in root:
                is_plausible=res['pass_result']
                time=res['time']
                loc=res['config'][0]['location']
                if is_plausible:
                    cur_result[loc]=round(time/60)

            result_file=ods_result[result]

            cur_rank=0
            for res in result_file:
                if res[1] in cur_result.keys():
                    cur_rank+=1
                    is_correct=False
                    if result in correct:
                        if res[1] in correct[result]:
                            is_correct=True
                    
                    if is_correct:
                        genprog_result[i].append((cur_result[res[1]],cur_rank))
                        break

    # SeAPR
    for result in d4j.D4J_1_2_LIST:
        try:
            simapr_result=open(f'{mode}/result/{result}-seapr/simapr-result.json','r')
        except:
            continue
        root=json.load(simapr_result)
        simapr_result.close()

        cur_result:Dict[str,int]=dict()
        for res in root:
            is_plausible=res['pass_result']
            time=res['time']
            loc=res['config'][0]['location']
            if is_plausible:
                cur_result[loc]=round(time/60)

        result_file=ods_result[result]

        cur_rank=0
        for res in result_file:
            if res[1] in cur_result.keys():
                cur_rank+=1
                is_correct=False
                if result in correct:
                    if res[1] in correct[result]:
                        is_correct=True
                
                if is_correct:
                    seapr_result.append((cur_result[res[1]],cur_rank))
                    break

    # original
    for result in d4j.D4J_1_2_LIST:
        try:
            simapr_result=open(f'{mode}/result/{result}-orig/simapr-result.json','r')
        except:
            continue
        root=json.load(simapr_result)
        simapr_result.close()

        cur_result:Dict[str,int]=dict()
        for res in root:
            is_plausible=res['pass_result']
            time=res['time']
            loc=res['config'][0]['location']
            if is_plausible:
                cur_result[loc]=round(time/60)

        result_file=ods_result[result]

        cur_rank=0
        for res in result_file:
            if res[1] in cur_result.keys():
                cur_rank+=1
                is_correct=False
                if result in correct:
                    if res[1] in correct[result]:
                        is_correct=True
                
                if is_correct:
                    orig_result.append((cur_result[res[1]],cur_rank))
                    break

get_ranking_info_tbar('tbar')
get_ranking_info_tbar('avatar')
get_ranking_info_tbar('kpar')
get_ranking_info_tbar('fixminer')

# Top-1
plt.clf()
fig=plt.figure(figsize=(4,3))

# Original
results=[]
for time,rank in orig_result:
    if rank==1:
        results.append(time)
results=sorted(results)
other_list=[0]
for i in range(0,300):
    if i in results:
        other_list.append(other_list[-1]+results.count(i))
    else:
        other_list.append(other_list[-1])
plt.plot(list(range(0,301)),other_list,'-.b',label='Orig')

# Casino
casino_list:List[List[int]]=[]
for i in range(50):
    cur_result=[]
    for time,rank in casino_result:
        if rank==1:
            cur_result.append(time)
    casino_list.append(cur_result)
guided_list:List[List[int]]=[]
guided_x=[]
guided_y=[]
temp_=[[],[],[],[],[]]
for j in range(50):
    cur_result=sorted(casino_list[j])
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

# SeAPR
results=[]
for time,rank in seapr_result:
    if rank==1:
        results.append(time)
results=sorted(results)
other_list=[0]
for i in range(0,300):
    if i in results:
        other_list.append(other_list[-1]+results.count(i))
    else:
        other_list.append(other_list[-1])
plt.plot(list(range(0,301)),other_list,':g',label='SeAPR')

# GenProg
genprog_list:List[List[int]]=[]
for i in range(50):
    cur_result=[]
    for time,rank in genprog_result:
        if rank==1:
            cur_result.append(time)
    genprog_list.append(cur_result)
guided_list:List[List[int]]=[]
guided_x=[]
guided_y=[]
temp_=[[],[],[],[],[]]
for j in range(50):
    cur_result=sorted(genprog_list[j])
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
other_df=pd.DataFrame({'Time':guided_x,'Number of valid patches':guided_y})
seaborn.lineplot(data=other_df,x='Time',y='Number of valid patches',color='y',label='GenProg',linestyle='dashed')

plt.legend(fontsize=12)
plt.xlabel('Time (min)',fontsize=15)
plt.ylabel('# of Valid Patches',fontsize=15)
plt.xticks(fontsize=15)
plt.yticks(fontsize=15)
plt.savefig(f'rq2-top-1.pdf',bbox_inches='tight')

# Top-5
plt.clf()
fig=plt.figure(figsize=(4,3))

# Original
results=[]
for time,rank in orig_result:
    if rank<=5:
        results.append(time)
results=sorted(results)
other_list=[0]
for i in range(0,300):
    if i in results:
        other_list.append(other_list[-1]+results.count(i))
    else:
        other_list.append(other_list[-1])
plt.plot(list(range(0,301)),other_list,'-.b',label='Orig')

# Casino
casino_list:List[List[int]]=[]
for i in range(50):
    cur_result=[]
    for time,rank in casino_result:
        if rank<=5:
            cur_result.append(time)
    casino_list.append(cur_result)
guided_list:List[List[int]]=[]
guided_x=[]
guided_y=[]
temp_=[[],[],[],[],[]]
for j in range(50):
    cur_result=sorted(casino_list[j])
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

# SeAPR
results=[]
for time,rank in seapr_result:
    if rank<=5:
        results.append(time)
results=sorted(results)
other_list=[0]
for i in range(0,300):
    if i in results:
        other_list.append(other_list[-1]+results.count(i))
    else:
        other_list.append(other_list[-1])
plt.plot(list(range(0,301)),other_list,':g',label='SeAPR')

# GenProg
genprog_list:List[List[int]]=[]
for i in range(50):
    cur_result=[]
    for time,rank in genprog_result:
        if rank<=5:
            cur_result.append(time)
    genprog_list.append(cur_result)
guided_list:List[List[int]]=[]
guided_x=[]
guided_y=[]
temp_=[[],[],[],[],[]]
for j in range(50):
    cur_result=sorted(genprog_list[j])
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
other_df=pd.DataFrame({'Time':guided_x,'Number of valid patches':guided_y})
seaborn.lineplot(data=other_df,x='Time',y='Number of valid patches',color='y',label='GenProg',linestyle='dashed')

plt.legend(fontsize=12)
plt.xlabel('Time (min)',fontsize=15)
plt.ylabel('# of Valid Patches',fontsize=15)
plt.xticks(fontsize=15)
plt.yticks(fontsize=15)
plt.savefig(f'rq2-top-5.pdf',bbox_inches='tight')
