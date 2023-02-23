import statistics
from typing import Dict, List, Tuple
import json
import matplotlib.pyplot as plt
import os
import sys

def get_patch_iteration(dir:str):
    f=open(dir+'/msv-result.json','r')
    data=json.load(f)
    f.close()

    basic=[]
    plausible=[]

    for res in data:
        is_basic=res['result']
        is_plausible=res['pass_result']
        iteration=res['iteration']
        tm = res['time']

        if is_basic:
            basic.append(int(tm / 60))
        if is_plausible:
            plausible.append(int(tm / 60))
        if tm > 3600:
            break
    return basic,plausible

def plot_patches(guided_data: Dict[str,List[str]],other_data: Dict[str,List[str]],mode='tbar',dir_postfix=''):
    guided_result=[[],[]]
    final_guided_result:Dict[str,int]={}

    for i in range(1,21):
        cur_iter_result=[[],[]]
        for name,results in guided_data.items(): # Should be len==1
            for result in results:
                current_name=result.split('-')[0]
                # basic,plausible=get_patch_iteration(f'result-{mode}{dir_postfix}/'+result+f'-{i}')
                # guided_result[0]+=basic
                # guided_result[1]+=plausible
                result_file=open(f'result-{mode}{dir_postfix}/'+result+f'-{i}/msv-result.json','r')
                root=json.load(result_file)
                result_file.close()

                prev_time=0.
                for res in root:
                    is_hq=res['result']
                    is_plausible=res['pass_result']
                    iteration=res['iteration']
                    time=res['time']
                    loc=res['config'][0]['location']

                    if is_hq:
                        guided_result[0].append(int((time)/60))
                    if is_plausible:
                        guided_result[1].append(int((time)/60))
                    if time>7200:
                        break

                    
        
        # guided_result[0]+=cur_iter_result[0]
        # guided_result[1]+=cur_iter_result[1]
    print(len(guided_result[1]))

    other_result=dict() # Dict[experiment_name,[basic,plausible]]
    for name,results in other_data.items():
        cur_result=[[],[]]
        for result in results:
            current_name=result.split('-')[0]
            # basic,plausible=get_patch_iteration(f'result-{mode}{dir_postfix}/'+result)
            # cur_result[0]+=basic
            # cur_result[1]+=plausible
            result_file=open(f'result-{mode}{dir_postfix}/'+result+f'/msv-result.json','r')
            root=json.load(result_file)
            result_file.close()

            for res in root:
                is_hq=res['result']
                is_plausible=res['pass_result']
                iteration=res['iteration']
                time=res['time']
                loc=res['config'][0]['location']

                if is_hq:
                    cur_result[0].append(int((time)/60))
                if is_plausible:
                    cur_result[1].append(int((time)/60))
                
                if time>7200:
                    break

        # cur_result[0]+=basic
        # cur_result[1]+=plausible
    
        if name not in other_result:
            other_result[name]=cur_result
        else:
            other_result[name][0]+=cur_result[0]
            other_result[name][1]+=cur_result[1]
        print(name)
        print(len(other_result[name][1]))

    guided_result[0].sort()
    guided_result[1].sort()
    for name,results in other_data.items():
        other_result[name][0].sort()
        other_result[name][1].sort()
    
    if mode=='fixminer':
        interval=400
    elif mode=='kpar':
        interval=100
    else:
        interval=250
    # Basic patch plot
    plt.clf()
    max_iter=guided_result[0][-1]
    for name,results in other_result.items():
        if max_iter < results[0][-1]:
            max_iter=results[0][-1]
    # max_iter=round(max_iter)
    plt.xlabel('Time',fontsize=16)
    plt.ylabel('Number of basic patches',fontsize=16)
    guided_list=[0]
    guided_scatters_x=[]
    guided_scatters_y=[]
    for i in range(1,max_iter+1):
        if i in guided_result[0]:
            guided_list.append((guided_list[-1]*20+guided_result[0].count(i))/20)
            # guided_list.append(guided_list[-1]+1)
        else:
            guided_list.append(guided_list[-1])
        if i%interval==0:
            guided_scatters_x.append(i)
            guided_scatters_y.append(guided_list[-1])

    plt.plot(list(range(max_iter+1)),guided_list,'r',label='CASINO')
    plt.scatter(guided_scatters_x,guided_scatters_y,c='r',marker='s')

    colors=['b','g','y','m','c','k']
    markers=['^','p','v','o']
    for name,results in other_result.items():
        other_list=[0]
        other_scatters_x=[]
        other_scatters_y=[]
        for i in range(1,max_iter+1):
            if i in results[0]:
                other_list.append(other_list[-1]+results[0].count(i))
            else:
                other_list.append(other_list[-1])
            if i%interval==0:
                other_scatters_x.append(i)
                other_scatters_y.append(other_list[-1])
        plt.plot(list(range(max_iter+1)),other_list,colors[0],label=name)
        plt.scatter(other_scatters_x,other_scatters_y,c=colors[0],marker=markers[0])
        colors.pop(0)
        markers.pop(0)

    plt.legend(fontsize=16)
    # plt.xscale('log',base=10)
    plt.savefig(f'basic-patch-{mode}{dir_postfix}.pdf',bbox_inches='tight')

    # Plausible patch plot
    plt.clf()
    # plt.xlabel('Time',fontsize=16)
    # plt.ylabel('Number of plausible patches',fontsize=16)
    guided_list=[0]
    guided_scatters_x=[]
    guided_scatters_y=[]
    for i in range(1,max_iter+1):
        if i in guided_result[1]:
            guided_list.append((guided_list[-1]*20+guided_result[1].count(i))/20)
            # guided_list.append(guided_list[-1]+guided_result[1].count(i))
        else:
            guided_list.append(guided_list[-1])
            if i%interval==0:
                guided_scatters_x.append(i)
                guided_scatters_y.append(guided_list[-1])
    plt.plot(list(range(max_iter+1)),guided_list,marker='s',markersize=5,markevery=int(max_iter/30),color='r',label='CASINO')
    # plt.plot(guided_result[1],list(range(len(guided_result[1]))),marker='s',markersize=5,markevery=int(max_iter/30),color='r',label='CASINO')
    # plt.scatter(guided_scatters_x,guided_scatters_y,c='r',marker='s',linewidths=1.5,label='CASINO')

    colors=['b','g','y','m','c','k']
    markers=['^','p','v','o']
    for name,results in other_result.items():
        other_list=[0]
        other_scatters_x=[]
        other_scatters_y=[]
        for i in range(1,max_iter+1):
            if i in results[1]:
                other_list.append(other_list[-1]+results[1].count(i))
            else:
                other_list.append(other_list[-1])
            if i%interval==0:
                other_scatters_x.append(i)
                other_scatters_y.append(other_list[-1])
        plt.plot(list(range(max_iter+1)),other_list,markersize=5,markevery=int(max_iter/30),color=colors[0],marker=markers[0],label=name)
        # plt.plot(other_result[name][1],list(range(len(other_result[name][1]))),marker=markers[0],markersize=5,markevery=int(max_iter/30),color=colors[0],label=name)
        # plt.scatter(other_scatters_x,other_scatters_y,c=colors[0],marker=markers[0],linewidths=1.5,label=name)
        colors.pop(0)
        markers.pop(0)

    plt.legend(fontsize=20)
    # plt.xscale('log',base=10)
    plt.xticks(fontsize=20)
    plt.yticks(fontsize=20)
    plt.savefig(f'plausible-patch-{mode}{dir_postfix}.pdf',bbox_inches='tight')




def plot_patches_recoder(guided_data: Dict[str,List[str]],other_data: Dict[str,List[str]],mode='recoder',dir_postfix=''):
    guided_result=[[],[]]
    for i in range(50):
        cur_iter_result=[[],[]]
        for name,results in guided_data.items(): # Should be len==1
            for result in results:
                basic,plausible=get_patch_iteration(f'result-{mode}{dir_postfix}/'+result+f'-220816-rq1-{i}')
                cur_iter_result[0]+=basic
                cur_iter_result[1]+=plausible
        
        guided_result[0]+=cur_iter_result[0]
        guided_result[1]+=cur_iter_result[1]

    other_result=dict() # Dict[experiment_name,[basic,plausible]]
    for name,results in other_data.items():
        cur_result=[[],[]]
        for result in results:
            basic,plausible=get_patch_iteration(f'result-{mode}{dir_postfix}/'+result)
            cur_result[0]+=basic
            cur_result[1]+=plausible
        
        cur_result[0]+=basic
        cur_result[1]+=plausible
    
        if name not in other_result:
            other_result[name]=cur_result
        else:
            other_result[name][0]+=cur_result[0]
            other_result[name][1]+=cur_result[1]

    guided_result[0].sort()
    guided_result[1].sort()
    for name,results in other_data.items():
        other_result[name][0].sort()
        other_result[name][1].sort()
    
    # Basic patch plot
    plt.clf()
    max_iter=guided_result[0][-1]
    for name,results in other_result.items():
        if max_iter < results[0][-1]:
            max_iter=results[0][-1]
    plt.xlabel('Iteration',fontsize=16)
    plt.ylabel('Number of basic patches',fontsize=16)
    guided_list=[0]
    for i in range(1,max_iter+1):
        if i in guided_result[0]:
            guided_list.append((guided_list[-1]*20+guided_result[0].count(i))/20)
        else:
            guided_list.append(guided_list[-1])
    plt.plot(list(range(max_iter+1)),guided_list,'r',label='CASINO')

    colors=['b','g','y','m','c','k']
    for name,results in other_result.items():
        other_list=[0]
        for i in range(1,max_iter+1):
            if i in results[0]:
                other_list.append(other_list[-1]+results[0].count(i))
            else:
                other_list.append(other_list[-1])
        plt.plot(list(range(max_iter+1)),other_list,colors[0],label=name)
        colors.pop(0)

    plt.legend(fontsize=16)
    plt.yscale('log',base=10)
    plt.savefig(f'basic-patch-{mode}{dir_postfix}.pdf',bbox_inches='tight')

    # Plausible patch plot
    plt.clf()
    max_iter=guided_result[1][-1]
    for name,results in other_result.items():
        if max_iter < results[1][-1]:
            max_iter=results[1][-1]
    # plt.xlabel('Iteration',fontsize=16)
    # plt.ylabel('Number of plausible patches',fontsize=16)
    guided_list=[0]
    for i in range(1,max_iter+1):
        if i in guided_result[1]:
            guided_list.append(guided_list[-1]+guided_result[1].count(i))
        else:
            guided_list.append(guided_list[-1])
    plt.plot(list(range(max_iter+1)),guided_list,'r',label='CASINO')

    colors=['b','g','y','m','c','k']
    for name,results in other_result.items():
        if name == 'SeAPR':
            continue
        other_list=[0]
        for i in range(1,max_iter+1):
            if i in results[1]:
                other_list.append(other_list[-1]+results[1].count(i)*20)
            else:
                other_list.append(other_list[-1])
        plt.plot(list(range(max_iter+1)),other_list,colors[0],label=name)
        colors.pop(0)

    plt.legend(fontsize=16)
    plt.yscale('log',base=10)
    plt.savefig(f'plausible-patch-{mode}{dir_postfix}.pdf',bbox_inches='tight')

def hq_patch_len_avg(guided_data: Dict[str,List[str]],mode='tbar',dir_postfix=''):
    guided_result=[[],[]]
    for i in range(1,21):
        cur_iter_result=[]
        cur_iter_result_p=[]
        for name,results in guided_data.items(): # Should be len==1
            for result in results:
                basic,plausible=get_patch_iteration(f'result-{mode}{dir_postfix}/'+result+f'-{i}')
                cur_iter_result.append(len(basic))
                cur_iter_result_p.append(len(plausible))

        guided_result[0].append(statistics.mean(cur_iter_result))
        guided_result[1].append(statistics.mean(cur_iter_result_p))

    return guided_result[0],guided_result[1]
        
def boxplot_hq_patches():
    tbar,tbar_p=hq_patch_len_avg(guided_datas.GUIDED_CORRECT_TBAR,'TBar','-220813')
    kpar,kpar_p=hq_patch_len_avg(guided_datas.GUIDED_CORRECT_KPAR,'kPar','-220813')
    avatar,avatar_p=hq_patch_len_avg(guided_datas.GUIDED_CORRECT_AVATAR,'Avatar','-220813')
    fixminer,fixminer_p=hq_patch_len_avg(guided_datas.GUIDED_CORRECT_FIXMINER,'Fixminer','-220813')

    plt.clf()
    plt.boxplot([tbar,kpar,avatar,fixminer],labels=['TBar','kPar','Avatar','Fixminer'],showfliers=True,vert=True)
    # plt.xlim((0.1,0.65))
    plt.xticks(fontsize=16)
    # plt.margins(x=0.1)
    plt.grid()
    # plt.xlabel('Improvement',fontsize=16)
    # plt.title('Improvement of each group',fontsize=16)
    plt.savefig(f'hq_boxplot.pdf')

    plt.clf()
    plt.boxplot([tbar_p,kpar_p,avatar_p,fixminer_p],labels=['TBar','kPar','Avatar','Fixminer'],showfliers=True,vert=True)
    # plt.xlim((0.1,0.65))
    plt.xticks(fontsize=16)
    # plt.margins(x=0.1)
    plt.grid()
    # plt.xlabel('Improvement',fontsize=16)
    # plt.title('Improvement of each group',fontsize=16)
    plt.savefig(f'plausible_boxplot.pdf')


    

# plot_patches(plausible_data.GUIDED_PLAUSIBLE_TBAR,plausible_data.OTHER_PLAUSIBLE_TBAR,'tbar','-plau-220823')
# plot_patches(plausible_data.GUIDED_PLAUSIBLE_KPAR,plausible_data.OTHER_PLAUSIBLE_KPAR,'kpar','-plau-220823')
# plot_patches(plausible_data.GUIDED_PLAUSIBLE_AVATAR,plausible_data.OTHER_PLAUSIBLE_AVATAR,'avatar','-plau-220823')
# plot_patches(plausible_data.GUIDED_PLAUSIBLE_FIXMINER,plausible_data.OTHER_PLAUSIBLE_FIXMINER,'fixminer','-plau-220823')
# # boxplot_hq_patches()



use_group = False

def check_dir(dir: str) -> bool:
    if not os.path.exists(dir):
        print(f"Dir {dir} does not exist!")
        return False
    return True

def get_correct_patch(correct_patch_csv: str) -> Dict[str, List[str]]:
    result = dict()
    with open(correct_patch_csv, "r") as f:
        for line in f.readlines():
            ln = line.strip()
            if len(ln) < 1 or ln.startswith("#"):
                continue
            tokens = ln.split(",")
            # print(tokens)
            # print(f"{len(bugid)} == {len(tokens[0])}")
            bugid = tokens[0]
            patches = tokens[1:]
            result[bugid] = patches
    return result

def sort_bugids(bugids: List[str]) -> List[str]:
    proj_dict = dict()
    for bugid in bugids:
        proj, id = bugid.split("-")
        if proj not in proj_dict:
            proj_dict[proj] = list()
        proj_dict[proj].append(int(id))
    projs = sorted(list(proj_dict.keys()))
    result = list()
    for proj in projs:
        ids = proj_dict[proj]
        ids.sort()
        for id in ids:
            result.append(f"{proj}-{id}")
    return result

def analyze_result(recoder_path: str, bugid: str, target_dir: str, correct_patches: List[str]) -> Tuple[int, float, int, float, int]:
    """
    Analyze the result of a bugid.
    Return: (plau iter, plau time, correct iter, correct time, total plau)
    """
    result_file = os.path.join(target_dir, f"msv-result.json")
    sim_file = os.path.join(recoder_path, "sim", bugid, f"{bugid}-sim.json")
    sim = dict()
    if os.path.exists(sim_file):
        try:
            with open(sim_file, "r") as f:
                sim = json.load(f)
        except:
            print(bugid + " error!")
    if not os.path.exists(result_file):
        return -1, -1, -1, -1, -1
    with open(result_file, "r") as f:
        root = json.load(f)
        global_time = 0.0
        pi = -1
        pt = -1
        ci = -1
        ct = -1
        found_correct = False
        found_plausible = False
        total_plau = 0
        for elem in root:
            iter = elem["iteration"]
            time = elem["time"]
            is_pass = elem["pass_result"]
            config = elem["config"][0]
            patch_id = f'{config["id"]}-{config["case_id"]}'
            patch_loc = config["location"]
            if patch_loc in sim:
                patch = sim[patch_loc]
                fail_time = patch["fail_time"]
                pass_time = patch["pass_time"]
                tm = fail_time + pass_time
                global_time += tm
                time = global_time
            else:
                print("NOT IN SIM!!!")
            if patch_id in correct_patches:
                if not found_correct:
                    ci = iter
                    ct = time
                    found_correct = True
            if is_pass:
                total_plau += 1
                if not found_plausible:
                    pi = iter
                    pt = time
                    found_plausible = True
        return pi, pt, ci, ct, total_plau

def main(args: List[str]) -> None:
    if len(args) < 4:
        print("Usage: gen-result-table.py <recoder-path> <outdir> <id>")
        return
    recoder_path = args[1]
    outdir = args[2]
    id = args[3]
    original_tool = "Recoder"
    if len(args) == 5:
        global use_group
        use_group = True
        original_tool = "AlphaRepair"

    if not os.path.exists(outdir):
        print(f"Outdir {outdir} does not exist!")
        return
    correct_patch_dict = get_correct_patch(os.path.join(recoder_path, "data", "correct_patch.csv"))
    bugids = list(correct_patch_dict.keys())
    bugids = sort_bugids(bugids)
    total_seapr = [0, 0]
    t_total_seapr = [0, 0]
    total_recoder = [0, 0]
    t_total_recoder = [0, 0]
    colors=['b','g','y','m','c','k']
    other_result: Dict[str, List[List[int]]] = {
        "SeAPR": [[], []],
        original_tool: [[], []],
    }
    guided_result = [[], []]
    for bugid in bugids:
        original_dir = os.path.join(outdir, f"{bugid}-recoder-{id}")
        if not check_dir(original_dir):
            continue
        basic,plausible=get_patch_iteration(original_dir)
        other_result[original_tool][0] += basic
        other_result[original_tool][1] += plausible
        # result_recoder = analyze_result(recoder_path, bugid, original_dir, correct_patch_dict[bugid])
        seapr_dir = os.path.join(outdir, f"{bugid}-seapr-{id}")
        basic,plausible=get_patch_iteration(seapr_dir)
        other_result["SeAPR"][0] += basic
        other_result["SeAPR"][1] += plausible
        # result_seapr = analyze_result(recoder_path, bugid, seapr_dir, correct_patch_dict[bugid])
        for i in range(50):
            guided_dir = os.path.join(outdir, f"{bugid}-guided-{id}-{i}")
            # tmp_result = analyze_result(recoder_path, bugid, guided_dir, correct_patch_dict[bugid])
            basic,plausible=get_patch_iteration(guided_dir)
            guided_result[0] += basic
            guided_result[1] += plausible

    for name in other_result:
        other_result[name][0].sort()
        other_result[name][1].sort()
    guided_result[0].sort()
    guided_result[1].sort()
    max_iter = guided_result[0][-1]
    for name in other_result:
        if max_iter < other_result[name][0][-1]:
            max_iter = other_result[name][0][-1]
    max_iter = 120
    plt.clf()
    # plt.xlabel('Iteration',fontsize=16)
    # plt.ylabel('Number of basic patches',fontsize=16)
    guided_list = [0]
    for i in range(0,max_iter+1):
        if i in guided_result[0]:
            guided_list.append((guided_list[-1]*50+guided_result[0].count(i))/50)
        else:
            guided_list.append(guided_list[-1])
    plt.plot(list(range(max_iter+2)),guided_list,'r',label='CASINO')
    for name in other_result:
        if name == 'SeAPR':
            continue
        other_list = [0]
        other_list=[0]
        for i in range(1,max_iter+1):
            if i in other_result[name][0]:
                other_list.append(other_list[-1]+other_result[name][0].count(i))
            else:
                other_list.append(other_list[-1])
        plt.plot(list(range(max_iter+1)),other_list,colors[0],label=name)
        colors.pop(0)
    plt.legend(fontsize=16)
    plt.yscale('log',base=10)
    plt.savefig(f'{outdir}/basic-patch-recoder-220827.pdf',bbox_inches='tight')
    
    max_iter = guided_result[1][-1]
    for name in other_result:
        if max_iter < other_result[name][1][-1]:
            max_iter = other_result[name][1][-1]
    max_iter = 60
    plt.clf()
    # plt.xlabel('Iteration',fontsize=16)
    # plt.ylabel('Number of basic patches',fontsize=16)
    guided_list = [0]
    for i in range(0,max_iter+1):
        if i in guided_result[1]:
            guided_list.append((guided_list[-1]*50+guided_result[1].count(i))/50)
        else:
            guided_list.append(guided_list[-1])
    plt.plot(list(range(max_iter+2)),guided_list,color='r',markersize=5, markevery=int(max_iter/30),label='CASINO', marker='s')
    for name in other_result:
        other_list = [0]
        other_list=[0]
        check = False
        if name == "Recoder": #SeAPR
            color = 'b'
            marker = '^'
        else:
            continue
            color = 'g'
            marker = 'o'
            check = True
        for i in range(0,max_iter+1):
            if i in other_result[name][1]:
                other_list.append(other_list[-1]+other_result[name][1].count(i))
            else:
                other_list.append(other_list[-1])
        if check:
            max_plau_total = guided_list[-1]
            max_plau = other_list[-1]
            last_index = max_iter
            if max_plau > max_plau_total:
                print(
                    f"max_plau: {max_plau}, last_index: {last_index}, {max_plau_total}")
                max_plau_total = max_plau
                check = False
            for i in range(len(guided_list)):
                yv = guided_list[i]
                if yv >= max_plau:
                    last_index = i
                    break
            print(f"max_plau: {max_plau}, last_index: {last_index}")
            # if check:
            #     plt.vlines(x=[last_index], colors=['r'], ls='--', lw=2, ymin=0, ymax=max_plau_total)
        plt.plot(list(range(max_iter+2)),other_list,color=color, markersize=5, markevery=int(max_iter/30), label=name, marker=marker)
        colors.pop(0)
    
    if True:
        plt.legend(fontsize=15)
        plt.xlabel('Time (min)',fontsize=15)
        plt.ylabel('# of Plausible Patches',fontsize=15)
        plt.xticks(fontsize=15)
        plt.yticks(fontsize=15)
    else:
        plt.legend(fontsize=20)
        # plt.xscale('log',base=10)
        plt.xticks(fontsize=20)
        plt.yticks(fontsize=20)
        # plt.yscale('log',base=10)
    plt.savefig(f'{outdir}/plausible-patch-{id}.png',bbox_inches='tight')
    plt.savefig(f'{outdir}/plausible-patch-{id}.pdf',bbox_inches='tight')
main(sys.argv)
