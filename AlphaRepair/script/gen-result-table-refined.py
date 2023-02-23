from typing import List, Set, Dict, Tuple
import multiprocessing as mp
import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np
from enum import Enum
import math
import getopt
from sklearn import metrics

NUM_GUIDED = 50

time_map: Dict[str, float]
rank_map: Dict[str, Dict[str, int]]
rank_map_ods: Dict[str, Dict[str, int]]
tool_name: str = ""

class ToolType(Enum):
    recoder = 0
    seapr = 1
    guided = 2
    # bounded_seapr = 3

class Group(Enum):
    neg = -1
    neut = 0
    pos = 1
    undefined = 2

def init_map(map) -> None:
    for tool in ToolType:
        map[tool] = dict()

plau_time_map_for_plot: Dict[ToolType, Dict[int, float]] = dict()
plau_iter_map_for_plot: Dict[ToolType, Dict[int, float]] = dict()
init_map(plau_time_map_for_plot)
init_map(plau_iter_map_for_plot)

corr_time_map_1: Dict[ToolType, Dict[int, float]] = dict()
corr_time_map_5: Dict[ToolType, Dict[int, float]] = dict()
corr_time_map_10: Dict[ToolType, Dict[int, float]] = dict()
init_map(corr_time_map_1)
init_map(corr_time_map_5)
init_map(corr_time_map_10)


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
    def __init__(self, outdir: str, resultdir: str, bugid: str, id: int, tool: ToolType, correct_patches: List[str]):
        self.outdir = outdir
        self.bugid = bugid
        self.tool = tool
        self.id = id
        self.correct_patches = correct_patches
        self.plau_list = list()
        self.plau_iter = -1
        self.plau_time = -1
        self.correct_iter = -1
        self.correct_time = -1
        self.total_plau = -1
        self.org_rank = -1
        self.ods_rank = -1
        self.has_correct_patch = False
        self.has_plau_patch = False
        self.has_result = True
        if tool == ToolType.guided:
            self.run(f"{outdir}/{bugid}-guided-{id}")
        # elif tool == ToolType.bounded_seapr:
        #     self.run(f"{outdir}/{bugid}-bounded-seapr")
        else:
            self.run(f"{outdir}/{bugid}-{tool.name}")
    
    def to_str(self) -> str:
        return f"{self.bugid},{self.tool.name},{self.id},{self.has_correct_patch},{self.correct_iter},{self.correct_time},{self.has_plau_patch},{self.plau_iter},{self.plau_time},{self.total_plau}\n"

    def to_json_obj(self) -> Dict[str, any]:
        obj = dict()
        obj["bugid"] = self.bugid
        obj["tool"] = self.tool.name
        obj["id"] = self.id
        obj["has_correct_patch"] = self.has_correct_patch
        obj["correct_iter"] = self.correct_iter
        obj["correct_time"] = self.correct_time
        obj["has_plau_patch"] = self.has_plau_patch
        obj["plau_iter"] = self.plau_iter
        obj["plau_time"] = self.plau_time
        obj["total_plau"] = self.total_plau
        obj["org_rank"] = self.org_rank
        obj["ods_rank"] = self.ods_rank
        obj["plau_list"] = self.plau_list
        return obj

    def get_iter_time(self, plau_list) -> tuple:
        iter = -1
        tm = -1
        rank = 0
        for elem in plau_list:
            rank += 1
            id = elem["id"]
            if id in self.correct_patches:
                iter = elem["iteration"]
                tm = elem["time"]
                break
        return iter, tm, rank

    def get_rank_by_time(self, plau_list, tm: int) -> int:
        rank = 0
        for elem in plau_list:
            min = elem["time"] // 60
            id = elem["id"]
            if min <= tm:
                rank += 1
                if id in self.correct_patches:
                    return rank
        return rank
    
    def update_corr_time_map(self, plau_list) -> None:
        for i in range(301):
            rank = self.get_rank_by_time(plau_list, i)
            if rank == 0:
                continue
            if rank <= 1:
                if i not in corr_time_map_1[self.tool]:
                    corr_time_map_1[self.tool][i] = 0
                corr_time_map_1[self.tool][i] += 1
            if rank <= 5:
                if i not in corr_time_map_5[self.tool]:
                    corr_time_map_5[self.tool][i] = 0
                corr_time_map_5[self.tool][i] += 1
            if rank <= 10:
                if i not in corr_time_map_10[self.tool]:
                    corr_time_map_10[self.tool][i] = 0
                corr_time_map_10[self.tool][i] += 1
    
    def sort_by_ranking(self):
        def sort_func(x):
            if x["id"] not in rank_map[self.bugid]:
                return 100000
            return rank_map[self.bugid][x["id"]]["rank"]
        def ods_sort_func(x):
            if x["id"] not in rank_map_ods[self.bugid]:
                return 100000
            return rank_map_ods[self.bugid][x["id"]]["rank"]
        self.plau_list.sort(key=lambda x: sort_func(x))
        iter, tm, rank = self.get_iter_time(self.plau_list)
        self.org_rank = rank
        self.plau_list.sort(key=lambda x: ods_sort_func(x))
        iter_ods, tm_ods, rank_ods = self.get_iter_time(self.plau_list)
        self.ods_rank = rank_ods
        self.update_corr_time_map(self.plau_list)

    def run(self, target_dir: str):
        global plau_time_map_for_plot
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
                if is_pass:
                    self.plau_list.append({"id": patch_id, "location": patch_loc, "time": tm, "iteration": iter})
                    min = tm // 60
                    if min not in plau_time_map_for_plot[self.tool]:
                        plau_time_map_for_plot[self.tool][min] = 0
                    plau_time_map_for_plot[self.tool][min] += 1
                    if iter not in plau_iter_map_for_plot[self.tool]:
                        plau_iter_map_for_plot[self.tool][iter] = 0
                    plau_iter_map_for_plot[self.tool][iter] += 1
                    if not self.has_correct_patch:
                        self.total_plau += 1
                    if not self.has_plau_patch:
                        self.plau_iter = iter
                        self.plau_time = tm
                        self.has_plau_patch = True
                if patch_id in self.correct_patches:
                    if not self.has_correct_patch:
                        self.correct_iter = iter
                        self.correct_time = tm
                        self.has_correct_patch = True
            # Hack: if no correct patch, set the correct iter to the last iter
            if not self.has_correct_patch:
                self.correct_iter = iter
                self.correct_time = tm
            if not self.has_plau_patch:
                self.plau_iter = iter
                self.plau_time = tm
                self.total_plau = 0
            self.sort_by_ranking()

class ProjectResult:
    def __init__(self, outdir: str, resultdir: str, bugid: str, correct_patches: List[str]):
        self.bugid = bugid
        self.outdir = outdir
        self.resultdir = resultdir
        self.correct_patches = correct_patches
        tmp_file = os.path.join(resultdir, "tmp", f"{bugid}.csv")
        tmp_json_file = os.path.join(resultdir, "tmp", f"{bugid}.json")
        contents = list()
        contents.append("bugid,tool,id,has_correct_patch,correct_iter,correct_time,has_plau_patch,plau_iter,plau_time,total_plau\n")
        self.recoder_result: ToolResult = ToolResult(outdir, resultdir, bugid, 0, ToolType.recoder, correct_patches)
        contents.append(self.recoder_result.to_str())
        self.seapr_result: ToolResult = ToolResult(outdir, resultdir, bugid, 0, ToolType.seapr, correct_patches)
        # self.bounded_seapr_result: ToolResult = ToolResult(outdir, resultdir, bugid, 0, ToolType.bounded_seapr, correct_patches)
        contents.append(self.seapr_result.to_str())
        self.guided_results: List[ToolResult] = list()
        self.has_correct_patch = len(correct_patches) > 0
        self.guided_group: Group = Group.undefined
        self.seapr_group: Group = Group.undefined
        for i in range(NUM_GUIDED):
            guided_result = ToolResult(outdir, resultdir, bugid, i, ToolType.guided, correct_patches)
            self.guided_results.append(guided_result)
            contents.append(guided_result.to_str())
        with open(tmp_file, "w") as f:
            f.writelines(contents)
        with open(tmp_json_file, "w") as f:
            json.dump(self.to_json_obj(), f, indent=2)
    def to_json_obj(self) -> list:
        obj = list()
        obj.append(self.recoder_result.to_json_obj())
        obj.append(self.seapr_result.to_json_obj())
        # obj.append(self.bounded_seapr_result.to_json_obj())
        for guided_result in self.guided_results:
            obj.append(guided_result.to_json_obj())
        return obj
    
class TotalResult:
    def __init__(self, outdir: str, resultdir: str, bugids: List[str], correct_patch_dict: Dict[str, List[str]]):
        self.outdir = outdir
        self.resultdir = resultdir
        self.bugids = bugids
        self.correct_patch_dict = correct_patch_dict
        self.result: Dict[str, ProjectResult] = dict()
    
    def run(self):
        # Analyze result
        for bugid in self.bugids:
            correct_patch = list()
            if bugid in self.correct_patch_dict:
                correct_patch = self.correct_patch_dict[bugid]
            self.result[bugid] = ProjectResult(self.outdir, self.resultdir, bugid, correct_patch)
            
def get_rank_map(rank_file: str) -> Dict[str, dict]:
    with open(rank_file, "r") as f:
        root = json.load(f)
        return root

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

def get_time_map(time_file: str) -> Dict[str, float]:
    time_map = dict()
    with open(time_file, "r") as f:
        for line in f:
            line = line.strip()
            if len(line) == 0 or line.startswith("#"):
                continue
            bugid, time = line.split(",")
            time_map[bugid] = float(time)
    return time_map

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
    org_rank = 10
    ods_rank = 11

def parse_line(line: str) -> Tuple[str, str, str, bool, int, float, bool, int, float, int, int, int]:
    bugid,tool,id,has_correct_patch,correct_iter,correct_time,has_plau_patch,plau_iter,plau_time,total_plau = line.split(",")
    gen_time = time_map[bugid]
    rank_org,rank_ods = 0, 0
    return bugid,tool,id,has_correct_patch=="True",int(correct_iter),gen_time+float(correct_time),has_plau_patch=="True",int(plau_iter),gen_time+float(plau_time),int(total_plau),int(rank_org),int(rank_ods)

def count_guided(lines: List[tuple]) -> tuple:
    num_correct = 0
    num_plau = 0
    for line in lines:
        has_correct_patch = line[Result.has_correct_patch.name]
        has_plau_patch = line[Result.has_plau_patch.name]
        if has_correct_patch:
            num_correct += 1
        if has_plau_patch:
            num_plau += 1
    return num_plau, num_correct

def recoder_to_str(line: tuple, is_time: bool = False) -> str:
    bugid = line[Result.bugid.name]
    tool = line[Result.tool.name]
    id = line[Result.id.name]
    has_correct_patch = line[Result.has_correct_patch.name]
    correct_iter = line[Result.correct_iter.name]
    correct_time = line[Result.correct_time.name]
    has_plau_patch = line[Result.has_plau_patch.name]
    plau_iter = line[Result.plau_iter.name]
    plau_time = line[Result.plau_time.name]
    total_plau = line[Result.total_plau.name]
    org_rank = line[Result.org_rank.name]
    ods_rank = line[Result.ods_rank.name]
    # has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau
    if is_time:
        return f"{has_plau_patch},{has_correct_patch},,,{plau_time},{correct_time},{total_plau},{org_rank},{ods_rank}"
    return f"{has_plau_patch},{has_correct_patch},,,{plau_iter},{correct_iter},{total_plau},{org_rank},{ods_rank}"

def seapr_to_str(recoder: tuple, line: tuple, is_time: bool = False) -> str:
    recoder_tool = recoder[Result.tool.name]
    recoder_id = recoder[Result.id.name]
    recoder_has_correct_patch = recoder[Result.has_correct_patch.name]
    recoder_correct_iter = recoder[Result.correct_iter.name]
    recoder_correct_time = recoder[Result.correct_time.name]
    recoder_has_plau_patch = recoder[Result.has_plau_patch.name]
    recoder_plau_iter = recoder[Result.plau_iter.name]
    recoder_plau_time = recoder[Result.plau_time.name]
    recoder_total_plau = recoder[Result.total_plau.name]
    # seapr
    tool = line[Result.tool.name]
    id = line[Result.id.name]
    has_correct_patch = line[Result.has_correct_patch.name]
    correct_iter = line[Result.correct_iter.name]
    correct_time = line[Result.correct_time.name]
    has_plau_patch = line[Result.has_plau_patch.name]
    plau_iter = line[Result.plau_iter.name]
    plau_time = line[Result.plau_time.name]
    total_plau = line[Result.total_plau.name]
    org_rank = line[Result.org_rank.name]
    ods_rank = line[Result.ods_rank.name]
    plau_impv = ""
    corr_impv = ""
    if is_time:
        if has_plau_patch and recoder_has_plau_patch:
            plau_impv = "%.4f" % ((recoder_plau_time - plau_time) / recoder_plau_time * 100)
        if has_correct_patch and recoder_has_correct_patch:
            corr_impv = "%.4f" % ((recoder_correct_time - correct_time) / recoder_correct_time * 100)
        return f"{has_plau_patch},{has_correct_patch},{plau_impv},{corr_impv},{plau_time},{correct_time},{total_plau},{org_rank},{ods_rank}"
    
    if has_plau_patch and recoder_has_plau_patch:
        plau_impv = "%.4f" % ((recoder_plau_iter - plau_iter) / recoder_plau_iter * 100)
    if has_correct_patch and recoder_has_correct_patch:
        corr_impv = "%.4f" % ((recoder_correct_iter - correct_iter) / recoder_correct_iter * 100)
    # has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau
    return f"{has_plau_patch},{has_correct_patch},{plau_impv},{corr_impv},{plau_iter},{correct_iter},{total_plau},{org_rank},{ods_rank}"

def guided_to_str(recoder: tuple, lines: List[tuple], is_time: bool = False) -> str:
    recoder_has_correct_patch = recoder[Result.has_correct_patch.name]
    recoder_correct_iter = recoder[Result.correct_iter.name]
    recoder_correct_time = recoder[Result.correct_time.name]
    recoder_has_plau_patch = recoder[Result.has_plau_patch.name]
    recoder_plau_iter = recoder[Result.plau_iter.name]
    recoder_plau_time = recoder[Result.plau_time.name]
    recoder_total_plau = recoder[Result.total_plau.name]

    # num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau    
    num_plau, num_correct = count_guided(lines)
    guided_plau_iter = 0
    guided_corr_iter = 0
    guided_total_plau = 0
    guided_org_rank = 0
    guided_ods_rank = 0
    guided_plau_time = 0
    guided_corr_time = 0
    n = len(lines)
    for line in lines:
        has_correct_patch = line[Result.has_correct_patch.name]
        correct_iter = line[Result.correct_iter.name]
        correct_time = line[Result.correct_time.name]
        has_plau_patch = line[Result.has_plau_patch.name]
        plau_iter = line[Result.plau_iter.name]
        plau_time = line[Result.plau_time.name]
        total_plau = line[Result.total_plau.name]
        org_rank = line[Result.org_rank.name]
        ods_rank = line[Result.ods_rank.name]
        guided_plau_iter += plau_iter
        guided_corr_iter += correct_iter
        guided_plau_time += plau_time
        guided_corr_time += correct_time
        guided_total_plau += total_plau
        guided_org_rank += org_rank
        guided_ods_rank += ods_rank
    guided_plau_iter /= n
    guided_corr_iter /= n
    guided_plau_time /= n
    guided_corr_time /= n
    guided_total_plau /= n
    guided_org_rank /= n
    guided_ods_rank /= n
    corr_impv = ""
    plau_impv = ""
    if is_time:
        if num_correct > 0 and recoder_has_correct_patch:
            corr_impv = "%.4f" % ((recoder_correct_time - guided_corr_time) / recoder_correct_time * 100)
        if num_plau > 0 and recoder_has_plau_patch:
            plau_impv = "%.4f" % ((recoder_plau_time - guided_plau_time) / recoder_plau_time * 100)
        return f"{num_plau},{num_correct},{plau_impv},{corr_impv},{guided_plau_time},{guided_corr_time},{guided_total_plau},{guided_org_rank},{guided_ods_rank}"
    if num_correct > 0 and recoder_has_correct_patch:
        corr_impv = "%.4f" % ((recoder_correct_iter - guided_corr_iter) / recoder_correct_iter * 100)
    if num_plau > 0 and recoder_has_plau_patch:
        plau_impv = "%.4f" % ((recoder_plau_iter - guided_plau_iter) / recoder_plau_iter * 100)
    return f"{num_plau},{num_correct},{plau_impv},{corr_impv},{guided_plau_iter},{guided_corr_iter},{guided_total_plau},{guided_org_rank},{guided_ods_rank}"

def time_recoder_to_str(line: tuple) -> str:
    bugid = line[Result.bugid.name]
    tool = line[Result.tool.name]
    id = line[Result.id.name]
    has_correct_patch = line[Result.has_correct_patch.name]
    correct_iter = line[Result.correct_iter.name]
    correct_time = line[Result.correct_time.name]
    has_plau_patch = line[Result.has_plau_patch.name]
    plau_iter = line[Result.plau_iter.name]
    plau_time = line[Result.plau_time.name]
    total_plau = line[Result.total_plau.name]
    # has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau
    return f"{has_plau_patch},{has_correct_patch},,,{plau_time},{correct_time},{total_plau}"

def time_seapr_to_str(recoder: tuple, line: tuple) -> str:
    recoder_tool = recoder[Result.tool.name]
    recoder_id = recoder[Result.id.name]
    recoder_has_correct_patch = recoder[Result.has_correct_patch.name]
    recoder_correct_iter = recoder[Result.correct_iter.name]
    recoder_correct_time = recoder[Result.correct_time.name]
    recoder_has_plau_patch = recoder[Result.has_plau_patch.name]
    recoder_plau_iter = recoder[Result.plau_iter.name]
    recoder_plau_time = recoder[Result.plau_time.name]
    recoder_total_plau = recoder[Result.total_plau.name]
    # seapr
    tool = line[Result.tool.name]
    id = line[Result.id.name]
    has_correct_patch = line[Result.has_correct_patch.name]
    correct_iter = line[Result.correct_iter.name]
    correct_time = line[Result.correct_time.name]
    has_plau_patch = line[Result.has_plau_patch.name]
    plau_iter = line[Result.plau_iter.name]
    plau_time = line[Result.plau_time.name]
    total_plau = line[Result.total_plau.name]
    plau_impv = ""
    if has_plau_patch and recoder_has_plau_patch:
        plau_impv = "%.4f" % ((recoder_plau_time - plau_time) / recoder_plau_time * 100)
    corr_impv = ""
    if has_correct_patch and recoder_has_correct_patch:
        corr_impv = "%.4f" % ((recoder_correct_time - correct_time) / recoder_correct_time * 100)
    # has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau
    return f"{has_plau_patch},{has_correct_patch},{plau_impv},{corr_impv},{plau_time},{correct_time},{total_plau}"

def time_guided_to_str(recoder: tuple, lines: List[tuple]) -> str:
    recoder_has_correct_patch = recoder[Result.has_correct_patch.name]
    recoder_correct_iter = recoder[Result.correct_iter.name]
    recoder_correct_time = recoder[Result.correct_time.name]
    recoder_has_plau_patch = recoder[Result.has_plau_patch.name]
    recoder_plau_iter = recoder[Result.plau_iter.name]
    recoder_plau_time = recoder[Result.plau_time.name]
    recoder_total_plau = recoder[Result.total_plau.name]

    # num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau    
    num_plau, num_correct = count_guided(lines)
    guided_plau_time = 0
    guided_corr_time = 0
    guided_total_plau = 0
    n = len(lines)
    for line in lines:
        has_correct_patch = line[Result.has_correct_patch.name]
        correct_iter = line[Result.correct_iter.name]
        correct_time = line[Result.correct_time.name]
        has_plau_patch = line[Result.has_plau_patch.name]
        plau_iter = line[Result.plau_iter.name]
        plau_time = line[Result.plau_time.name]
        total_plau = line[Result.total_plau.name]
        guided_plau_time += plau_time
        guided_corr_time += correct_time
        guided_total_plau += total_plau
    guided_plau_time /= n
    guided_corr_time /= n
    guided_total_plau /= n
    corr_impv = ""
    if num_correct > 0 and recoder_has_correct_patch:
        corr_impv = "%.4f" % ((recoder_correct_time - guided_corr_time) / recoder_correct_time * 100)
    plau_impv = ""
    if num_plau > 0 and recoder_has_plau_patch:
        plau_impv = "%.4f" % ((recoder_plau_time - guided_plau_time) / recoder_plau_time * 100)
    return f"{num_plau},{num_correct},{plau_impv},{corr_impv},{guided_plau_time},{guided_corr_time},{guided_total_plau}"

def load_bugid(bugid_file: str, bugid: tuple) -> tuple:
    recoder_result = None
    seapr_result = None
    guided_result = list()
    with open(bugid_file, "r") as f:
        print(bugid_file)
        results = json.load(f)
        for res in results:
            if res[Result.tool.name] == "recoder":
                recoder_result = res
            elif res[Result.tool.name] == 'seapr':
                seapr_result = res
            # elif res[Result.tool.name] == "bounded_seapr":
            #     seapr_result = res
            #     pass
            elif res[Result.tool.name] == "guided":
                guided_result.append(res)
    "bugid,num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau\n"
    return recoder_result, seapr_result, guided_result

def tuple_to_str(tup: tuple) -> str:
    return ",".join([str(x) for x in tup])

def save_to_table(result_dir: str, bugids: List[str], id: str) -> None:
    iter_result_file = os.path.join(result_dir, f"{tool_name}-result-iter-{id}.csv")
    time_result_file = os.path.join(result_dir, f"{tool_name}-result-time-{id}.csv")
    guided_col_tup = ("guided", "", "", "", "", "", "", "", "")
    seapr_col_tup = ("seapr", "", "", "", "", "", "", "", "")
    recoder_col_tup = (tool_name, "", "", "", "", "", "", "", "")
    guided_tup = ('num_plau','num_corr','plau_impv%','corr_impv%','plau_iter','corr_iter','total_plau', 'org_rank', 'ods_rank')
    seapr_tup = ('has_plau','has_corr','plau_impv%','corr_impv%','plau_iter','corr_iter','total_plau', 'org_rank', 'ods_rank')
    guided_tup_tm = ('num_plau','num_corr','plau_impv%','corr_impv%','plau_time','corr_time','total_plau', 'org_rank', 'ods_rank')
    seapr_tup_tm = ('has_plau','has_corr','plau_impv%','corr_impv%','plau_time','corr_time','total_plau', 'org_rank', 'ods_rank')
    with open(iter_result_file, "w") as i, open(time_result_file, "w") as t:
        i.write(f",{tuple_to_str(guided_col_tup)},{tuple_to_str(seapr_col_tup)},{tuple_to_str(recoder_col_tup)}\n")
        i.write(f",{tuple_to_str(guided_tup)},{tuple_to_str(seapr_tup)},{tuple_to_str(seapr_tup)}\n")
        t.write(f",{tuple_to_str(guided_col_tup)},{tuple_to_str(seapr_col_tup)},{tuple_to_str(recoder_col_tup)}\n")
        t.write(f",{tuple_to_str(guided_tup_tm)},{tuple_to_str(seapr_tup_tm)},{tuple_to_str(seapr_tup_tm)}\n")
        # i.write(",guided,,,,,,,seapr,,,,,,,recoder,,,,,,,group_casino,group_seapr\n")
        # i.write(",num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau\n")
        # t.write(",guided,,,,,,,seapr,,,,,,,recoder,,,,,,,group_casino,group_seapr\n")
        # t.write(",num_plau,num_corr,plau_impv%,corr_impv%,plau_time,corr_time,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_time,corr_time,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_time,corr_time,total_plau\n")
        for bugid in bugids:
            tmp_file = os.path.join(result_dir, "tmp", bugid + ".json")
            recoder_result, seapr_result, guided_result = load_bugid(tmp_file, bugid)
            recoder_str = recoder_to_str(recoder_result)
            seapr_str = seapr_to_str(recoder_result, seapr_result)
            guided_str = guided_to_str(recoder_result, guided_result)
            i.write(f"{bugid},{guided_str},{seapr_str},{recoder_str}\n")
            recoder_str = recoder_to_str(recoder_result, True)
            seapr_str = seapr_to_str(recoder_result, seapr_result, True)
            guided_str = guided_to_str(recoder_result, guided_result, True)
            t.write(f"{bugid},{guided_str},{seapr_str},{recoder_str}\n")

def sec_to_min(sec: float) -> int:
    return sec // 60

def time_map_update(line: tuple, map: dict) -> None:
    bugid = line[Result.bugid.name]
    tool = line[Result.tool.name]
    id = line[Result.id.name]
    has_correct_patch = line[Result.has_correct_patch.name]
    correct_iter = line[Result.correct_iter.name]
    correct_time = sec_to_min(line[Result.correct_time.name])
    has_plau_patch = line[Result.has_plau_patch.name]
    plau_iter = line[Result.plau_iter.name]
    plau_time = sec_to_min(line[Result.plau_time.name])
    total_plau = line[Result.total_plau.name]
    if has_correct_patch:
        if correct_time in map:
            map[correct_time] += 1
        else:
            map[correct_time] = 1

def get_item(line: tuple, index: int):
    if index < len(line):
        return line[index]
    else:
        return ""

def time_map_to_list(x: list, map: dict, div: int = 1) -> List[int]:
    y = list()
    total = 0
    for i in x:
        if i in map:
            total += map[i]
        y.append(total)
    for i in range(len(y)):
        y[i] = y[i] / div
    return y

def rank_map_to_list(x: list, map: dict, div: int = 1) -> List[int]:
    y = list()
    for i in x:
        if i in map:
            y.append(map[i] / div)
        else:
            y.append(0)
    return y

def rank_list(x: list, rank: list, div=1) -> list:
    result = list()
    for r in rank:
        total = 0
        for i in x:
            if i <= r:
                total += 1
        result.append(total / div)
    return result

def save_plau_plot(result_dir: str, id: str) -> None:
    plau_plot_time = os.path.join(result_dir, f"{tool_name}-plau-time-{id}.pdf")
    x = range(301)
    plt.clf()
    fig = plt.figure(figsize=(4,3))
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.recoder], 1), label=tool_name, markersize=5, markevery=15, color="b", marker="^")    
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.guided], NUM_GUIDED), label="Casino", markersize=5, markevery=15, color="r", marker="s")
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.seapr], 1), label="SeAPR", markersize=5, markevery=15, color="g", marker="p")
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.xlabel("Time (min)", fontsize=13)
    plt.ylabel("# of Valid Patches", fontsize=13)
    plt.legend(fontsize=13)
    # plt.grid()
    plt.savefig(plau_plot_time, bbox_inches="tight")

    print(f"recoder: {metrics.auc(list(x), time_map_to_list(x, plau_time_map_for_plot[ToolType.recoder], 1))}")
    print(f"guided: {metrics.auc(list(x), time_map_to_list(x, plau_time_map_for_plot[ToolType.guided], NUM_GUIDED))}")
    print(f"seapr: {metrics.auc(list(x), time_map_to_list(x, plau_time_map_for_plot[ToolType.seapr], 1))}")

    plau_plot_time = os.path.join(result_dir, f"{tool_name}-plau-time-1h-{id}.pdf")
    x = range(61)
    plt.clf()
    fig = plt.figure(figsize=(4,3))
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.recoder], 1), label=tool_name, markersize=5, markevery=3, color="b", marker="^")    
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.guided], NUM_GUIDED), label="Casino", markersize=5, markevery=3, color="r", marker="s")
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.seapr], 1), label="SeAPR", markersize=5, markevery=3, color="g", marker="p")
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.xlabel("Time (min)", fontsize=13)
    plt.ylabel("# of Valid Patches", fontsize=13)
    plt.legend(fontsize=13)
    # plt.grid()
    plt.savefig(plau_plot_time, bbox_inches="tight")

    plau_plot_iter = os.path.join(result_dir, f"{tool_name}-plau-iter-{id}.pdf")
    x = range(1001)
    plt.clf()
    fig = plt.figure(figsize=(4,3))
    plt.plot(x, time_map_to_list(x, plau_iter_map_for_plot[ToolType.recoder], 1), label=tool_name, markersize=5, markevery=50, color="b", marker="^")    
    plt.plot(x, time_map_to_list(x, plau_iter_map_for_plot[ToolType.guided], NUM_GUIDED), label="Casino", markersize=5, markevery=50, color="r", marker="s")
    plt.plot(x, time_map_to_list(x, plau_iter_map_for_plot[ToolType.seapr], 1), label="SeAPR", markersize=5, markevery=50, color="g", marker="p")
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.xlabel("Iteration", fontsize=13)
    plt.ylabel("# of Valid Patches", fontsize=13)
    plt.legend(fontsize=13)
    # plt.grid()
    plt.savefig(plau_plot_iter, bbox_inches="tight")

def save_rank_plot(result_dir: str, id: str) -> None:
    plau_plot = os.path.join(result_dir, f"{tool_name}-rank-{id}.pdf")
    rank_plot_1 = os.path.join(result_dir, f"{tool_name}-rank-1-{id}.pdf")
    rank_plot_5 = os.path.join(result_dir, f"{tool_name}-rank-5-{id}.pdf")
    rank_plot_10 = os.path.join(result_dir, f"{tool_name}-rank-10-{id}.pdf")
    x = range(301)
    plt.clf()
    fig = plt.figure(figsize=(4,3))
    plt.plot(x, rank_map_to_list(x, corr_time_map_1[ToolType.guided], NUM_GUIDED), label="Top-1", markersize=5, markevery=15, color="b", marker="^")    
    plt.plot(x, rank_map_to_list(x, corr_time_map_5[ToolType.guided], NUM_GUIDED), label="Top-5", markersize=5, markevery=15, color="r", marker="s")
    plt.plot(x, rank_map_to_list(x, corr_time_map_10[ToolType.guided], NUM_GUIDED), label="Top-10", markersize=5, markevery=15, color="g", marker="p")
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.xlabel("Time (min)", fontsize=13)
    plt.ylabel("# of Versions", fontsize=13)
    plt.legend(fontsize=13)
    # plt.grid()
    plt.savefig(plau_plot, bbox_inches="tight")
    plt.clf()
    fig = plt.figure(figsize=(4,3))
    plt.plot(x, rank_map_to_list(x, corr_time_map_1[ToolType.recoder], 1), label=tool_name, markersize=5, markevery=15, color="b", marker="^")    
    plt.plot(x, rank_map_to_list(x, corr_time_map_1[ToolType.guided], NUM_GUIDED), label="Casino", markersize=5, markevery=15, color="r", marker="s")
    plt.plot(x, rank_map_to_list(x, corr_time_map_1[ToolType.seapr], 1), label="SeAPR", markersize=5, markevery=15, color="g", marker="p")
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.xlabel("Time (min)", fontsize=13)
    plt.ylabel("# of Versions", fontsize=13)
    plt.legend(fontsize=13)
    # plt.grid()
    plt.savefig(rank_plot_1, bbox_inches="tight")
    plt.clf()
    fig = plt.figure(figsize=(4,3))
    plt.plot(x, rank_map_to_list(x, corr_time_map_5[ToolType.recoder], 1), label=tool_name, markersize=5, markevery=15, color="b", marker="^")    
    plt.plot(x, rank_map_to_list(x, corr_time_map_5[ToolType.guided], NUM_GUIDED), label="Casino", markersize=5, markevery=15, color="r", marker="s")
    plt.plot(x, rank_map_to_list(x, corr_time_map_5[ToolType.seapr], 1), label="SeAPR", markersize=5, markevery=15, color="g", marker="p")
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.xlabel("Time (min)", fontsize=13)
    plt.ylabel("# of Versions", fontsize=13)
    plt.legend(fontsize=13)
    # plt.grid()
    plt.savefig(rank_plot_5, bbox_inches="tight")
    plt.clf()
    fig = plt.figure(figsize=(4,3))
    plt.plot(x, rank_map_to_list(x, corr_time_map_10[ToolType.recoder], 1), label=tool_name, markersize=5, markevery=15, color="b", marker="^")    
    plt.plot(x, rank_map_to_list(x, corr_time_map_10[ToolType.guided], NUM_GUIDED), label="Casino", markersize=5, markevery=15, color="r", marker="s")
    plt.plot(x, rank_map_to_list(x, corr_time_map_10[ToolType.seapr], 1), label="SeAPR", markersize=5, markevery=15, color="g", marker="p")
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.xlabel("Time (min)", fontsize=13)
    plt.ylabel("# of Versions", fontsize=13)
    plt.legend(fontsize=13)
    # plt.grid()
    plt.savefig(rank_plot_10, bbox_inches="tight")

def save_to_plot(result_dir: str, bugids: List[str], id: str) -> None:
    rq2_plot = os.path.join(result_dir, f"{tool_name}-rq2-{id}.pdf")
    x = range(301)
    rq2_y_guided = dict()
    rq2_y_seapr = dict()
    rq2_y_recoder = dict()
    rq3_y_guided = list()
    rq3_y_seapr = list()
    rq3_y_recoder = list()
    for bugid in bugids:
        tmp_file = os.path.join(result_dir, "tmp", bugid + ".json")
        recoder_result, seapr_result, guided_result = load_bugid(tmp_file, bugid)
        time_map_update(recoder_result, rq2_y_recoder)
        time_map_update(seapr_result, rq2_y_seapr)
        rq3_y_recoder.append(recoder_result[Result.ods_rank.name])
        rq3_y_seapr.append(seapr_result[Result.ods_rank.name])
        for guided_res in guided_result:
            time_map_update(guided_res, rq2_y_guided)
            rq3_y_guided.append(guided_res[Result.ods_rank.name])
    # RQ2
    plt.clf()
    fig = plt.figure(figsize=(4,3))
    plt.plot(x, time_map_to_list(x, rq2_y_recoder, 1), label=tool_name, markersize=5, markevery=15, color="b", marker="^")   
    plt.plot(x, time_map_to_list(x, rq2_y_guided, NUM_GUIDED), label="Casino", markersize=5, markevery=15, color="r", marker="s")
    plt.plot(x, time_map_to_list(x, rq2_y_seapr, 1), label="SeAPR", markersize=5, markevery=15, color="g", marker="p")
    plt.xticks(fontsize=13)
    plt.xlabel("Time (min)", fontsize=13)
    plt.ylabel("# of Versions", fontsize=13)
    plt.yticks(fontsize=13)
    plt.legend(fontsize=13)
    # plt.grid()
    plt.savefig(rq2_plot, bbox_inches="tight")
    # RQ3
    # plt.clf()
    # fig = plt.figure(figsize=(4.5,4))
    # rank_range = [1, 5, 10]
    # x = [1.2, 2.2, 3.2]
    # # plt.bar([1.4, 2.4, 3.4], rank_list(rq3_y_recoder, rank_range), width=0.2, label=tool_name, markersize=5, markevery=2, color="b", marker="v")
    # # plt.bar([1, 2, 3], rank_list(rq3_y_guided, rank_range, div=NUM_GUIDED), width=0.2, label="Casino", markersize=5, markevery=2, color="r", marker="^")
    # # plt.bar([1.2, 2.2, 3.2], rank_list(rq3_y_seapr, rank_range), width=0.2, label="SeAPR", markersize=5, markevery=2, color="g", marker="p")
    # plt.xticks(x,['First-1','First-5','First-10'],fontsize=13)
    # plt.yticks(fontsize=13)
    # plt.legend(fontsize=13)
    # plt.savefig(rq3_plot, bbox_inches="tight")

def main(args: List[str]) -> None:
    opts, args = getopt.getopt(args[1:], "rah")
    refresh = True
    global tool_name
    tool_name = "Recoder"
    for o, a in opts:
        if o == "-a":
            tool_name = "AlphaRepair"
        elif o == "-r":
            refresh = False
        elif o == "-h":
            print("Usage: gen-result-table.py [-r] <recoder-path> <outdir> <id>")
            return
    if len(args) < 3:
        print("Usage: gen-result-table.py <recoder-path> <outdir> <id>")
        return
    global time_map, rank_map, rank_map_ods
    recoder_path = args[0]
    outdir = args[1]
    id = args[2]
    result_dir = f"{recoder_path}/out-result/{id}"
    os.makedirs(result_dir, exist_ok=True)
    correct_patch_dict = get_correct_patch(os.path.join(recoder_path, "data", "likely_correct.csv"))
    time_map = get_time_map(os.path.join(recoder_path, "data", "time.csv"))
    rank_map = get_rank_map(os.path.join(recoder_path, "data", "rank_map.json"))
    rank_map_ods = get_rank_map(os.path.join(recoder_path, "data", "rank_map_ods.json"))
    bugids = get_bugids(os.path.join(recoder_path, "data", "likely_correct.csv"))
    bugids = sort_bugids(bugids)
    if refresh or not os.path.exists(result_dir + "/tmp"):
        os.makedirs(result_dir + "/tmp", exist_ok=True)
        total_result = TotalResult(outdir, result_dir, bugids, correct_patch_dict)
        total_result.run()
        save_plau_plot(result_dir, id)
        save_rank_plot(result_dir, id)
    # read results from intermediate file and analyze them
    save_to_table(result_dir, bugids, id)
    save_to_plot(result_dir, bugids, id)


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

if __name__ == "__main__":
    main(sys.argv)
