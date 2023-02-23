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
        print("Usage: python3 recoder.py <project>")
        exit(1)
    bugid = argv[1]
    if "_" in bugid:
        bugid = bugid.replace("_", "-")
    cmd = ["python3", 'testDefect4j.py', bugid]
    os.chdir("../../Recoder")
    execute_cmd(cmd)

if __name__ == "__main__":
    main(sys.argv)