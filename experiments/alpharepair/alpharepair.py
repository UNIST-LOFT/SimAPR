import subprocess
import getopt
import sys
import os

def main(argv):
    if len(argv) < 2:
        print("Usage: python3 alpharepair.py <project> [gpu-core]")
        exit(1)

    bugid = argv[1]
    if "_" in bugid:
        bugid = bugid.replace("_", "-")
    print(f"Run AlphaRepair: {bugid}")
    cmd = ["python3", 'experiment.py', '--bug_id', bugid, '--output_folder', 'd4j', '--skip_v', '--re_rank', '--beam_width', '5', '--top_n_locations', '40']

    new_env=os.environ.copy()
    if len(argv) > 2:
        new_env["CUDA_VISIBLE_DEVICES"]=argv[2]
    os.chdir("../../AlphaRepair")
    result=subprocess.run(cmd,env=new_env)
    print(f"AlphaRepair finished bug {bugid} with return code {result.returncode}")
    exit(result.returncode)

if __name__ == "__main__":
    main(sys.argv)