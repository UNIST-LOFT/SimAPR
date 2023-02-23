import subprocess
import getopt


def execute_cmd(cmd: list) -> int:
    print(" ".join(cmd))
    result = subprocess.run(cmd)
    return result.returncode

def main(argv):
    opts,args=getopt.getopt(argv,"",['finish-correct-patch','timeout=','max-iter='])
    if len(args)<5:
        print("Usage: python3 casino-reproduce.py [options] <project> <output_dir> <casino|original|seapr> <tool> <project_path> [seed]")
        exit(1)
    
    finish_correct_patch=False
    timeout=0
    max_iter=0
    for a,o in opts:
        if a=='--finish-correct-patch':
            finish_correct_patch=True
        elif a=='--timeout':
            timeout=int(o)
        elif a=='--max-iter':
            max_iter=int(o)

    project=args[0]
    if "-" in project:
        proj, bid = project.split("-")
    else:
        proj, bid = project.split("_")
    output_dir=args[1]
    mode=args[2]
    tool=args[3]
    project_path=args[4]
    seed=-1
    if len(args)>5:
        seed=int(args[5])

    correct_dict=dict()
    with open(f'correct-{tool}.csv') as f:
        lines=f.readlines()
        for line in lines:
            line=line.strip()
            elem=line.split(',')

            cor_str=''
            for e in elem[1:]:
                cor_str+=e+','
            cor_str=cor_str[:-1]
            correct_dict[elem[0]]=cor_str

    default_opts = ["python3", "../casino.py", "--use-exp-alpha", "-t", "180000", "--use-pass-test", "--seed", str(seed)]
    if timeout > 0:
        default_opts.extend(["-T", str(timeout)])
    if max_iter > 0:
        default_opts.extend(["-E", str(max_iter)])
    if mode=='casino':
        if tool=='avatar' or tool=='fixminer' or tool=='kpar' or tool=='tbar':
            project = f"{proj}_{bid}"
            cmd= default_opts + ["-o", output_dir, "-m", "guided", "--tbar-mode",
                    '-w',f'{tool}/d4j/{project}/0' if tool=='fixminer' else f'{tool}/d4j/{project}']
            if project in correct_dict:
                cmd.append('-c')
                cmd.append(correct_dict[project])
            if tool=='fixminer':
                cmd.append('--fixminer-mode')
            if finish_correct_patch:
                cmd.append('--finish-correct-patch')
            execute_cmd(cmd+['--','python3','../script/d4j_run_test.py',project_path])
        else: # recoder, alpharepair
            project = f"{proj}-{bid}"
            cmd = default_opts + ["-o", output_dir, "-m", "guided", "--recoder-mode",
                    '-w',f'{tool}/d4j/{project}']
            if project in correct_dict:
                cmd.append('-c')
                cmd.append(correct_dict[project])
            if finish_correct_patch:
                cmd.append('--finish-correct-patch')
            execute_cmd(cmd+['--','python3','../script/d4j_run_test.py',project_path])
            
    elif mode=='original':
        if tool=='avatar' or tool=='fixminer' or tool=='kpar' or tool=='tbar':
            project = f"{proj}_{bid}"
            cmd = default_opts + ["-o", output_dir, "-m", "tbar", "--tbar-mode",
                    '-w',f'{tool}/d4j/{project}/0' if tool=='fixminer' else f'{tool}/d4j/{project}']
            if project in correct_dict:
                cmd.append('-c')
                cmd.append(correct_dict[project])
            if tool=='fixminer':
                cmd.append('--fixminer-mode')
            if finish_correct_patch:
                cmd.append('--finish-correct-patch')
            execute_cmd(cmd+['--','python3','../script/d4j_run_test.py',project_path])
        else: # recoder, alpharepair
            project = f"{proj}-{bid}"
            cmd = default_opts + ["-o", output_dir, "-m", "recoder", "--recoder-mode",
                    '-w',f'{tool}/d4j/{project}']
            if project in correct_dict:
                cmd.append('-c')
                cmd.append(correct_dict[project])
            if finish_correct_patch:
                cmd.append('--finish-correct-patch')
            execute_cmd(cmd+['--','python3','../script/d4j_run_test.py',project_path])
            
    elif mode=='seapr':
        if tool=='avatar' or tool=='fixminer' or tool=='kpar' or tool=='tbar':
            project = f"{proj}_{bid}"
            cmd = default_opts + ["-o", output_dir, "-m", "seapr", "--tbar-mode", "--ignore-compile-error", "--use-pattern",
                    '-w',f'{tool}/d4j/{project}/0' if tool=='fixminer' else f'{tool}/d4j/{project}']
            if project in correct_dict:
                cmd.append('-c')
                cmd.append(correct_dict[project])
            if tool=='fixminer':
                cmd.append('--fixminer-mode')
            if finish_correct_patch:
                cmd.append('--finish-correct-patch')
            execute_cmd(cmd+['--','python3','../script/d4j_run_test.py',project_path])
        else: # recoder, alpharepair
            project = f"{proj}-{bid}"
            cmd = default_opts + ["-o", output_dir, "-m", "seapr", "--recoder-mode", 
                                  "--ignore-compile-error", '-w',f'{tool}/d4j/{project}']
            execute_cmd(cmd+['--','python3','../script/d4j_run_test.py',project_path])