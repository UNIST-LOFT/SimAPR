
import getopt
import json
from os import chdir, getcwd
from sys import argv


class Config:
    def __init__(self,switch,case,operator=-1,variable=-1,constant=-1) -> None:
        self.switch = switch
        self.case = case
        self.operator = operator
        self.variable = variable
        self.constant = constant

def insert_patch(original_file:str,backup_file:str,begin_line:int,begin_column:int,end_line:int,end_column:int,patch:str):
    # line informations may have function declaration for patch generation
    begin_line-=2
    end_line-=2
    with open(backup_file,'r') as file:
        lines=file.readlines()

        previous_lines=[]
        post_lines=[]
        for i,line in enumerate(lines):
            if i<=begin_line:
                previous_lines.append(line)
            if i>=end_line:
                post_lines.append(line)

        first_line:str=previous_lines[-1]
        last_line=post_lines[0]
        previous_first_line=first_line[:begin_column-1]
        last_first_line=last_line[end_column+1:]
        patch_lines=patch.splitlines()
        # Remove comment
        while patch_lines.count('')>0:
            patch_lines.remove('')
        while patch_lines.count('\t')>0:
            patch_lines.remove('\t')

        patch_first_line=previous_first_line+ patch_lines[0]
        if len(patch_lines)>1:
            patch_last_line=patch_lines[-1] + last_first_line
        else:
            patch_last_line=last_first_line

        del previous_lines[-1]
        del post_lines[0]
        actual_lines=previous_lines+[patch_first_line]+patch_lines[1:-1]+[patch_last_line]+post_lines
        with open('patched_'+original_file,'w') as file:
            for line in actual_lines:
                if line[-1]!='\n':
                    file.write(line+"\n")
                else:
                    file.write(line)

        return 'patched_'+original_file

def replace_actual_condition(config:Config,patch:str):
    if patch.find('__is_neg')!=-1:
        start_abst_cond=patch.find('__is_neg')
        end_abst_cond=-1
        is_start=False
        counter=0
        for i,char in enumerate(patch):
            if i<start_abst_cond:
                continue
            if char=='(':
                counter+=1
                if not is_start:
                    start_param=i
                    is_start=True
            elif char==')':
                counter-=1
            if counter==0 and is_start:
                end_abst_cond=i
                break
        
        params_str=patch[start_param:end_abst_cond]
        params=params_str.split(',')[3:]

        if config.operator==4:
            actual_condition='1'
        elif 0<=config.operator<=3:
            var=params[config.variable*2][2:-1]
            if config.operator==0:
                oper='=='
            elif config.operator==1:
                oper='!='
            elif config.operator==2:
                oper='>'
            else:
                oper='<'
            actual_condition=var+' '+oper+' '+str(config.constant)
        else:
            var=params[config.variable*2][2:-1]
            var2=params[config.constant*2][2:-1]
            if config.operator==0:
                oper='=='
            elif config.operator==1:
                oper='!='
            elif config.operator==2:
                oper='>'
            else:
                oper='<'
            actual_condition=var+' '+oper+' '+var2
        
        abst_condition=patch[start_abst_cond:end_abst_cond]
        return patch.replace(abst_condition,actual_condition)
    else:
        return patch

if __name__=='__main__':
    opts, args = getopt.getopt(argv[1 :], "gh")
    gen_diff=False
    for o, a in opts:
        if o == "-g":
            gen_diff=True
        elif o == '-h':
            print(f"""Usage: python diff_gen.py [options] <work_dir> <config_str>

Generate patched source file with patch configuration. Generated source file will be 'patched_<file>'.
<work_dir>: work directory of program.
<config_str>: <switch>-<case>[-<operator>[-<variable>-<constant>]].

Options:
    -g: generate diff file.
    -h: show help. """)
            exit(0)

    work_dir=args[0]
    config_str=args[1].split('-')

    if len(config_str)==2:
        config=Config(int(config_str[0]),int(config_str[1]))
    elif len(config_str)==3:
        config=Config(int(config_str[0]),int(config_str[1]),int(config_str[2]))
    else:
        config=Config(int(config_str[0]),int(config_str[1]),int(config_str[2]),int(config_str[3]),int(config_str[4]))
    
    orig_dir=getcwd()
    chdir(work_dir)

    info_file=open('switch-info.json','r')
    info=json.load(info_file)
    info_file.close()

    files=info['rules']
    is_end=False
    for file in files:
        if is_end:
            break
        for line in file['lines']:
            if is_end:
                break
            for switch in line['switches']:
                if is_end:
                    break
                elif switch['switch']!=config.switch:
                    continue
                else:
                    begin_line=switch['begin_line']
                    begin_column=switch['begin_column']
                    end_line=switch['end_line']
                    end_column=switch['end_column']
                    src_file=file['file_name']
                    patch_codes=switch['patch_codes']
                    is_end=True

    file_name=src_file.split('/')[-1]
    backup_log_file='__backup.log'
    with open(backup_log_file,'r') as file:
        backuped_file=file.readlines()
    for i,file in enumerate(backuped_file):
        if file.strip()==src_file:
            backup_index=i
            break
    fixed_file='fixed_'+file_name
    original_file=f'__backup{backup_index}'

    patch=patch_codes[config.case-1]
    if patch[-1]!=';' and patch[-1]!='}' and patch[-1]!='\n':
        patch+=';'
    patch=replace_actual_condition(config,patch)
    print(f'patch:\n{patch}')
    patched_file=insert_patch(file_name,original_file,begin_line,begin_column,end_line,end_column,patch)

    chdir(orig_dir)