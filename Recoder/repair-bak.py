import json
import sys
import os
from Searchnode import Node
from stringfycode import stringfyRoot
import javalang
import subprocess
import time
import signal
import traceback
from typing import Dict, List, Set, Tuple
#lst = ['Chart-1', 'Chart-8', 'Chart-9', 'Chart-11', 'Chart-12', 'Chart-13', 'Chart-20', 'Chart-24', 'Chart-26', 'Closure-1', 'Closure-10', 'Closure-14', 'Closure-15', 'Closure-18', 'Closure-31', 'Closure-33', 'Closure-38', 'Closure-51', 'Closure-62', 'Closure-63', 'Closure-70', 'Closure-73', 'Closure-86', 'Closure-92', 'Closure-93', 'Closure-107', 'Closure-118', 'Closure-113', 'Closure-124', 'Closure-125', 'Closure-129', 'Lang-6', 'Lang-16', 'Lang-26', 'Lang-29', 'Lang-33', 'Lang-38', 'Lang-39', 'Lang-43', 'Lang-45', 'Lang-51', 'Lang-55', 'Lang-57', 'Lang-59', 'Lang-61', 'Math-2', 'Math-5', 'Math-25', 'Math-30', 'Math-33', 'Math-34', 'Math-41', 'Math-57', 'Math-58', 'Math-59', 'Math-69', 'Math-70', 'Math-75', 'Math-80', 'Math-82', 'Math-85', 'Math-94', 'Math-105', 'Time-4', 'Time-15', 'Time-16', 'Time-19', 'Lang-43', 'Math-50', 'Math-98', 'Time-7', 'Mockito-38', 'Mockito-22', 'Mockito-29', 'Mockito-34', 'Closure-104', 'Math-27']
lst = ['Lang-39', 'Lang-63', 'Math-88', 'Math-82', 'Math-20', 'Math-28', 'Math-6', 'Math-72', 'Math-79', 'Math-8', 'Math-98']#['Closure-38', 'Closure-123', 'Closure-124', 'Lang-61', 'Math-3', 'Math-11', 'Math-48', 'Math-53', 'Math-63', 'Math-73', 'Math-101', 'Math-98', 'Lang-16']
def convert_time_to_str(time):
    #时间数字转化成字符串，不够10的前面补个0
    if (time < 10):
        time = '0' + str(time)
    else:
        time=str(time)
    return time

def sec_to_data(y):
    h=int(y//3600 % 24)
    d = int(y // 86400)
    m =int((y % 3600) // 60)
    s = round(y % 60,2)
    h=convert_time_to_str(h)
    m=convert_time_to_str(m)
    s=convert_time_to_str(s)
    d=convert_time_to_str(d)
    # 天 小时 分钟 秒
    return d + ":" + h + ":" + m + ":" + s
def getroottree2(tokens, isex=False):
    root = Node(tokens[0], 0)
    currnode = root
    idx = 1
    for x in tokens[1:]:
        if x != "^":
            nnode = Node(x, idx)
            nnode.father = currnode
            currnode.child.append(nnode)
            currnode = nnode
            idx += 1
        else:
            currnode = currnode.father
    return root

def add_tests(recoder_path: str, outdir: str, bugid: str, switch_info: dict) -> None:
    proj = bugid.split("-")[0]
    bid = bugid.split("-")[1]
    build_dir = os.path.join(recoder_path, "buggy", bugid)
    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(outdir + "/" + bugid, exist_ok=True)
    gen_proj_cmd = f"defects4j checkout -p {proj} -v {bid}b -w {build_dir}"
    print("Generating project directory! " + gen_proj_cmd)
    os.system(gen_proj_cmd)
    tests_all_file = os.path.join(outdir, bugid, "tests.all")
    tests_relevant_file = os.path.join(outdir, bugid, "tests.rel")
    tests_trigger_file = os.path.join(outdir, bugid, "tests.trig")
    gen_test_all_cmd = f"defects4j export -w {build_dir} -o {tests_all_file} -p tests.all"
    os.system(gen_test_all_cmd)
    gen_test_rel_cmd = f"defects4j export -w {build_dir} -o {tests_relevant_file} -p tests.relevant"
    os.system(gen_test_rel_cmd)
    gen_test_trig_cmd = f"defects4j export -w {build_dir} -o {tests_trigger_file} -p tests.trigger"
    os.system(gen_test_trig_cmd)
    # TODO: tests
    failing_test_cases = list()
    failed = dict()
    passing_test_cases = list()
    relevent_test_cases = list()
    with open(tests_trigger_file, "r") as tf:
        for line in tf.readlines():
        #     test = line.split("::")[0]
        #     if test not in failed:
        #         failed[test] = 0
        #     failed[test] += 1
        # for fail in failed:
            failing_test_cases.append(line.strip())
    with open(tests_all_file, "r") as tf:
        for line in tf.readlines():
            test = line.strip()
            passing_test_cases.append(test)
    with open(tests_relevant_file, "r") as tf:
        for line in tf.readlines():
            test = line.strip()
            relevent_test_cases.append(test)
    switch_info["failing_test_cases"] = failing_test_cases
    switch_info["passing_test_cases"] = passing_test_cases
    switch_info["relevant_test_cases"] = relevent_test_cases

def save_code_as_file(outdir: str, bugid: str, patches: dict, func_map: Dict[str, dict]) -> None:
    recoder_path = "."
    if "RECODER_HOME" in os.environ:
        recoder_path = os.environ["RECODER_HOME"]
    switch_info = dict()
    switch_info["project_name"] = bugid
    proj = bugid.split("-")[0]
    bid = bugid.split("-")[1]
    add_tests(recoder_path, outdir, bugid, switch_info)
    rankings = list()
    # fl_scores = list()
    # with open(os.path.join(recoder_path, "location", "ochiai", proj.lower(), bid + ".txt" )) as fl:
    #     for line in fl.readlines():
    #         fl_score = dict()
    #         tokens = fl_score.split(",")
    #         classname, lineid = tokens[0].split("#")
    #         fl_score["file"] = classname
    #         fl_score["line"] = lineid
    #         fl_score["score"] = float(tokens[1])
    #         fl_scores.append(fl_score)
    # switch_info["priority"] = fl_scores
    rules = list()
    file_dict = dict()
    id_dict = dict()
    file_line_id = dict()
    for i, p in enumerate(patches):
        if i < 0:
            continue
        iden = bugid + str(p['line']) + p['filename'].replace("/", "")[::-1]
        id = p["id"]
        if id not in id_dict:
            id_dict[id] = 0
        id_dict[id] += 1
        filename: str = p["filename"]
        fl_score = p["fl_score"]
        if filename.startswith(f"buggy/{bugid}/"):
            filename = filename.replace(f"buggy/{bugid}/", "", 1)
        if filename not in file_dict:
            file_dict[filename] = dict()
        line_dict = file_dict[filename]
        line_num = int(p["line"])
        if line_num not in line_dict:
            line_dict[line_num] = {"line": line_num, "id": id, "fl_score": fl_score, "cases": []}
        file_line = f"{filename}:{line_num}"
        if file_line not in file_line_id:
            file_line_id[file_line] = id
        else:
            if file_line_id[file_line] != id:
                print("Not correct id!!!")
                print(f"{file_line} -> {file_line_id[file_line]} != {id}")
        case_dict = dict()
        case_dict["case"] = id_dict[id]
        save_file = os.path.join(outdir, bugid, str(id), str(id_dict[id]), os.path.basename(filename))
        case_dict["location"] = os.path.join(str(id), str(id_dict[id]), os.path.basename(filename))
        case_dict["prob"] = p["prob"]
        case_dict["edit"] = p["code"]
        case_dict["mode"] = p["mode"]
        case_dict["actlist"] = p["actlist"]
        curride = iden
        # if os.path.exists(save_file):
        #     line_dict[line_num]["cases"].append(case_dict)
        #     continue
        try:
            root = getroottree2(p['code'].split())
        except:
            #assert(0)
            continue
        mode = p['mode']
        precode = p['precode']
        aftercode = p['aftercode']        
        oldcode = p['oldcode']
        if '-1' in oldcode:
            continue
        if mode == 1:
            aftercode = oldcode + aftercode
        lines = aftercode.splitlines()
        if 'throw' in lines[0] and mode == 1:
            for s, l in enumerate(lines):
                if 'throw' in l or l.strip() == "}":
                    precode += l + "\n"
                else:
                    break
            aftercode = "\n".join(lines[s:])
        if lines[0].strip() == '}' and mode == 1:
            precode += lines[0] + "\n"
            aftercode = "\n".join(lines[1:])
        #print(aftercode.splitlines()[:10])

        try:
            code = stringfyRoot(root, False, mode)
        except:
            #print(traceback.print_exc())
            continue
        if '<string>' in code:
            if '\'.\'' in oldcode:
                code = code.replace("<string>", '"."')
            elif '\'-\'' in oldcode:
                code = code.replace("<string>", '"-"')
            elif '\"class\"' in oldcode:
                code = code.replace("<string>", '"class"')
            else:
                code = code.replace("<string>", "\"null\"")
        if len(root.child) > 0 and root.child[0].name == 'condition' and mode == 0:
            code = 'if' + code + "{"
        if code == "" and 'for' in oldcode and mode == 0:
            code = oldcode + "if(0!=1)break;"
        filepath2 = os.path.join(outdir, p["filename"])
        lnum = 0
        for l in code.splitlines():
            if l.strip() != "":
                lnum += 1
            else:
                continue
        if mode == 1 and len(precode.splitlines()) > 0 and 'case' in precode.splitlines()[-1]:
            lines = precode.splitlines()
            for i in range(len(lines) - 2, 0, -1):
                if lines[i].strip() == '}':
                    break
            precode = "\n".join(lines[:i])
            aftercode = "\n".join(lines[i:]) + "\n" + aftercode
        if lnum == 1 and 'if' in code and mode == 1:
            if p['isa']:
                code = code.replace("if", 'while')
            #print('ppp', precode.splitlines()[-1])
            if len(precode.splitlines()) > 0 and 'for' in precode.splitlines()[-1]:
                code = code + 'continue;\n}\n'    
            else:
                afterlines = aftercode.splitlines()
                lnum = 0
                rnum = 0
                ps = p
                for p, y in enumerate(afterlines):
                    if ps['isa'] and y.strip() != '':
                        aftercode = "\n".join(afterlines[:p + 1] + ['}'] + afterlines[p + 1:])
                        break
                    if '{' in y:
                        lnum += 1
                    if '}' in y:
                        if lnum == 0:
                            aftercode = "\n".join(afterlines[:p] + ['}'] + afterlines[p:])
                            #assert(0)
                            break
                        lnum -= 1
            print(code)
            tmpcode = precode + "\n" + code + aftercode
            tokens = javalang.tokenizer.tokenize(tmpcode)
            parser = javalang.parser.Parser(tokens)
        else:
            print(code)
            tmpcode = precode + "\n" + code + aftercode
            tokens = javalang.tokenizer.tokenize(tmpcode)
            parser = javalang.parser.Parser(tokens)
        try:
            tree = parser.parse()
        except:
            #assert(0)
            #print(code)
            #assert(0)
            #print('ttttt')
            continue
        # print(filepath2)
        # open(filepath2, "w").write(tmpcode)
        case_dict["code"] = code
        case_dict["oldcode"] = oldcode
        line_dict[line_num]["cases"].append(case_dict)
        rankings.append(f"{id}-{case_dict['case']}")
        os.makedirs(os.path.dirname(save_file), exist_ok=True)
        with open(save_file, "w") as sf:
            sf.write(tmpcode)
    switch_info_file = os.path.join(outdir, bugid, "switch-info.json")
    file_list = list()
    for file in file_dict:
        line_list = list()
        line_dict = file_dict[file]
        file_list.append({"file": file, "lines": line_list})
        for line in line_dict:
            line_list.append(line_dict[line])
    switch_info["rules"] = file_list
    switch_info["ranking"] = rankings
    func_locations = list()
    for file in func_map:
        func_filter = dict()
        tmp_file_level = dict()
        tmp_file_level["file"] = file
        functions = list()
        tmp_file_level["functions"] = functions
        for func in func_map[file]:
            func_id = f"{func['function']}:{func['begin']}-{func['end']}"
            if func_id not in func_filter:
                func_filter[func_id] = func
                functions.append(func)
        func_locations.append(tmp_file_level)
    switch_info["func_locations"] = func_locations
    with open(switch_info_file, "w") as sif:
        json.dump(switch_info, sif, indent=2)
    

def main(bugid: str) -> None:
    lst = [bugid]
    starttime = time.time()
    timelst = []
    for x in lst:
        if x != bugid:
            continue
        wf = open('patches/' + x + "patch.txt", 'w')
        patches = json.load(open("patch/%s.json"%x, 'r'))
        curride = ""
        proj = x.split("-")[0]
        bid = x.split("-")[1]
        x = x.replace("-", "")
        if os.path.exists('buggy%s' % x):
            os.system('rm -rf buggy%s' % x)
        os.system("defects4j checkout -p %s -v %s -w buggy%s" % (proj, bid + 'b', x))
        xsss = x
        testmethods = os.popen('defects4j export -w buggy%s -p tests.trigger'%x).readlines()
        for i, p in enumerate(patches):
            if i < 0:
                continue
            endtime = time.time()
            if endtime - starttime > 18000:
                open('timeg.txt', 'a').write(xsss + "\t" + sec_to_data(endtime - starttime) + "\n")
                exit(0)
            iden = x + str(p['line']) + p['filename'].replace("/", "")[::-1]
            if iden != curride:
                if curride != "":
                    os.system('rm -rf buggy%s'%x)
            os.system('defects4j checkout -p %s -v %s -w buggy%s' % (proj, bid + 'b', x))
            curride = iden
            try:
                root = getroottree2(p['code'].split())
            except:
                #assert(0)
                continue
            mode = p['mode']
            precode = p['precode']
            aftercode = p['aftercode']        
            oldcode = p['oldcode']
            if '-1' in oldcode:
                continue
            if mode == 1:
                aftercode = oldcode + aftercode
            lines = aftercode.splitlines()
            if 'throw' in lines[0] and mode == 1:
                for s, l in enumerate(lines):
                    if 'throw' in l or l.strip() == "}":
                        precode += l + "\n"
                    else:
                        break
                aftercode = "\n".join(lines[s:])
            if lines[0].strip() == '}' and mode == 1:
                precode += lines[0] + "\n"
                aftercode = "\n".join(lines[1:])
            #print(aftercode.splitlines()[:10])

            try:
                code = stringfyRoot(root, False, mode)
            except:
                #print(traceback.print_exc())
                continue
            if '<string>' in code:
                if '\'.\'' in oldcode:
                    code = code.replace("<string>", '"."')
                elif '\'-\'' in oldcode:
                    code = code.replace("<string>", '"-"')
                elif '\"class\"' in oldcode:
                    code = code.replace("<string>", '"class"')
                else:
                    code = code.replace("<string>", "\"null\"")
            if len(root.child) > 0 and root.child[0].name == 'condition' and mode == 0:
                code = 'if' + code + "{"
            if code == "" and 'for' in oldcode and mode == 0:
                code = oldcode + "if(0!=1)break;"
            filepath2 = 'buggy%s'%x + p['filename'][5:]
            lnum = 0
            for l in code.splitlines():
                if l.strip() != "":
                    lnum += 1
                else:
                    continue
            if mode == 1 and len(precode.splitlines()) > 0 and 'case' in precode.splitlines()[-1]:
                lines = precode.splitlines()
                for i in range(len(lines) - 2, 0, -1):
                    if lines[i].strip() == '}':
                        break
                precode = "\n".join(lines[:i])
                aftercode = "\n".join(lines[i:]) + "\n" + aftercode
            if lnum == 1 and 'if' in code and mode == 1:
                if p['isa']:
                    code = code.replace("if", 'while')
                #print('ppp', precode.splitlines()[-1])
                if len(precode.splitlines()) > 0 and 'for' in precode.splitlines()[-1]:
                    code = code + 'continue;\n}\n'    
                else:
                    afterlines = aftercode.splitlines()
                    lnum = 0
                    rnum = 0
                    ps = p
                    for p, y in enumerate(afterlines):
                        if ps['isa'] and y.strip() != '':
                            aftercode = "\n".join(afterlines[:p + 1] + ['}'] + afterlines[p + 1:])
                            break
                        if '{' in y:
                            lnum += 1
                        if '}' in y:
                            if lnum == 0:
                                aftercode = "\n".join(afterlines[:p] + ['}'] + afterlines[p:])
                                #assert(0)
                                break
                            lnum -= 1
                print(code)
                tmpcode = precode + "\n" + code + aftercode
                tokens = javalang.tokenizer.tokenize(tmpcode)
                parser = javalang.parser.Parser(tokens)
            else:
                print(code)
                tmpcode = precode + "\n" + code + aftercode
                tokens = javalang.tokenizer.tokenize(tmpcode)
                parser = javalang.parser.Parser(tokens)
            try:
                tree = parser.parse()
            except:
                #assert(0)
                #print(code)
                #assert(0)
                #print('ttttt')
                continue
            print(filepath2)
            open(filepath2, "w").write(tmpcode)
            bugg = False
            for t in testmethods:
                #print(t.strip())
                cmd = 'defects4j test -w buggy%s/ -t %s' % (x, t.strip())
                Returncode = ""
                child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1, start_new_session=True)
                while_begin = time.time() 
                while True:                
                    Flag = child.poll()
                    #print(Flag)
                    #print(time.time() - while_begin)
                    if  Flag == 0:
                        Returncode = child.stdout.readlines()#child.stdout.read()
                        break
                    elif Flag != 0 and Flag is not None:
                        bugg = True
                        break
                    elif time.time() - while_begin > 15:
                        print('ppp')
                        os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                        bugg = True
                        break
                    else:
                        time.sleep(1)
                log = Returncode
                if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
                    continue
                else:
                    #print(len(log), log[-1].decode('utf-8'))
                    bugg = True
                    break
            if not bugg:
                print('s')
                cmd = 'defects4j test -w buggy%s/' % (x)
                Returncode = ""
                child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1, start_new_session=True)
                while_begin = time.time() 
                while True:                
                    Flag = child.poll()
                    #print(time.time() - while_begin, Flag)
                    if  Flag == 0:
                        Returncode = child.stdout.readlines()#child.stdout.read()
                        break
                    elif Flag != 0 and Flag is not None:
                        bugg = True
                        break
                    elif time.time() - while_begin > 180:
                        os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                        bugg = True
                        break
                    else:
                        time.sleep(1)
                log = Returncode
                print(log)
                if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
                    print('success')
                    endtime = time.time()
                    open('timeg.txt', 'a').write(xsss + "\t" + sec_to_data(endtime - starttime) + "\n")
                    #timelst.append(sec_to_data(endtime - starttime))
                    wf.write(curride + "\n")
                    wf.write("-" + oldcode + "\n")
                    wf.write("+" +  code + "\n")
                    wf.write("🚀\n")
                    wf.flush()    
                    if os.path.exists('buggy%s' % x):
                        os.system('rm -rf buggy%s' % x)
                    exit(0)

        endtime = time.time()

if __name__ == "__main__":
    # main(sys.argv[1])
    ls = [sys.argv[1]]
    for bugid in ls:
        patches = json.load(open(f"d4j/{bugid}/{bugid}.json", 'r'))
        func_loc = json.load(open(f"d4j/{bugid}/func_loc.json"))
        save_code_as_file("d4j", bugid, patches, func_loc)