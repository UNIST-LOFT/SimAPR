import multiprocessing as mp
import subprocess
import os
import sys
from sys import stderr
from time import time
from typing import List, Dict, Set, Tuple


"""
s_1 함수:
c값 2배 증가: c = 2 * (50 + 50^0.5)
c값 2배 감소: c = 1/2 * (50 + 50^0.5)
s_3 함수: 
FL_CONST = 0.125
분모 2배 증가: score_{max}(n) / 8*score_{prev}
FL_CONST = 0.5
분모 2배 감소: score_{max}(n) / 2*score_{prev}
Epsilon-function:
c_1 2배 증가: c_1 = 20
c_1 2배 감소: c_1 = 5
c_2 2배 증가: c_2 = 2/3
c_2 2배 감소: c_2 = 1/6
Strength의 weight:
weight_a = 2, weight_b = 1
weight_a = 1, weight_b = 2
"""
options = ["s_1-1", "s_1-2", "s_3-1", "s_3-2", "c_1-1",
           "c_1-2", "c_2-1", "c_2-2", "strg-1", "strg-2"]
tool_path = sys.argv[1]
name = sys.argv[2]
os.makedirs(f"{tool_path}/out-{name}-params", exist_ok=True)
for opt in options:
  casino_path = os.path.join("/root/project", f"msv-{opt}")
  os.system(f"python3 /root/project/Recoder/script/gen-result-table.py {tool_path} {tool_path}/out-{name}-{opt} {name}-{opt}")
  os.system(f"cp -r {tool_path}/out-{name}-{opt}/tmp {tool_path}/out-{name}-params/{opt}")
os.system(f"tar -zvcf {tool_path}/{name}-params.tar.gz {tool_path}/out-{name}-params")
