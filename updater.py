import subprocess
import os
import time


def updater(q):
    time.sleep(20)
    while True:
        proc = subprocess.Popen('git remote show origin', shell=True, stdout=subprocess.PIPE,)
        output = proc.communicate()[0]
        if "out of date" in output.decode("utf-8"):
            os.system("git pull origin master")
            time.sleep(2)
            q.put(1)
        time.sleep(10)
