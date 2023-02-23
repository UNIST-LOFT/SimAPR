import subprocess
import getopt
import sys
import os

def execute_cmd(cmd: list) -> int:
    print(" ".join(cmd))
    result = subprocess.run(cmd)
    return result.returncode

def main(argv):
    if len(argv) < 2:
        print("Usage: python3 alpharepair.py <project>")
        exit(1)
    bugid = argv[1]
    if "_" in bugid:
        bugid = bugid.replace("_", "-")
    cmd = ["python3", 'experiment.py', '--bug_id', bugid, '--output_folder', 'd4j', '--skip_v', '--re_rank', '--beam_width', '5', '--top_n_locations', '40']
    os.chdir("../../AlphaRepair")
    execute_cmd(cmd)

if __name__ == "__main__":
    main(sys.argv)