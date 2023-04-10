import subprocess
import getopt
import sys
import os

def main(argv):
    if len(argv) < 2:
        print("Usage: python3 recoder.py <project> [gpu-core]")
        exit(1)
    
    bugid = argv[1]
    if "_" in bugid:
        bugid = bugid.replace("_", "-")
    print(f"Run recoder: {bugid}")
    cmd = ["python3", 'testDefect4j.py', bugid]

    new_env=os.environ.copy()
    if len(argv) > 2:
        new_env["CUDA_VISIBLE_DEVICES"]=argv[2]
    os.chdir("../../Recoder")
    result=subprocess.run(cmd,env=new_env)
    if result.returncode != 0:
        print(f"Recoder failed to run recoder {bugid}")
        exit(result.returncode)

    result2=subprocess.run(["python3", "repair.py", bugid],env=new_env)
    if result2.returncode != 0:
        print(f"Recoder failed to generate actual patches {bugid}")
        exit(result2.returncode)
    print(f"Recoder finished bug {bugid} with return code {result.returncode}")
    exit(result.returncode)
    
if __name__ == "__main__":
    main(sys.argv)