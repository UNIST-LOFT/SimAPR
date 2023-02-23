from typing import List, Set, Dict, Tuple
import multiprocessing as mp
import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np
from enum import Enum
import math

time_map: Dict[str, float]

class ToolType(Enum):
    recoder = 0
    seapr = 1
    guided = 2

class Group(Enum):
    neg = -1
    neut = 0
    pos = 1
    undefined = 2

plau_time_map_for_plot: Dict[ToolType, Dict[int, float]] = dict()
plau_time_map_for_plot[ToolType.recoder] = dict()
plau_time_map_for_plot[ToolType.seapr] = dict()
plau_time_map_for_plot[ToolType.guided] = dict()


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
    
    def to_str(self) -> str:
        return f"{self.bugid},{self.tool.name},{self.id},{self.has_correct_patch},{self.correct_iter},{self.correct_time},{self.has_plau_patch},{self.plau_iter},{self.plau_time},{self.total_plau}\n"

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
                if is_pass:
                    min = tm // 60
                    if min in plau_time_map_for_plot[self.tool]:
                        plau_time_map_for_plot[self.tool][min] += 1
                    else:
                        plau_time_map_for_plot[self.tool][min] = 1
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
                # self.has_correct_patch = True
            if not self.has_plau_patch:
                self.plau_iter = iter
                self.plau_time = tm
                self.total_plau = 0
                # self.has_plau_patch = True

class ProjectResult:
    def __init__(self, outdir: str, resultdir: str, bugid: str, correct_patches: List[str]):
        self.bugid = bugid
        self.outdir = outdir
        self.resultdir = resultdir
        self.correct_patches = correct_patches
        tmp_file = os.path.join(resultdir, "tmp", f"{bugid}.csv")
        contents = list()
        contents.append("bugid,tool,id,has_correct_patch,correct_iter,correct_time,has_plau_patch,plau_iter,plau_time,total_plau\n")
        self.recoder_result: ToolResult = ToolResult(outdir, resultdir, bugid, 0, ToolType.recoder, correct_patches)
        contents.append(self.recoder_result.to_str())
        self.seapr_result: ToolResult = ToolResult(outdir, resultdir, bugid, 0, ToolType.seapr, correct_patches)
        contents.append(self.seapr_result.to_str())
        self.guided_results: List[ToolResult] = list()
        self.has_correct_patch = len(correct_patches) > 0
        self.guided_group: Group = Group.undefined
        self.seapr_group: Group = Group.undefined
        for i in range(50):
            guided_result = ToolResult(outdir, resultdir, bugid, i, ToolType.guided, correct_patches)
            self.guided_results.append(guided_result)
            contents.append(guided_result.to_str())
        with open(tmp_file, "w") as f:
            f.writelines(contents)

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

def parse_line(line: str) -> Tuple[str, str, str, bool, int, float, bool, int, float, int]:
    bugid,tool,id,has_correct_patch,correct_iter,correct_time,has_plau_patch,plau_iter,plau_time,total_plau = line.split(",")
    gen_time = time_map[bugid]
    return bugid,tool,id,has_correct_patch=="True",int(correct_iter),gen_time+float(correct_time),has_plau_patch=="True",int(plau_iter),gen_time+float(plau_time),int(total_plau)

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

def time_recoder_to_str(line: tuple) -> str:
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
    return f"{has_plau_patch},{has_correct_patch},,,{plau_time},{correct_time},{total_plau}"

def time_seapr_to_str(recoder: tuple, line: tuple) -> str:
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
        plau_impv = "%.4f" % ((recoder_plau_time - plau_time) / recoder_plau_time * 100)
    corr_impv = ""
    if has_correct_patch and recoder_has_correct_patch:
        corr_impv = "%.4f" % ((recoder_correct_time - correct_time) / recoder_correct_time * 100)
    # has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau
    return f"{has_plau_patch},{has_correct_patch},{plau_impv},{corr_impv},{plau_time},{correct_time},{total_plau}"

def time_guided_to_str(recoder: tuple, lines: List[tuple]) -> str:
    recoder_has_correct_patch = recoder[Result.has_correct_patch.value]
    recoder_correct_iter = recoder[Result.correct_iter.value]
    recoder_correct_time = recoder[Result.correct_time.value]
    recoder_has_plau_patch = recoder[Result.has_plau_patch.value]
    recoder_plau_iter = recoder[Result.plau_iter.value]
    recoder_plau_time = recoder[Result.plau_time.value]
    recoder_total_plau = recoder[Result.total_plau.value]

    # num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau    
    num_plau, num_correct = count_guided(lines)
    guided_plau_time = 0
    guided_corr_time = 0
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

def load_bugid(bugid_file: str, bugid: str) -> tuple:
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
    return recoder_result, seapr_result, guided_result

def save_to_table(result_dir: str, bugids: List[str], id: str) -> None:
    iter_result_file = os.path.join(result_dir, f"result-iter-{id}.csv")
    time_result_file = os.path.join(result_dir, f"result-time-{id}.csv")
    with open(iter_result_file, "w") as i, open(time_result_file, "w") as t:
        i.write(",guided,,,,,,,seapr,,,,,,,recoder,,,,,,,group_casino,group_seapr\n")
        i.write(",num_plau,num_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_iter,corr_iter,total_plau\n")
        t.write(",guided,,,,,,,seapr,,,,,,,recoder,,,,,,,group_casino,group_seapr\n")
        t.write(",num_plau,num_corr,plau_impv%,corr_impv%,plau_time,corr_time,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_time,corr_time,total_plau,has_plau,has_corr,plau_impv%,corr_impv%,plau_time,corr_time,total_plau\n")
        for bugid in bugids:
            tmp_file = os.path.join(result_dir, "tmp", bugid + ".csv")
            recoder_result, seapr_result, guided_result = load_bugid(tmp_file, bugid)
            recoder_str = recoder_to_str(recoder_result)
            seapr_str = seapr_to_str(recoder_result, seapr_result)
            guided_str = guided_to_str(recoder_result, guided_result)
            i.write(f"{bugid},{guided_str},{seapr_str},{recoder_str}\n")
            recoder_str = time_recoder_to_str(recoder_result)
            seapr_str = time_seapr_to_str(recoder_result, seapr_result)
            guided_str = time_guided_to_str(recoder_result, guided_result)
            t.write(f"{bugid},{guided_str},{seapr_str},{recoder_str}\n")

def sec_to_min(sec: float) -> int:
    return sec // 60

def time_map_update(line: tuple, map: dict) -> None:
    bugid = line[Result.bugid.value]
    tool = line[Result.tool.value]
    id = line[Result.id.value]
    has_correct_patch = line[Result.has_correct_patch.value]
    correct_iter = line[Result.correct_iter.value]
    correct_time = sec_to_min(line[Result.correct_time.value])
    has_plau_patch = line[Result.has_plau_patch.value]
    plau_iter = line[Result.plau_iter.value]
    plau_time = sec_to_min(line[Result.plau_time.value])
    total_plau = line[Result.total_plau.value]
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

def rank_list(x: list, rank: list, div=1) -> list:
    result = list()
    for r in rank:
        total = 0
        for i in x:
            if i <= r:
                total += 1
        result.append(total / div)
    return result

def save_plau_plot(result_dir: str, id: str = "plot") -> None:
    plau_plot = os.path.join(result_dir, f"plau-{id}.png")
    x = range(300)
    plt.clf()
    fig = plt.figure(figsize=(3.5,4))
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.guided], 50), label="Casino")
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.seapr], 1), label="SeAPR")
    plt.plot(x, time_map_to_list(x, plau_time_map_for_plot[ToolType.recoder], 1), label="Original")    
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.legend(fontsize=13)
    plt.grid()
    plt.savefig(plau_plot, bbox_inches="tight")


def save_to_plot(result_dir: str, bugids: List[str], id: str) -> None:
    rq2_plot = os.path.join(result_dir, f"rq2-{id}.png")
    rq3_plot = os.path.join(result_dir, f"rq3-{id}.png")
    x = range(300)
    rq2_y_guided = dict()
    rq2_y_seapr = dict()
    rq2_y_recoder = dict()
    rq3_y_guided = list()
    rq3_y_seapr = list()
    rq3_y_recoder = list()
    for bugid in bugids:
        tmp_file = os.path.join(result_dir, "tmp", bugid + ".csv")
        recoder_result, seapr_result, guided_result = load_bugid(tmp_file, bugid)
        time_map_update(recoder_result, rq2_y_recoder)
        time_map_update(seapr_result, rq2_y_seapr)
        rq3_y_recoder.append(get_item(recoder_result, Result.total_plau.value))
        rq3_y_seapr.append(get_item(seapr_result, Result.total_plau.value))
        for guided_res in guided_result:
            time_map_update(guided_res, rq2_y_guided)
            rq3_y_guided.append(get_item(guided_res, Result.total_plau.value))
    # RQ2
    plt.clf()
    fig = plt.figure(figsize=(3.5,4))
    plt.plot(x, time_map_to_list(x, rq2_y_guided, 50), label="Casino")
    plt.plot(x, time_map_to_list(x, rq2_y_seapr, 1), label="SeAPR")
    plt.plot(x, time_map_to_list(x, rq2_y_recoder, 1), label="Original")    
    plt.xticks(fontsize=13)
    plt.yticks(fontsize=13)
    plt.legend(fontsize=13)
    plt.grid()
    plt.savefig(rq2_plot, bbox_inches="tight")
    # RQ3
    plt.clf()
    fig = plt.figure(figsize=(4.5,4))
    rank_range = [1, 5, 10]
    x = [1.2, 2.2, 3.2]
    plt.bar([1, 2, 3], rank_list(rq3_y_guided, rank_range, div=50), width=0.2, label="Casino")
    plt.bar([1.2, 2.2, 3.2], rank_list(rq3_y_seapr, rank_range), width=0.2, label="SeAPR")
    plt.bar([1.4, 2.4, 3.4], rank_list(rq3_y_recoder, rank_range), width=0.2, label="Original")
    plt.xticks(x,['First-1','First-5','First-10'],fontsize=13)
    plt.yticks(fontsize=13)
    plt.legend(fontsize=13)
    plt.savefig(rq3_plot, bbox_inches="tight")

def main(args: List[str]) -> None:
    if len(args) < 4:
        print("Usage: gen-result-table.py <recoder-path> <outdir> <id>")
        return
    global time_map
    recoder_path = args[1]
    outdir = args[2]
    id = args[3]
    result_dir = f"{recoder_path}/out-result/{id}"
    os.makedirs(result_dir, exist_ok=True)
    correct_patch_dict = get_correct_patch(os.path.join(recoder_path, "data", "correct_patch.csv"))
    time_map = get_time_map(os.path.join(recoder_path, "data", "time.csv"))
    bugids = get_bugids(os.path.join(recoder_path, "data", "correct_patch.csv"))
    bugids = sort_bugids(bugids)
    if not os.path.exists(result_dir + "/tmp"):
        os.makedirs(result_dir + "/tmp", exist_ok=True)
        total_result = TotalResult(outdir, result_dir, bugids, correct_patch_dict)
        total_result.run()
        save_plau_plot(result_dir)
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
