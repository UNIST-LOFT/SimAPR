
import getopt
import json
from os import chdir, getcwd, mkdir, path
import subprocess
from sys import argv
from typing import List


class Config:
    """
        Data class for patch configuration.
    """
    def __init__(self,switch,case,operator=-1,variable=-1,constant=-1) -> None:
        self.switch = switch
        self.case = case
        self.operator = operator
        self.variable = variable
        self.constant = constant
    
    def __str__(self) -> str:
        result=f'{self.switch}-{self.case}'
        if self.operator != -1:
            result += f'-{self.operator}'
        if self.variable != -1:
            result += f'-{self.variable}-{self.constant}'
        return result

class SwitchInfo:
    """
        Data class for switch information.
        Includes switch number, patch appearance, file, begin/end line/column.
    """
    def __init__(self, switch_num:int,patches:List[str],file_name:str,begin_line:int,end_line:int,begin_column:int,end_column:int) -> None:
        self.switch_num = switch_num
        self.patches = patches
        self.file_name = file_name
        self.begin_line = begin_line
        self.end_line = end_line
        self.begin_column = begin_column
        self.end_column = end_column

def insert_patch(original_file:str,backup_file:str,begin_line:int,begin_column:int,end_line:int,end_column:int,patch:str):
    """
        Insert a patch string into actual source file, and generate patched file.
        original_file: original source file
        backup file: backup file name read from __backup.log
        patch: patch string read from switch-info.json
    """
    # line informations may have function declaration for patch generation
    begin_line-=2
    end_line-=2
    with open(backup_file,'r') as file:
        lines=file.readlines()

        previous_lines=[]
        post_lines:List[str]=[]
        for i,line in enumerate(lines):
            if i<=begin_line:
                previous_lines.append(line)
            if i>=end_line:
                post_lines.append(line)

        first_line:str=previous_lines[-1]
        last_line=post_lines[0]
        previous_first_line=first_line[:begin_column-1]
        if previous_first_line[-1].isalpha():
            previous_first_line=first_line[:begin_column+1]
        last_first_line:str=last_line[end_column+1:]
        if (previous_first_line[-5:]=='else ' or previous_first_line[-4:]=='else') and last_first_line[:2]=='if':
            previous_first_line += '{ '
            # TODO: Find finish of next if and add }
            breacket_counter=0
            is_finish_then=False
            is_finish_else=False
            is_finish=False
            has_else=False
            else_counter=0
            for i,c in enumerate(last_first_line):
                if c=='{':
                    # Next IfStmt has CompoundStmt and it's start of it
                    breacket_counter+=1
                elif not c.isspace() and is_finish_then and not has_else and breacket_counter==0:
                    # then finish, no else
                    is_finish=True
                    last_first_line=last_first_line[:i+1]+'}\n'+last_first_line[i+1:]
                    break
                elif c==';' and breacket_counter==0:
                    # Next IfStmt has other statement for then branch
                    is_finish_then=True
                elif c=='}':
                    breacket_counter-=1
                    if has_else and breacket_counter==0:
                        # else finish
                        is_finish_else=True
                        is_finish=True
                        last_first_line=last_first_line[:i+1]+'}'+last_first_line[i+1:]
                        break
                    elif breacket_counter==0:
                        is_finish_then=True

                elif c=='e' and not has_else and is_finish_then:
                    else_counter+=1
                elif c=='l' and else_counter==1:
                    else_counter+=1
                elif c=='s' and else_counter==2:
                    else_counter+=1
                elif c=='e' and else_counter==3:
                    has_else=True
            
            if not is_finish:
                for i,line in enumerate(post_lines[1:]):
                    for j,c in enumerate(line):
                        if c=='{':
                            # Next IfStmt has CompoundStmt and it's start of it
                            breacket_counter+=1
                        elif not c.isspace() and is_finish_then and not has_else and breacket_counter==0:
                            # then finish, no else
                            is_finish=True
                            post_lines[i+1]=line[:j]+'}'+line[j:]
                            break
                        elif c==';' and breacket_counter==0:
                            # Next IfStmt has other statement for then branch
                            is_finish_then=True
                        elif c=='}':
                            breacket_counter-=1
                            if has_else and breacket_counter==0:
                                # else finish
                                is_finish_else=True
                                is_finish=True
                                post_lines[i+1]=line[:j]+'}'+line[j:]
                                break
                            elif breacket_counter==0:
                                is_finish_then=True
                        elif c=='e' and not has_else and is_finish_then:
                            else_counter+=1
                        elif c=='l' and else_counter==1:
                            else_counter+=1
                        elif c=='s' and else_counter==2:
                            else_counter+=1
                        elif c=='e' and else_counter==3:
                            has_else=True
                    if is_finish:
                        break

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
    """
        Replace abstract condition with actual condition.
        If abstract condition not found(a.k.a. normal patch), do nothing.
    """
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
        
        end_abst_cond+=1
        params_str=patch[start_param:end_abst_cond]
        params=params_str.split(',')[3:]

        if config.operator==4:
            actual_condition='1'
        elif 0<=config.operator<=3:
            var=params[config.variable*2][3:-1]
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
        return patch.replace(abst_condition,'('+actual_condition+')')
    else:
        return patch

def generate_diff(original_file:str,backup_file:str,src_path:str,config:Config,output_dir:str='patch'):
    if not path.isdir(output_dir):
        mkdir(output_dir)
    
    output_file=open(f'{output_dir}/{config}.patch','w')
    subprocess.run(['diff','-uNr',backup_file,'patched_'+original_file],stdout=output_file)
    output_file.close()

    patch_file=open(f'{output_dir}/{config}.patch','r')
    patch_lines=patch_file.readlines()
    patch_file.close()

    for i,line in enumerate(patch_lines):
        if line[:3]=='+++':
            begin_loc=4
            end_loc=line.find('.c')+2
            old_str=line[begin_loc:end_loc]
            new_str=line.replace(old_str,src_path)
            patch_lines[i]=new_str
    
    with open(f'{output_dir}/{config}.patch','w') as file:
        for line in patch_lines:
            file.write(line)

if __name__=='__main__':
    opts, args = getopt.getopt(argv[1:], "ghc:i:o:")
    gen_diff=False
    config_str=None
    input_file=None
    output_file='patch'
    for o, a in opts:
        if o == "-g":
            gen_diff=True
        elif o == "-c":
            config_str=a
        elif o=='-i':
            input_file=a
        elif o=='-o':
            output_file=a
        elif o == '-h':
            print(f"""Usage: python diff_gen.py [options] <work_dir>

Generate patched source file with patch configuration. Generated source file will be 'patched_<file>'.
<work_dir>: work directory of program.
If -c option is specified, generate diff file with specified patch configuration. Otherwise, generate diff files of all plausible patches.
One of -c or -i option should be specified.

Options:
    -g: generate diff file.
    -h: show help.
    -c <config_str>: specify patch configuration. <config_str>: <switch>-<case>[-<operator>[-<variable>-<constant>]].
    -i <search_result_file>: result file of MSV-search.
    -o <output_file>: output directory of diff files. """)
            exit(0)

    if config_str is None and input_file is None:
        print('Patch configuration or result file of MSV-search is required.')
        exit(1)

    work_dir=args[0]
    config=[]
    if config_str is not None:
        config_strs=config_str.split('-')
        if len(config_strs)==2:
            config.append(Config(int(config_strs[0]),int(config_strs[1])))
        elif len(config_strs)==3:
            config.append(Config(int(config_strs[0]),int(config_strs[1]),int(config_strs[2])))
        else:
            config.append(Config(int(config_strs[0]),int(config_strs[1]),int(config_strs[2]),int(config_strs[3]),int(config_strs[4])))
    else:
        result_file=open(input_file+'/msv-result.json','r')
        result_root=json.load(result_file)
        result_file.close()

        for result in result_root:
            if result['pass_result']:
                cur_config=result['config'][0]
                switch=cur_config['switch']
                case=cur_config['case']
                if cur_config['is_cond']:
                    if cur_config['operator']==4:
                        config_obj=Config(switch,case,4)
                    else:
                        config_obj=Config(switch,case,cur_config['operator'],cur_config['variable'],cur_config['constant'])
                else:
                    config_obj=Config(switch,case)

                config.append(config_obj)
    
    orig_dir=getcwd()
    chdir(work_dir)

    info_file=open('switch-info.json','r')
    info=json.load(info_file)
    info_file.close()

    switch_list:List[SwitchInfo]=[]
    files=info['rules']
    for file in files:
        for line in file['lines']:
            for switch in line['switches']:
                new_switch=SwitchInfo(switch['switch'],switch['patch_codes'],file['file_name'],switch['begin_line'],switch['end_line'],switch['begin_column'],switch['end_column'])
                switch_list.append(new_switch)
    

    for conf in config:
        for switch in switch_list:
            if switch.switch_num==conf.switch:
                current_switch=switch

        file_name=current_switch.file_name.split('/')[-1]
        backup_log_file='__backup.log'
        with open(backup_log_file,'r') as file:
            backuped_file=file.readlines()
        for i,file in enumerate(backuped_file):
            if file.strip()==current_switch.file_name:
                backup_index=i
                break
        fixed_file='fixed_'+file_name
        original_file=f'__backup{backup_index}'

        patch=current_switch.patches[conf.case-1]
        if patch[-1]!=';' and patch[-1]!='}' and patch[-1]!='\n':
            patch+=';'
        patch=replace_actual_condition(conf,patch)
        print(f'patch:\n{patch}')
        patched_file=insert_patch(file_name,original_file,current_switch.begin_line,current_switch.begin_column,current_switch.end_line,current_switch.end_column,patch)

        if gen_diff:
            generate_diff(file_name,original_file,current_switch.file_name,conf,output_file)

    chdir(orig_dir)