from typing import List, Set, Dict, Tuple
import multiprocessing as mp
import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np
from enum import Enum
import math

class ToolType(Enum):
    recoder = 0
    seapr = 1
    guided = 2

class ResultType(Enum):
    hq_iter = 0
    plau_iter = 1
    correct_iter = 2
    hq_time = 3
    plau_time = 4
    correct_time = 5
    total_plau = 6
    correct_num = 7
    plau_num = 8

class Group(Enum):
    neg = -1
    neut = 0
    pos = 1
    undefined = 2

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

class ToolResult:
    def __init__(self, outdir: str, bugid: str, id: int, tool: ToolType, correct_patches: List[str]):
        self.outdir = outdir
        self.bugid = bugid
        self.tool = tool
        self.id = id
        self.correct_patches = correct_patches
        self.plau_iter = -1
        self.plau_time = -1
        self.correct_iter = -1
        self.correct_time = -1
        self.total_plau = -1
        self.has_correct_patch = False
        self.has_plau_patch = False
        self.has_result = True
        if tool == ToolType.guided:
            self.run(f"{outdir}/{bugid}-guided-{id}")
        else:
            self.run(f"{outdir}/{bugid}-{tool.name}")
        self.save(f"{outdir}/tmp/{bugid}.csv")

    def save(self, save_file: str) -> None:
        with open(save_file, "a") as f:
            f.write(f"{self.bugid},{self.tool.name},{self.id},{self.has_correct_patch},{self.correct_iter},{self.correct_time},{self.has_plau_patch},{self.plau_iter},{self.plau_time},{self.total_plau}\n")
    def run(self, target_dir: str):
        print(f"Analyzing {self.bugid} - {self.tool} - {self.id}")
        result_file = os.path.join(target_dir, f"msv-result.json")
        if not os.path.exists(result_file):
            print(f"Result file {result_file} does not exist!")
            self.has_result = False
            return
        with open(result_file, "r") as f:
            root = json.load(f)
            self.total_plau = 0
            iter = 0
            tm = 0
            for elem in root:
                iter = elem["iteration"]
                tm = elem["time"]
                is_pass = elem["pass_result"]
                config = elem["config"][0]
                patch_id = f'{config["id"]}-{config["case_id"]}'
                patch_loc = config["location"]
                if patch_id in self.correct_patches:
                    if not self.has_correct_patch:
                        self.correct_iter = iter
                        self.correct_time = tm
                        self.has_correct_patch = True
                if is_pass:
                    self.total_plau += 1
                    if not self.has_plau_patch:
                        self.plau_iter = iter
                        self.plau_time = tm
                        self.has_plau_patch = True
                if self.has_correct_patch:
                    break
            # Hack: if no correct patch, set the correct iter to the last iter
            if not self.has_correct_patch:
                self.correct_iter = iter
                self.correct_time = tm
                # self.has_correct_patch = True
            if not self.has_plau_patch:
                self.plau_iter = iter
                self.plau_time = tm
                self.total_plau = 0
                # self.has_plau_patch = True

class ProjectResult:
    def __init__(self, outdir: str, bugid: str, correct_patches: List[str]):
        self.bugid = bugid
        self.outdir = outdir
        self.correct_patches = correct_patches
        tmp_file = os.path.join(outdir, "tmp", f"{bugid}.csv")
        with open(tmp_file, "w") as f:
            f.write("bugid,tool,id,has_correct_patch,correct_iter,correct_time,has_plau_patch,plau_iter,plau_time,total_plau\n")
        self.recoder_result: ToolResult = ToolResult(outdir, bugid, 0, ToolType.recoder, correct_patches)
        self.seapr_result: ToolResult = ToolResult(outdir, bugid, 0, ToolType.seapr, correct_patches)
        self.guided_results: List[ToolResult] = list()
        self.has_correct_patch = len(correct_patches) > 0
        self.guided_group: Group = Group.undefined
        self.seapr_group: Group = Group.undefined
        for i in range(50):
            self.guided_results.append(ToolResult(outdir, bugid, i, ToolType.guided, correct_patches))
        self.result = dict()
        self.result[ToolType.recoder] = dict()
        self.result[ToolType.seapr] = dict()
        self.result[ToolType.guided] = dict()
        self.num_correct_in_guided = 0
        self.num_plau_in_guided = 0
        self.num_total_plau_in_guided = 0
        # These values are average
        self.total_correct_iter_guided = 0
        self.total_correct_time_guided = 0
        self.total_plau_iter_guided = 0
        self.total_plau_time_guided = 0
        self.total_total_plau_guided = 0
        # self.analyze()

    def get_impv(self, base: float, target: float) -> float:
        if base == 0:
            print("ERROR: base is 0!")
            return 0
        return (base - target) / base
    
    def get_iter_result_str(self) -> str:
        recoder_correct_iter = self.recoder_result.correct_iter
        recoder_plau_iter = self.recoder_result.plau_iter
        recoder_plau_total = self.recoder_result.total_plau
        recoder_str = f",,{recoder_plau_iter},{recoder_correct_iter},{recoder_plau_total}"
        seapr_correct_iter = self.seapr_result.correct_iter
        seapr_plau_iter = self.seapr_result.plau_iter
        seapr_correct_impv = self.get_impv(seapr_correct_iter, recoder_correct_iter)
        seapr_plau_impv = self.get_impv(seapr_plau_iter, recoder_plau_iter)
        seapr_plau_total = self.seapr_result.total_plau
        seapr_str = f"{seapr_plau_impv},{seapr_correct_impv},{seapr_plau_iter},{seapr_correct_iter},{seapr_plau_total}"
        guided_correct_iter = self.total_correct_iter_guided
        guided_plau_iter = self.total_plau_iter_guided
        guided_correct_impv = self.get_impv(guided_correct_iter, recoder_correct_iter)
        guided_plau_impv = self.get_impv(guided_plau_iter, recoder_plau_iter)
        guided_plau_total = self.total_total_plau_guided
        guided_str = f"{guided_plau_impv},{guided_correct_impv},{guided_plau_iter},{guided_correct_iter},{guided_plau_total}"
        return f"{self.bugid},{guided_str},{seapr_str},{recoder_str},{self.seapr_group.name},{self.guided_group.name}\n"
    
    def get_time_result_str(self) -> str:
        recoder_correct_time = self.recoder_result.correct_time
        recoder_plau_time = self.recoder_result.plau_time
        recoder_plau_total = self.recoder_result.total_plau
        recoder_str = f",,{recoder_plau_time},{recoder_correct_time},{recoder_plau_total}"
        seapr_correct_time = self.seapr_result.correct_time
        seapr_plau_time = self.seapr_result.plau_time
        seapr_correct_impv = self.get_impv(recoder_correct_time, seapr_correct_time)
        seapr_plau_impv = self.get_impv(recoder_plau_time, seapr_plau_time)
        seapr_plau_total = self.seapr_result.total_plau
        seapr_str = f"{seapr_plau_impv},{seapr_correct_impv},{seapr_plau_time},{seapr_correct_time},{seapr_plau_total}"
        guided_correct_time = self.total_correct_time_guided
        guided_plau_time = self.total_plau_time_guided
        guided_correct_impv = self.get_impv(recoder_correct_time, guided_correct_time)
        guided_plau_impv = self.get_impv(recoder_plau_time, guided_plau_time)
        guided_plau_total = self.total_total_plau_guided
        guided_str = f"{guided_plau_impv},{guided_correct_impv},{guided_plau_time},{guided_correct_time},{guided_plau_total}"
        return f"{self.bugid},{guided_str},{seapr_str},{recoder_str},{self.seapr_group.name},{self.guided_group.name}\n"
    
    def analyze(self):
        group_type = ResultType.correct_time
        # SeAPR
        if self.recoder_result.has_correct_patch:
            self.result[ToolType.recoder][ResultType.correct_num] = 1
        else:
            self.result[ToolType.recoder][ResultType.correct_num] = 0
        self.result[ToolType.recoder][ResultType.correct_iter] = self.recoder_result.correct_iter
        self.result[ToolType.recoder][ResultType.correct_time] = self.recoder_result.correct_time
        
        if self.recoder_result.has_plau_patch:
            self.result[ToolType.recoder][ResultType.plau_num] = 1
        else:
            self.result[ToolType.recoder][ResultType.plau_num] = 0
        self.result[ToolType.recoder][ResultType.plau_iter] = self.recoder_result.plau_iter
        self.result[ToolType.recoder][ResultType.plau_time] = self.recoder_result.plau_time
        self.result[ToolType.recoder][ResultType.total_plau] = self.recoder_result.total_plau

        if self.seapr_result.has_correct_patch:
            self.result[ToolType.seapr][ResultType.correct_num] = 1
        else:
            self.result[ToolType.seapr][ResultType.correct_num] = 0
        self.result[ToolType.seapr][ResultType.correct_iter] = self.seapr_result.correct_iter
        self.result[ToolType.seapr][ResultType.correct_time] = self.seapr_result.correct_time
        if self.seapr_result.has_plau_patch:
            self.result[ToolType.seapr][ResultType.plau_num] = 1
        else:
            self.result[ToolType.seapr][ResultType.plau_num] = 0
        self.result[ToolType.seapr][ResultType.plau_iter] = self.seapr_result.plau_iter
        self.result[ToolType.seapr][ResultType.plau_time] = self.seapr_result.plau_time
        self.result[ToolType.seapr][ResultType.total_plau] = self.seapr_result.total_plau
        # Guided
        self.result[ToolType.guided][ResultType.correct_iter] = 0.0
        self.result[ToolType.guided][ResultType.correct_time] = 0.0
        self.result[ToolType.guided][ResultType.correct_num] = 0
        self.result[ToolType.guided][ResultType.plau_iter] = 0.0
        self.result[ToolType.guided][ResultType.plau_time] = 0.0
        self.result[ToolType.guided][ResultType.total_plau] = 0
        self.result[ToolType.guided][ResultType.plau_num] = 0
        for guided_result in self.guided_results:
            if guided_result.has_correct_patch:
                self.result[ToolType.guided][ResultType.correct_num] += 1
            self.num_correct_in_guided += 1
            self.result[ToolType.guided][ResultType.correct_iter] += guided_result.correct_iter
            self.result[ToolType.guided][ResultType.correct_time] += guided_result.correct_time
            self.total_correct_iter_guided += guided_result.correct_iter
            self.total_correct_time_guided += guided_result.correct_time
            if guided_result.has_plau_patch:
                self.result[ToolType.guided][ResultType.plau_num] += 1
            self.num_plau_in_guided += 1
            self.result[ToolType.guided][ResultType.plau_iter] += guided_result.plau_iter
            self.result[ToolType.guided][ResultType.plau_time] += guided_result.plau_time
            self.result[ToolType.guided][ResultType.total_plau] += guided_result.total_plau
            self.total_plau_iter_guided += guided_result.plau_iter
            self.total_plau_time_guided += guided_result.plau_time
            self.total_total_plau_guided += guided_result.total_plau
        # Divide by total number
        if self.num_correct_in_guided > 0:
            self.result[ToolType.guided][ResultType.correct_iter] /= self.num_correct_in_guided
            self.result[ToolType.guided][ResultType.correct_time] /= self.num_correct_in_guided
            self.total_correct_iter_guided /= self.num_correct_in_guided
            self.total_correct_time_guided /= self.num_correct_in_guided
            # Get group
            if self.result[ToolType.guided][group_type] > 0.01:
                self.guided_group = Group.pos
            elif self.result[ToolType.guided][group_type] < -0.01:
                self.guided_group = Group.neg
            else:
                self.guided_group = Group.neut
        if self.num_plau_in_guided > 0:
            self.result[ToolType.guided][ResultType.plau_iter] /= self.num_plau_in_guided
            self.result[ToolType.guided][ResultType.plau_time] /= self.num_plau_in_guided
            self.total_plau_iter_guided /= self.num_plau_in_guided
            self.total_plau_time_guided /= self.num_plau_in_guided
            self.total_total_plau_guided /= self.num_plau_in_guided

class TotalResult:
    def __init__(self, outdir: str, bugids: List[str], correct_patch_dict: Dict[str, List[str]]):
        self.outdir = outdir
        self.bugids = bugids
        self.correct_patch_dict = correct_patch_dict
        self.result: Dict[str, ProjectResult] = dict()
    
    def run(self):
        # Analyze result
        for bugid in self.bugids:
            correct_patch = list()
            if bugid in self.correct_patch_dict:
                correct_patch = self.correct_patch_dict[bugid]
            self.result[bugid] = ProjectResult(self.outdir, bugid, correct_patch)
    
    def calculate_group_result(self, origin: Dict[ResultType, List[float]], group_result: Dict[ResultType, float]) -> None:
        if len(origin) == 0:
            for res_type in group_result:
                origin[res_type] = list()
        for res_type in group_result:
            origin[res_type].append(group_result[res_type])

    def init_group_result(self, group_result: Dict[Group, List[Dict[ResultType, float]]]):
        for group in Group:
            group_result[group] = list()

    def collect_group_result(self, result_list: List[Dict[ResultType, float]], type: ResultType) -> float:
        total = 0.0
        for result in result_list:
            total += result[type]
        return total / len(result_list)

    def get_reduction(self, original: Dict[ResultType, float], target: Dict[ResultType, float], type: ResultType) -> float:
        if original[type] == 0:
            print("Error: original is 0")
            return 0
        return (original[type] - target[type]) / original[type]

    def get_group_result(self, is_time: bool) -> List[str]:
        contents = list()
        # Classify result
        seapr_group_original_result: Dict[Group, List[Dict[ResultType, float]]] = dict()
        self.init_group_result(seapr_group_original_result)
        seapr_group_result: Dict[Group, List[Dict[ResultType, float]]] = dict()
        self.init_group_result(seapr_group_result)
        guided_group_original_result: Dict[Group, List[Dict[ResultType, float]]] = dict()
        self.init_group_result(guided_group_original_result)
        guided_group_result: Dict[Group, List[Dict[ResultType, float]]] = dict()
        self.init_group_result(guided_group_result)

        # Collect result and reduction
        res_type = ResultType.correct_time if is_time else ResultType.correct_iter
        seapr_reduction: Dict[Group, float] = dict()
        guided_reduction: Dict[Group, float] = dict()
        for bugid in self.bugids:
            proj_result = self.result[bugid]
            recoder_res = proj_result.result[ToolType.recoder]
            seapr_res = proj_result.result[ToolType.seapr]
            guided_res = proj_result.result[ToolType.guided]
            seapr_reduction += self.get_reduction(recoder_res, seapr_res, res_type)
            guided_reduction += self.get_reduction(recoder_res, guided_res, res_type)
            seapr_group_result[proj_result.seapr_group].append(seapr_res)
            seapr_group_result[Group.undefined].append(seapr_res)
            seapr_group_original_result[proj_result.seapr_group].append(recoder_res)
            seapr_group_original_result[Group.undefined].append(recoder_res)
            guided_group_result[proj_result.guided_group].append(guided_res)
            guided_group_result[Group.undefined].append(guided_res)
            guided_group_original_result[proj_result.guided_group].append(recoder_res)
            guided_group_original_result[Group.undefined].append(recoder_res)
        # Calculate result
        if is_time:
            contents.append(f"Group,Size,Time_org,Time_casino,diff,reduction,#Correct_exists\n")
        else:
            contents.append("Group,Size,NPC_org,NPC_casino,diff,reduction,#Correct_exists\n")
        for group in Group:
            guided_str = f"{group.name},"
            if group == Group.undefined:
                guided_str = "ALL,"
            guided_size = len(seapr_group_result[group])
            org_npc = self.collect_group_result(seapr_group_original_result[group], res_type)
            guided_npc = self.collect_group_result(seapr_group_result[group], res_type)
            diff = org_npc - guided_npc
            reduction = guided_reduction / guided_size
            corr_exists = self.collect_group_result(seapr_group_result[group], ResultType.correct_num)
            guided_str += f"{guided_size},{org_npc},{guided_npc},{diff},{reduction},{corr_exists}\n"
            contents.append(seapr_str)
        contents.append("\n")
        if is_time:
            contents.append(f"Group,Size,Time_org,Time_seapr,diff,reduction\n")
        else:
            contents.append("Group,Size,NPC_org,NPC_seapr,diff,reduction\n")
        for group in Group:
            seapr_str = f"{group.name},"
            if group == Group.undefined:
                seapr_str = "ALL,"
            seapr_size = len(seapr_group_result[group])
            org_npc = self.collect_group_result(seapr_group_original_result[group], res_type)
            seapr_npc = self.collect_group_result(seapr_group_result[group], res_type)
            diff = org_npc - seapr_npc
            reduction = seapr_reduction / seapr_size
            corr_exists = self.collect_group_result(seapr_group_result[group], ResultType.correct_num)
            seapr_str += f"{seapr_size},{org_npc},{seapr_npc},{diff},{reduction},{corr_exists}\n"
            contents.append(seapr_str)
        return contents

    def write_result(self):
        # Write result
        with open(os.path.join(self.outdir, "result-iter.csv"), "w") as f:
            f.write(",guided,,,,,seapr,,,,,recoder,,,,,group_casino,group_seapr\n")
            f.write(",plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau\n")
            for bugid in self.bugids:
                f.write(self.result[bugid].get_iter_result_str())
            f.write("\n")
            f.writelines(self.get_group_result(False))
        with open(os.path.join(self.outdir, "result-time.csv"), "w") as f:
            f.write(",guided,,,,,seapr,,,,,recoder,,,,,group_casino,group_seapr\n")
            f.write(",plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau\n")
            for bugid in self.bugids:
                f.write(self.result[bugid].get_time_result_str())
            f.write("\n")
            f.writelines(self.get_group_result(True))
            

def get_bugids(bugid_file: str) -> List[str]:
    bugids = []
    with open(bugid_file, "r") as f:
        for line in f:
            line = line.strip()
            if len(line) == 0 or line.startswith("#"):
                continue
            bugid = line.split(",")[0]
            bugids.append(bugid)
    return bugids

class Result(Enum):
    bugid = 0
    tool = 1
    id = 2
    has_correct_patch = 3
    correct_iter = 4
    correct_time = 5
    has_plau_patch = 6
    plau_iter = 7
    plau_time = 8
    total_plau = 9

def parse_line(line: str) -> Tuple[str, str, str, bool, int, float, bool, int, float, int]:
    bugid,tool,id,has_correct_patch,correct_iter,correct_time,has_plau_patch,plau_iter,plau_time,total_plau = line.split(",")
    return bugid,tool,id,has_correct_patch=="True",int(correct_iter),float(correct_time),has_plau_patch=="True",int(plau_iter),float(plau_time),int(total_plau)

def recoder_to_str(line: tuple) -> str:
    bugid = line[Result.bugid.value]
    tool = line[Result.tool.value]
    id = line[Result.id.value]
    has_correct_patch = line[Result.has_correct_patch.value]
    correct_iter = line[Result.correct_iter.value]
    correct_time = line[Result.correct_time.value]
    has_plau_patch = line[Result.has_plau_patch.value]
    plau_iter = line[Result.plau_iter.value]
    plau_time = line[Result.plau_time.value]
    total_plau = line[Result.total_plau.value]
    # has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau
    return f"{has_plau_patch},{has_correct_patch},,,{plau_iter},{correct_iter},{total_plau}"

def seapr_to_str(recoder: tuple, line: tuple) -> str:
    recoder_tool = recoder[Result.tool.value]
    recoder_id = recoder[Result.id.value]
    recoder_has_correct_patch = recoder[Result.has_correct_patch.value]
    recoder_correct_iter = recoder[Result.correct_iter.value]
    recoder_correct_time = recoder[Result.correct_time.value]
    recoder_has_plau_patch = recoder[Result.has_plau_patch.value]
    recoder_plau_iter = recoder[Result.plau_iter.value]
    recoder_plau_time = recoder[Result.plau_time.value]
    recoder_total_plau = recoder[Result.total_plau.value]
    # seapr
    tool = line[Result.tool.value]
    id = line[Result.id.value]
    has_correct_patch = line[Result.has_correct_patch.value]
    correct_iter = line[Result.correct_iter.value]
    correct_time = line[Result.correct_time.value]
    has_plau_patch = line[Result.has_plau_patch.value]
    plau_iter = line[Result.plau_iter.value]
    plau_time = line[Result.plau_time.value]
    total_plau = line[Result.total_plau.value]
    plau_impv = ""
    if has_plau_patch and recoder_has_plau_patch:
        plau_impv = "%.4f" % ((recoder_plau_iter - plau_iter) / recoder_plau_iter * 100)
    corr_impv = ""
    if has_correct_patch and recoder_has_correct_patch:
        corr_impv = "%.4f" % ((recoder_correct_iter - correct_iter) / recoder_correct_iter * 100)
    # has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau
    return f"{has_plau_patch},{has_correct_patch},{plau_impv},{corr_impv},{plau_iter},{correct_iter},{total_plau}"

def count_guided(lines: List[tuple]) -> tuple:
    num_correct = 0
    num_plau = 0
    for line in lines:
        has_correct_patch = line[Result.has_correct_patch.value]
        has_plau_patch = line[Result.has_plau_patch.value]
        if has_correct_patch:
            num_correct += 1
        if has_plau_patch:
            num_plau += 1
    return num_plau, num_correct

def guided_to_str(recoder: tuple, lines: List[tuple]) -> str:
    recoder_has_correct_patch = recoder[Result.has_correct_patch.value]
    recoder_correct_iter = recoder[Result.correct_iter.value]
    recoder_correct_time = recoder[Result.correct_time.value]
    recoder_has_plau_patch = recoder[Result.has_plau_patch.value]
    recoder_plau_iter = recoder[Result.plau_iter.value]
    recoder_plau_time = recoder[Result.plau_time.value]
    recoder_total_plau = recoder[Result.total_plau.value]

    # num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau    
    num_plau, num_correct = count_guided(lines)
    guided_plau_iter = 0
    guided_corr_iter = 0
    guided_total_plau = 0
    n = len(lines)
    for line in lines:
        has_correct_patch = line[Result.has_correct_patch.value]
        correct_iter = line[Result.correct_iter.value]
        correct_time = line[Result.correct_time.value]
        has_plau_patch = line[Result.has_plau_patch.value]
        plau_iter = line[Result.plau_iter.value]
        plau_time = line[Result.plau_time.value]
        total_plau = line[Result.total_plau.value]
        guided_plau_iter += plau_iter
        guided_corr_iter += correct_iter
        guided_total_plau += total_plau
    guided_plau_iter /= n
    guided_corr_iter /= n
    guided_total_plau /= n
    corr_impv = ""
    if num_correct > 0 and recoder_has_correct_patch:
        corr_impv = "%.4f" % ((recoder_correct_iter - guided_corr_iter) / recoder_correct_iter * 100)
    plau_impv = ""
    if num_plau > 0 and recoder_has_plau_patch:
        plau_impv = "%.4f" % ((recoder_plau_iter - guided_plau_iter) / recoder_plau_iter * 100)
    return f"{num_plau},{num_correct},{plau_impv},{corr_impv},{guided_plau_iter},{guided_corr_iter},{guided_total_plau}"

def load_bugid(bugid_file: str, bugid: str) -> str:
    recoder_result = None
    seapr_result = None
    guided_result = list()
    with open(bugid_file, "r") as f:
        for line in f.readlines():
            line = line.strip()
            if len(line) == 0 or line.startswith("#"):
                continue
            if not line.startswith(bugid):
                continue
            res = parse_line(line)
            if res[Result.tool.value] == "recoder":
                recoder_result = res
            elif res[Result.tool.value] == "seapr":
                seapr_result = res
            elif res[Result.tool.value] == "guided":
                guided_result.append(res)
    "bugid,num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau\n"
    recoder_str = recoder_to_str(recoder_result)
    seapr_str = seapr_to_str(recoder_result, seapr_result)
    guided_str = guided_to_str(recoder_result, guided_result)
    return f"{bugid},{guided_str},{seapr_str},{recoder_str}\n"

def main(args: List[str]) -> None:
    if len(args) < 4:
        print("Usage: gen-result-table.py <recoder-path> <outdir> <id>")
        return
    recoder_path = args[1]
    outdir = args[2]
    id = args[3]
    result_dir = f"{recoder_path}/out-result/{id}"
    os.makedirs(result_dir, exist_ok=True)
    correct_patch_dict = get_correct_patch(os.path.join(recoder_path, "data", "correct_patch.csv"))
    bugids = get_bugids(os.path.join(recoder_path, "data", "correct_patch.csv"))
    bugids = sort_bugids(bugids)
    if not os.path.exists(outdir + "/tmp"):
        os.makedirs(outdir + "/tmp", exist_ok=True)
        total_result = TotalResult(outdir, bugids, correct_patch_dict)
        total_result.run()
        # total_result.write_result()
    # TODO: read result from file
    os.system("cp -r " + outdir + "/tmp " + result_dir)
    result_file = os.path.join(result_dir, "result.csv")
    with open(result_file, "w") as f:
        f.write(",guided,,,,,,,seapr,,,,,,,recoder,,,,,,,group_casino,group_seapr\n")
        f.write(",num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau\n")
        for bugid in bugids:
            tmp_file = os.path.join(result_dir, "tmp", bugid + ".csv")
            result = load_bugid(tmp_file, bugid)
            f.write(result)


        

def get_iqr(data):
  q1 = np.quantile(data, 0.25)
  q2 = np.quantile(data, 0.50)
  q3 = np.quantile(data, 0.75)
  iqr = q3 - q1
  q4 = np.quantile(data, 1)
  q1_list = list()
  q2_list = list()
  q3_list = list()
  q4_list = list()
  iqr_list = list()
  for i in range(len(data)):
    if data[i] < q1:
      q1_list.append(data[i])
    elif data[i] < q2:
      iqr_list.append(data[i])
      q2_list.append(data[i])
    elif data[i] < q3:
      iqr_list.append(data[i])
      q3_list.append(data[i])
    else:
      q4_list.append(data[i])
  print("iqr: ", iqr, )    
  print("q1: ", q1, )
  print("q2: ", q2, )
  print("q3: ", q3, )

def check_dir(dir: str) -> bool:
    if not os.path.exists(dir):
        print(f"Dir {dir} does not exist!")
        return False
    return True


def analyze_result(recoder_path: str, bugid: str, target_dir: str, correct_patches: List[str]) -> Tuple[int, float, int, float, int]:
    """
    Analyze the result of a bugid.
    Return: (plau iter, plau time, correct iter, correct time, total plau)
    """
    result_file = os.path.join(target_dir, f"msv-result.json")
    sim_file = os.path.join(recoder_path, "sim-corr", bugid, f"{bugid}-sim.json")
    sim = dict()
    if os.path.exists(sim_file):
        try:
            with open(sim_file, "r") as f:
                sim = json.load(f)
        except:
            print(bugid + " error!")
    if not os.path.exists(result_file):
        print(f"Result file {result_file} does not exist!")
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
            tm = elem["time"]
            is_pass = elem["pass_result"]
            config = elem["config"][0]
            patch_id = f'{config["id"]}-{config["case_id"]}'
            patch_loc = config["location"]
            # if int(tm / 60) > 60:
            #     break
            # if patch_loc in sim:
            #     patch = sim[patch_loc]
            #     fail_time = patch["fail_time"]
            #     pass_time = patch["pass_time"]
            #     tm = fail_time + pass_time
            #     global_time += tm
            #     time = global_time
            # else:
            #     print("NOT IN SIM!!!")
            if patch_id in correct_patches:
                if not found_correct:
                    ci = iter
                    ct = tm
                    found_correct = True
            if is_pass:
                total_plau += 1
                if not found_plausible:
                    pi = iter
                    pt = tm
                    found_plausible = True
            if found_correct:
                break
        return pi, pt, ci, ct, total_plau


def main_old(args: List[str]) -> None:
    if len(args) < 4:
        print("Usage: gen-result-table.py <recoder-path> <outdir> <[?group]>")
        return
    recoder_path = args[1]
    outdir = args[2]
    # id = args[3]
    if len(args) == 4:
        global use_group
        use_group = True
    if not os.path.exists(outdir):
        print(f"Outdir {outdir} does not exist!")
        return
    os.system(f"mv {outdir}/tmp {outdir}/tmp-bak")
    os.makedirs(outdir + "/tmp", exist_ok=True)
    correct_patch_dict = get_correct_patch(os.path.join(recoder_path, "data", "correct_patch.csv"))
    bugids = list(correct_patch_dict.keys())
    bugids = sort_bugids(bugids)
    result = [",guided,,,,,seapr,,,,,recoder,,,,,group_casino,group_seapr",
              ",plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau"]
    t_result = [",guided,,,,,seapr,,,,,recoder,,,,,group_casino,group_seapr",
                ",plau_impv%,corr_impv%,plau_time,corr_time,total_plau,plau_impv%,corr_impv%,plau_time,corr_time,total_plau,plau_impv%,corr_impv%,plau_time,corr_time,total_plau"]
    total_guided = [0, 0]
    t_total_guided = [0, 0]
    total_seapr = [0, 0]
    t_total_seapr = [0, 0]
    total_recoder = [0, 0]
    t_total_recoder = [0, 0]
    if use_group:
        groups = dict()
        groups_seapr = dict()
        with open(os.path.join(outdir, f"tmp-recoder-result.csv")) as f:
            lines = f.readlines()
            for line in lines:
                tokens = line.strip().split(",")
                print(tokens)
                bugid = tokens[0]
                corr_impv = float(tokens[2])
                corr_iter = tokens[4]
                org_iter = tokens[14]
                seapr_impv = float(tokens[7])
                if corr_impv > 1:
                    groups[bugid] = 1
                elif corr_impv < -1:
                    groups[bugid] = -1
                else:
                    groups[bugid] = 0
                if seapr_impv > 1:
                    groups_seapr[bugid] = 1
                elif seapr_impv < -1:
                    groups_seapr[bugid] = -1
                else:
                    groups_seapr[bugid] = 0
    final_list_pos = list()
    final_list_neut = list()
    final_list_neg = list()
    pos_dict = dict()
    neg_dict = dict()
    neut_dict = dict()
    base_pos_iter = 0
    base_neg_iter = 0
    base_neut_iter = 0
    base_pos_dict = dict()
    base_neg_dict = dict()
    base_neut_dict = dict()
    final_list_pos_seapr = list()
    final_list_neut_seapr = list()
    final_list_neg_seapr = list()
    for i in range(50):
        pos_dict[i] = 0
        neg_dict[i] = 0
        neut_dict[i] = 0
        base_pos_dict[i] = 0
        base_neg_dict[i] = 0
        base_neut_dict[i] = 0
    for bugid in bugids:
        print(bugid)
        # if bugid not in groups:
        #     continue
        # os.makedirs(os.path.join("/root/project/Recoder/switch-info", bugid), exist_ok=True)
        # os.system(f"cp {os.path.join(recoder_path, 'd4j', bugid, 'switch-info.json')} {os.path.join('/root/project/Recoder/switch-info', bugid)}")
        # continue
        original_dir = os.path.join(outdir, f"{bugid}-recoder")
        if not check_dir(original_dir):
            continue
        result_recoder = analyze_result(recoder_path, bugid, original_dir, correct_patch_dict[bugid])
        # print(f"Recoder: {result_recoder}")
        p_base = result_recoder[0]
        t_p_base = result_recoder[1]
        c_base = result_recoder[2]
        t_c_base = result_recoder[3]
        plau_iter = "-"
        plau_time = "-"
        corr_iter = "-"
        corr_time = "-"
        plau_impv = "-"
        t_plau_impv = "-"
        corr_impv = "-"
        t_corr_impv = "-"
        if use_group:
            if groups[bugid] == 1:
                base_pos_iter += c_base
            elif groups[bugid] == -1:
                base_neg_iter += c_base
            else:
                base_neut_iter += c_base
        if p_base > 0:
            plau_iter = str(p_base)
            plau_time = str(t_p_base)
            total_recoder[0] += p_base
            t_total_recoder[0] += t_p_base
        if c_base > 0:
            corr_iter = str(c_base)
            corr_time = str(t_c_base)
            total_recoder[1] += c_base
            t_total_recoder[1] += t_c_base
        result_str_recoder = f"-,-,{plau_iter},{corr_iter},{result_recoder[4]}"
        t_result_str_recoder = f"-,-,{plau_time},{corr_time},{result_recoder[4]}"
        seapr_dir = os.path.join(outdir, f"{bugid}-seapr")
        result_seapr = analyze_result(recoder_path, bugid, seapr_dir, correct_patch_dict[bugid])
        # print(f"Seapr: {result_seapr}")
        plau_seapr = result_seapr[0]
        t_plau_seapr = result_seapr[1]
        corr_seapr = result_seapr[2]
        t_corr_seapr = result_seapr[3]
        plau_iter = "-"
        plau_time = "-"
        corr_iter = "-"
        corr_time = "-"
        plau_impv = "-"
        t_plau_impv = "-"
        corr_impv = "-"
        t_corr_impv = "-"
        if plau_seapr > 0:
            plau_iter = str(plau_seapr)
            plau_time = str(t_plau_seapr)
            total_seapr[0] += plau_seapr
            t_total_seapr[0] += t_plau_seapr
            if p_base > 0:
                plau_impv = '%0.4f' % (100 * (p_base - plau_seapr) / p_base)
                t_plau_impv = '%0.4f' % (100 * (t_p_base - t_plau_seapr) / t_p_base)
        
        corr_impv_seapr = 100 * (c_base - corr_seapr) / c_base
        if corr_impv_seapr > 1:
            final_list_pos_seapr.append(corr_impv_seapr)
        elif corr_impv_seapr < -1:
            final_list_neg_seapr.append(corr_impv_seapr)
        else:
            final_list_neut_seapr.append(corr_impv_seapr)

        if corr_seapr > 0:
            corr_iter = str(corr_seapr)
            corr_time = str(t_corr_seapr)
            total_seapr[1] += corr_seapr
            t_total_seapr[1] += t_corr_seapr
            if c_base > 0:
                corr_impv = '%0.4f' % (100 * (c_base - corr_seapr) / c_base)
                t_corr_impv = '%0.4f' % (100 * (t_c_base - t_corr_seapr) / t_c_base)
        result_str_seapr = f"{plau_impv},{corr_impv},{plau_iter},{corr_iter},{result_seapr[4]}"
        t_result_str_seapr = f"{t_plau_impv},{t_corr_impv},{plau_time},{corr_time},{result_seapr[4]}"
        # with open(f"{outdir}/seapr.csv", "a") as tex:
        #     seapr_group = 0
        #     if (c_base - corr_seapr) / c_base > 0.01:
        #         seapr_group = 2
        #     elif (c_base - corr_seapr) / c_base < -0.01:
        #         seapr_group = -2
        #     tex.write(f"{bugid},{seapr_group},{corr_seapr},{c_base}\n")
        result_guided = list()
        cc = 0
        pc = 0
        gpi = 0
        gpt = 0
        gci = 0
        gct = 0
        total_plau_guided = 0
        tc = 0
        for i in range(50):
            guided_dir = os.path.join(outdir, f"{bugid}-guided-{i}")
            tmp_result = analyze_result(recoder_path, bugid, guided_dir, correct_patch_dict[bugid])
            # print(f"Guided {i}: {tmp_result}")
            guided_correct_iter = tmp_result[2]
            guided_correct_impv = (c_base - guided_correct_iter) / c_base * 100
            with open(os.path.join(outdir, "tmp", f"result-{i}.csv"), "a") as tmp:
                tmp.write(f"{bugid},{guided_correct_impv},{guided_correct_iter},{c_base}\n")
            if guided_correct_iter < 0:
                print(f"No correct patch in {bugid} - {i}")
            if use_group:
                print(f"{bugid}-{i} impv: {guided_correct_impv}")
                if groups[bugid] == 1:
                    pos_dict[i] += guided_correct_iter
                elif groups[bugid] == -1:
                    neg_dict[i] += guided_correct_iter
                else:
                    neut_dict[i] += guided_correct_iter
            """
            # if guided_correct_impv > 1:
            #     pos_dict[i] += guided_correct_iter
            #     base_pos_dict[i] += c_base
            #     # final_list_pos.append(guided_correct_impv)
            # elif guided_correct_impv < -1:
            #     neg_dict[i] += guided_correct_iter
            #     base_neg_dict[i] += c_base
            #     # final_list_neg.append(guided_correct_impv)
            # else:
            #     neut_dict[i] += guided_correct_iter
            #     base_neut_dict[i] += c_base
            #     # final_list_neut.append(guided_correct_impv)
            """
            if tmp_result[0] >= 0:
                gpi += tmp_result[0]
                gpt += tmp_result[1]
                pc += 1
            if tmp_result[2] >= 0:
                gci += tmp_result[2]
                gct += tmp_result[3]
                cc += 1
            if tmp_result[4] > 0:
                total_plau_guided += tmp_result[4]
                tc += 1
        plau_guided = "-"
        t_plau_guided = "-"
        plau_impv = "-"
        t_plau_impv = "-"
        corr_guided = "-"
        t_corr_guided = "-"
        corr_impv = "-"
        t_corr_impv = "-"
        if pc > 0:
            gpi /= pc
            gpt /= pc
            total_guided[0] += gpi
            t_total_guided[0] += gpt
            plau_guided = str(gpi)
            t_plau_guided = str(gpt)
            if p_base > 0:
                plau_impv = '%0.4f' % (100 * (p_base - gpi) / p_base)
                t_plau_impv = '%0.4f' % (100 * (t_p_base - gpt) / t_p_base)
        if cc > 0:
            gci /= cc
            gct /= cc
            total_guided[1] += gci
            t_total_guided[1] += gct
            corr_guided = str(gci)
            t_corr_guided = str(gct)
            if c_base > 0:
                corr_impv = '%0.4f' % (100 * (c_base - gci) / c_base)
                t_corr_impv = '%0.4f' % (100 * (t_c_base - gct) / t_c_base)
        # if tc > 0:
        #     total_plau_guided /= tc
        group_num = 0
        if (c_base - gci) / c_base > 0.01:
            group_num = 2
        elif (c_base - gci) / c_base < -0.01:
            group_num = -2
        total_plau_guided = total_plau_guided / 50
        result_str_guided = f"{plau_impv},{corr_impv},{plau_guided},{corr_guided},{total_plau_guided}"
        t_result_str_guided = f"{t_plau_impv},{t_corr_impv},{t_plau_guided},{t_corr_guided},{total_plau_guided}"
        result_str = f"{bugid},{result_str_guided},{result_str_seapr},{result_str_recoder},{group_num}"        
        if use_group:
            t_result_str = f"{bugid},{t_result_str_guided},{t_result_str_seapr},{t_result_str_recoder},{2 * groups[bugid]},{2*groups_seapr[bugid]}"
        else:
            t_result_str = f"{bugid},{t_result_str_guided},{t_result_str_seapr},{t_result_str_recoder}"
        result.append(result_str)
        t_result.append(t_result_str)
    total_str = f"TOTAL,,,{total_guided[0]},{total_guided[1]},,,,{total_seapr[0]},{total_seapr[1]},,,,{total_recoder[0]},{total_recoder[1]},,"
    result.append(total_str)
    num = len(result) - 1
    # result.extend([f'"pos","=COUNTIF(B$3:B${num}, "">1"")","=COUNTIF(C$3:C${num}, "">1"")"," ",," ","=COUNTIF(G$3:G${num}, "">1"")","=COUNTIF(H$3:H${num}, "">1"")"," ",," "," ","=COUNTIF(M$3:M${num}, "">1"")"," ","=COUNTIF(O$3:O${num}, "">1"")",',
    #                f'"neg","=COUNTIF(B$3:B${num}, ""<-1"")","=COUNTIF(C$3:C${num}, ""<-1"")"," ",," ","=COUNTIF(G$3:G${num}, ""<-1"")","=COUNTIF(H$3:H${num}, ""<-1"")"," ",," "," ","=COUNTIF(M$3:M${num}, ""<-1"")"," ","=COUNTIF(O$3:O${num}, ""<-1"")",',
    #                f'"eq","=COUNTIF(B$3:B${num}, ""=0"")","=COUNTIF(C$3:C${num}, ""=0"")"," ",," ","=COUNTIF(G$3:G${num}, ""=0"")","=COUNTIF(H$3:H${num}, ""=0"")"," ",," "," "," "," "," ",',
    #                f'"Pos 10%","=COUNTIF(B$3:B${num}, "">10"")","=COUNTIF(C$3:C${num}, "">10"")"," ",," ","=COUNTIF(G$3:G${num}, "">10"")","=COUNTIF(H$3:H${num}, "">10"")"," ",," "," "," "," "," ",',
    #                f'"Neg 10%","=COUNTIF(B$3:B${num}, ""<-10"")","=COUNTIF(C$3:C${num}, ""<-10"")"," ",," ","=COUNTIF(G$3:G${num}, ""<-10"")","=COUNTIF(H$3:H${num}, ""<-10"")"," ",," "," "," "," "," ",',
    #                f'"pos rate","=(SUMIF(B$3:B${num}, "">1"", N$3:N${num}) - SUMIF(B$3:B${num}, "">1"", D$3:D${num})) / (SUMIF(B$3:B${num}, "">1"", N$3:N${num}))","=(SUMIF(C$3:C${num}, "">1"", O$3:O${num}) - SUMIF(C$3:C${num}, "">1"", E$3:E${num})) / (SUMIF(C$3:C${num}, "">1"", O$3:O${num}))"," ",," ","=(SUMIF(G$3:G${num}, "">1"", N$3:N${num}) - SUMIF(G$3:G${num}, "">1"", I$3:I${num})) / (SUMIF(G$3:G${num}, "">1"", N$3:N${num}))","=(SUMIF(H$3:H${num}, "">1"", O$3:O${num}) - SUMIF(H$3:H${num}, "">1"", J$3:J${num})) / (SUMIF(H$3:H${num}, "">1"", O$3:O${num}))"," ",," "," "," "," "," ",',
    #                f'"neg rate","=(SUMIF(B$3:B${num}, ""<-1"", N$3:N${num}) - SUMIF(B$3:B${num}, ""<-1"", D$3:D${num})) / (SUMIF(B$3:B${num}, ""<-1"", N$3:N${num}))","=(SUMIF(C$3:C${num}, ""<-1"", O$3:O${num}) - SUMIF(C$3:C${num}, ""<-1"", E$3:E${num})) / (SUMIF(C$3:C${num}, ""<-1"", O$3:O${num}))"," ",," ","=(SUMIF(G$3:G${num}, ""<-1"", N$3:N${num}) - SUMIF(G$3:G${num}, ""<-1"", I$3:I${num})) / (SUMIF(G$3:G${num}, ""<-1"", N$3:N${num}))","=(SUMIF(H$3:H${num}, ""<-1"", O$3:O${num}) - SUMIF(H$3:H${num}, ""<-1"", J$3:J${num})) / (SUMIF(H$3:H${num}, ""<-1"", O$3:O${num}))"," ",," "," "," "," "," ",'])
    with open(os.path.join(outdir, f"recoder-result-{id}.csv"), "w") as f:
        for line in result:
            f.write(line + "\n")
    print("pos - seapr")
    get_iqr(final_list_pos_seapr)
    print("neg - seapr")
    get_iqr(final_list_neg_seapr)
    if use_group:
        with open(os.path.join(outdir, f"recoder-result-time-{id}.csv"), "w") as f:
            for line in t_result:
                f.write(line + "\n")
        for i in range(50):
            final_list_pos.append(
                (base_pos_iter - pos_dict[i]) / base_pos_iter * 100)
            final_list_neg.append(
                (base_neg_iter - neg_dict[i]) / base_neg_iter * 100)
            final_list_neut.append(
                (base_neut_iter - neut_dict[i]) / base_neut_iter * 100)
        fig = plt.figure(figsize=(3.5, 4))
        print(final_list_pos)
        print(final_list_neg)
        print(final_list_neut)
        # print("pos")
        # get_iqr(final_list_pos)
        # print("neg")
        # get_iqr(final_list_neg)
        plt.boxplot([final_list_pos, final_list_neut, final_list_neg], labels=[
                    'Pos', 'Neut', 'Neg'], showfliers=True, positions=(0.25, 0.5, 0.75), vert=True)
        plt.xlim((0.1, 0.9))
        plt.xticks(fontsize=20)
        plt.yticks(fontsize=20)
        # plt.margins(x=0.1)
        plt.grid()
        plt.savefig(os.path.join(outdir, f"boxplot-{id}.pdf"), bbox_inches='tight')
        plt.savefig(os.path.join(outdir, f"boxplot-{id}.png"), bbox_inches='tight')

if __name__ == "__main__":
    main(sys.argv)
