import os
import re
import signal
import subprocess
import time
from typing import Any, Dict
import javalang

# Basic generate and valdiate class
class GVpatches(object):

    def __init__(self, bug_id, testmethods, logger, patch_pool_folder="patches-pool", skip_validation=False):
        self.bug_id = bug_id
        self.pre_codes = []
        self.fault_lines = []
        self.l_changes = []
        self.post_codes = []
        self.files = []
        self.line_numbers = []
        self.num_of_patches = 1
        self.testmethods = testmethods
        self.logger = logger
        self.patch_pool_folder = patch_pool_folder
        self.skip_validation = skip_validation
        self.generation_time = 0
        self.location_ids = list()
        self.locations = dict()

    def add_new_patch_generation(self, pre_code, fault_line, changes, post_code, file, line_number, n_time, original_file, fl_score, loc_id):
        self.pre_codes.append(pre_code)
        self.fault_lines.append(fault_line)
        self.l_changes.append(changes)
        self.post_codes.append(post_code)
        self.files.append(file)
        self.line_numbers.append(line_number)
        self.generation_time += n_time
        self.location_ids.append(loc_id)
        if loc_id not in self.locations:
            self.locations[loc_id] = { "line": (line_number+1), "id": loc_id, "fl_score": fl_score, "file": original_file, "oldcode": fault_line, "cases": [] }

    def checkout_d4j_project(self):
        subprocess.run('rm -rf ' + '/tmp/' + self.bug_id, shell=True)
        subprocess.run("defects4j checkout -p %s -v %s -w %s" % (self.bug_id.split('_')[0],
                                                                 self.bug_id.split('_')[1] + 'b',
                                                                 ('/tmp/' + self.bug_id)),
                       shell=True)

    def write_changes_to_file(self, change, index):
        with open(self.files[index], 'w', encoding='utf-8') as f:
            for line in self.pre_codes[index]:
                f.write(line)
            f.write(change + '\n')
            for line in self.post_codes[index]:
                f.write(line)
        subprocess.run("touch -r " + self.files[index] + " -d '1 day' " + self.files[index],
                       shell=True)  # this to force recompilation

    def syntax_check(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            tmpcode = f.read()
            try:
                tokens = javalang.tokenizer.tokenize(tmpcode)
                parser = javalang.parser.Parser(tokens)
                parser.parse()
            except:
                return False
        return True
    
    def save_patch_to_file(self, change, index, pardir, filename) -> bool:
        full_path = os.path.join(pardir, filename)
        os.makedirs(pardir, exist_ok=True)
        with open(full_path, "w", encoding='utf-8') as f:
            for line in self.pre_codes[index]:
                f.write(line)
            f.write(change + '\n')
            for line in self.post_codes[index]:
                f.write(line)
        return self.syntax_check(full_path)

    def run_d4j_test(self, prob, index):

        bugg = False
        compile_fail = False
        timed_out = False
        entire_bugg = False
        error_string = ""

        with open(self.files[index], 'r', encoding='utf-8') as f:
            tmpcode = f.read()
            try:
                tokens = javalang.tokenizer.tokenize(tmpcode)
                parser = javalang.parser.Parser(tokens)
                parser.parse()
            except:
                self.logger.logo(prob)
                self.logger.logo("Syntax Error")
                return

        for t in self.testmethods:
            cmd = 'defects4j test -w %s/ -t %s' % (('/tmp/' + self.bug_id), t.strip())
            Returncode = ""
            error_file = open("stderr.txt", "wb")
            child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=error_file, bufsize=-1,
                                     start_new_session=True)
            while_begin = time.time()
            while True:
                Flag = child.poll()
                if Flag == 0:
                    Returncode = child.stdout.readlines()  # child.stdout.read()
                    print(b"".join(Returncode).decode('utf-8'))
                    error_file.close()
                    break
                elif Flag != 0 and Flag is not None:
                    compile_fail = True
                    error_file.close()
                    with open("stderr.txt", "rb") as f:
                        r = f.readlines()
                    for line in r:
                        if re.search(':\serror:\s', line.decode('utf-8')):
                            error_string = line.decode('utf-8')
                            break
                    print(error_string)
                    break
                elif time.time() - while_begin > 15:
                    error_file.close()
                    print('ppp')
                    os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                    timed_out = True
                    break
                else:
                    time.sleep(1)
            log = Returncode
            if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
                continue
            else:
                print("Failure Output")
                bugg = True
                break

        # Then we check if it passes all the tests, include the previously okay tests
        if not bugg:
            print('So you pass the basic tests, Check if it passes all the test, include the previously passing tests')
            cmd = 'defects4j test -w %s/' % ('/tmp/' + self.bug_id)
            Returncode = ""
            child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1,
                                     start_new_session=True)
            while_begin = time.time()
            while True:
                Flag = child.poll()
                # print(time.time() - while_begin, Flag)
                if Flag == 0:
                    Returncode = child.stdout.readlines()  # child.stdout.read()
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
            else:
                entire_bugg = True

        self.logger.logo(prob)
        if compile_fail:
            self.logger.logo("Compiled Error:")
            self.logger.logo(error_string)
            self.logger.logo("Compilation Failed")
        elif timed_out:
            self.logger.logo("Timed Out")
        elif bugg:
            self.logger.logo("Failed Testcase")
        elif entire_bugg:
            self.logger.logo("Failed Original Testcase")
        else:
            self.logger.logo("Success (Plausible Patch)")

    def validate(self, info:Dict[str,Any],func_info:Dict[str,dict]):
        start_time = time.time()
        print("----------------- BEGIN VALIDATION OF PATCHES -----------------")
        rules = list()
        file_map = dict()
        patch_ranking = list()
        case_id = 0
        for index in range(len(self.l_changes)):
            self.logger.logo("Validating Patches for file: {} {}".format(self.files[index], self.line_numbers[index]))
            # self.checkout_d4j_project()
            loc_id = self.location_ids[index]
            loc_info = self.locations[loc_id]
            file_name = loc_info["file"]
            if file_name not in file_map:
                file_map[file_name] = dict()
            
            # Find function from file_map
            func_info_map=file_map[file_name]
            for file in func_info:
                if file['file']==file_name:
                    cur_funcs=file['functions']
                    break

            cur_func=None
            for func in cur_funcs:
                if func['begin']<=loc_info['line']<=func['end']:
                    cur_func=func
                    break

            if cur_func is None:
                cur_func={
                    "function":f"no_function:{loc_info['line']}-{loc_info['line']}",
                    "begin":loc_info['line'],
                    "end":loc_info['line']
                }
                cur_funcs.append(cur_func)

            if cur_func['function'] not in func_info_map:
                temp_func_info={
                    "function":cur_func['function'],
                    "lines":[]
                }
                func_info_map[cur_func['function']]=temp_func_info

            cur_func_info=func_info_map[cur_func['function']]
            cur_func_info['lines'].append(loc_info)
            case_list: list = loc_info["cases"]
            
            for change, prob, masked_line in self.l_changes[index]:
                # self.write_changes_to_file(change, index)
                self.logger.logo("----------------------------------------")
                self.logger.logo("Patch Number :{}".format(self.num_of_patches))
                self.logger.logo('- ' + self.fault_lines[index].strip())
                self.logger.logo('+ ' + change.strip())
                self.logger.logo('mask:' + masked_line.strip())
                if not self.skip_validation:
                    self.run_d4j_test(prob, index)
                self.num_of_patches += 1
                case_id += 1
                loc_dir = os.path.join(self.patch_pool_folder, str(loc_id), str(case_id))
                loc_file = os.path.basename(file_name)
                if self.save_patch_to_file(change, index, loc_dir, loc_file):
                    loc = os.path.join(str(loc_id), str(case_id), loc_file)
                    case_info = { "case": case_id, "location": loc, "prob": prob, "code": change, "edit": masked_line, "patch_no": self.num_of_patches }
                    case_list.append(case_info)
                    patch_ranking.append(loc)
        end_time = time.time()
        self.logger.logo("----------------- FINISH VALIDATION OF PATCHES -----------------")
        # Todo: Maybe change log to separate log file
        self.logger.logo("Patch Generation Time: {}".format(self.generation_time))
        self.logger.logo("Patch Validation Time: {}".format(end_time - start_time))
        # Convert file_map into rules
        for file_name in file_map:
            file_info = { "file": file_name, "functions": list(file_map[file_name].values()) }
            rules.append(file_info)
        info["rules"] = rules
        info["ranking"] = patch_ranking

class UNIAPRpatches(GVpatches):
    D4J_Struct = {
        'Chart': {
            'source': 'org',
            'classpath': 'build/'
        },
        'Closure': {
            'source': 'com',
            'classpath': 'build/classes:lib/*:build/lib/*'
        },
        'Lang': {
            'source': 'org',
            'classpath': 'target/classes'
        },
        'Math': {
            'source': 'org',
            'classpath': 'target/classes'
        },
        'Mockito': {
            'source': 'org',
            'classpath': 'target/classes'
        },
        'Time': {
            'source': 'org',
            'classpath': 'target/classes'
        }
    }

    def javac_compile(self, index):
        compiled = True
        try:
            subprocess.run("cd /tmp/" + self.bug_id + "; javac -cp " + self.D4J_Struct[self.bug_id.split("_")[0]][
                'classpath'] + " " + self.files[index].split(self.bug_id + "/")[-1],
                           shell=True, check=True, timeout=10)
        except subprocess.CalledProcessError as e:
            self.logger.logo(e.stderr)
            compiled = False
        except subprocess.TimeoutExpired as e:
            self.logger.logo(e.stderr)
            compiled = False
        return compiled

    def compile_d4j_project(self):
        compiled = True
        try:
            subprocess.run("defects4j compile -w %s" % ('/tmp/' + self.bug_id), stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            # print("Return code: {}".format(e.returncode))
            compiled = False

        return compiled

    def make_patch_pool_folder(self):
        maven_project_path = "~/prapr_data/Projects/" + self.bug_id.split("_")[0] + "/" + self.bug_id.split("_")[
            1] + "/" + self.patch_pool_folder
        subprocess.run('rm -rf ' + maven_project_path, shell=True)
        subprocess.run('mkdir ' + maven_project_path, shell=True)
        return

    def move_compiled_patch(self, index):
        # assert (len(class_changed) > 0)
        class_file = self.files[index].replace(".java", ".class")
        maven_project_path = "~/prapr_data/Projects/" + self.bug_id.split("_")[0] + "/" + self.bug_id.split("_")[
            1] + "/" + self.patch_pool_folder
        source_folder = self.D4J_Struct[self.bug_id.split("_")[0]]['source']
        partial_path = ""
        split_file = class_file.split("/")
        for i, file in enumerate(split_file):
            if file == source_folder:
                partial_path = "/".join(split_file[i:])
                break

        folder_name = "/".join(partial_path.split("/")[:-1])
        subprocess.run('mkdir -p ' + maven_project_path + "/" + str(self.num_of_patches) + "/" + folder_name,
                       shell=True)
        subprocess.run(
            'mv ' + class_file + " " + maven_project_path + "/" + str(self.num_of_patches) + "/" + partial_path,
            shell=True)
        subprocess.run('cp ' + self.files[index] + " " + maven_project_path + "/" + str(self.num_of_patches) + "/",
                       shell=True)

        return

    def syntax_check(self, index):
        with open(self.files[index], 'r', encoding='utf-8') as f:
            tmpcode = f.read()
            try:
                tokens = javalang.tokenizer.tokenize(tmpcode)
                parser = javalang.parser.Parser(tokens)
                parser.parse()
            except:
                return False
        return True

    def run_uniapr(self):
        success = True
        try:
            # grab basic uniapr output
            uniapr_val_file = "~/CodeBertAPR/" + self.logger.logfile.split(".txt")[0] + "_restart_val.txt"
            subprocess.run("cd ~/prapr_data/Projects/" + self.bug_id.split("_")[0] + "/" + self.bug_id.split("_")[1] +
                           "; mvn org.uniapr:uniapr-plugin:validate -DrestartJVM=true -Dd4jAllTestsFile=all_tests "
                           "-DpatchesPool=" + self.patch_pool_folder + ">" + uniapr_val_file,
                           shell=True, check=True)
        except subprocess.CalledProcessError as e:
            success = False
        return success

    def validate(self, info):  # different validation process than traditional
        # make folder
        num_of_compiled_patches = 0
        file_patches = {}
        start_time = time.time()
        self.make_patch_pool_folder()
        self.D4J_Struct[self.bug_id.split("_")[0]]['classpath'] = \
            os.popen('defects4j export -w %s -p cp.compile' % ('/tmp/' + self.bug_id)).readlines()[-1]
        self.D4J_Struct[self.bug_id.split("_")[0]]['classpath'] += ":" + os.popen('defects4j export -w %s -p cp.test' % ('/tmp/' + self.bug_id)).readlines()[-1]
        self.logger.logo("Class path: {}".format(self.D4J_Struct[self.bug_id.split("_")[0]]['classpath']))
        print("----------------- BEGIN VALIDATION OF PATCHES -----------------")
        for index in range(len(self.l_changes)):
            file_patches[self.files[index] + " " + str(self.line_numbers[index])] = \
                {'total': 0, 'compiled': 0, 'syntax error': 0}
            self.logger.logo(
                "---- Validating Patches for file: {} {} ----".format(self.files[index], self.line_numbers[index]))
            self.checkout_d4j_project()
            self.compile_d4j_project()
            for change, prob, masked_line in self.l_changes[index]:
                self.write_changes_to_file(change, index)
                self.logger.logo("----------------------------------------")
                self.logger.logo("Patch Number :{}".format(self.num_of_patches))
                self.logger.logo('- ' + self.fault_lines[index].strip())
                self.logger.logo('+ ' + change.strip())
                self.logger.logo('mask:' + masked_line.strip())
                if not self.skip_validation:
                    syntax = self.syntax_check(index)
                    if syntax:
                        compiled = self.javac_compile(index)
                        if compiled:
                            num_of_compiled_patches += 1
                            self.move_compiled_patch(index)
                            file_patches[self.files[index] + " " + str(self.line_numbers[index])]['compiled'] += 1
                        else:
                            self.logger.logo("Compiled Error")
                    else:
                        self.logger.logo("Syntax Error")
                        file_patches[self.files[index] + " " + str(self.line_numbers[index])]['syntax error'] += 1
                self.num_of_patches += 1
                file_patches[self.files[index] + " " + str(self.line_numbers[index])]['total'] += 1
        compile_end_time = time.time()
        self.logger.logo("----------------- RUNNING UNIAPR VALIDATION -----------------")
        if not self.skip_validation:
           success = self.run_uniapr()
           if success:
               self.logger.logo("Uniapr Success!")
           else:
               self.logger.logo("Uniapr Failure :(")
        uniapr_end_time = time.time()
        self.logger.logo("----------------- FINISH VALIDATION OF PATCHES -----------------")
        self.logger.logo(
            "Num of patches generated: {} compiled: {}".format(self.num_of_patches, num_of_compiled_patches))
        for file_line, item in file_patches.items():
            self.logger.logo("{}: Total: {} Compiled: {} Syntax Errors: {}".format(file_line, item['total'],
                                                                                   item['compiled'],
                                                                                   item['syntax error']))
        self.logger.logo("Patch Generation Time: {}".format(self.generation_time))
        self.logger.logo("Patch Validation Time: {}".format(uniapr_end_time - start_time))
        self.logger.logo("Patch Compilation Time: {}".format(compile_end_time - start_time))
        self.logger.logo("Uniapr Time: {}".format(uniapr_end_time - compile_end_time))
