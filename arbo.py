import os
import queue
import sys
import time
from threading import Thread

import requests
from colorama import Fore, Style

import logic
import updater


f = open("version", "r")
ver = f.read()
if ver != str(requests.get("https://api.github.com/repos/701789262a/arbobotti/tags").json()[0]["name"]):
    print(f"{Fore.MAGENTA}[!] NEW VERSION AVAILABLE %s, CURRENT: %s {Style.RESET_ALL}" % (
        str(requests.get("https://api.github.com/repos/701789262a/arbobotti/tags").json()[0]["name"]), ver))
    time.sleep(3)
    f.close()
    try:
        os.system("git pull origin master")
        f = open("version", "w+")
        f.write(str(requests.get("https://api.github.com/repos/701789262a/arbobotti/tags").json()[0]["name"]))
        f.close()
    except:
        print(f"{Fore.RED}[!] FAILED TO UPDATE, CLOSING...")
        sys.exit(1)

else:
    print(f"{Fore.MAGENTA}[!] UPDATED VERSION %s, CURRENT: %s {Style.RESET_ALL}" % (
        str(requests.get("https://api.github.com/repos/701789262a/arbobotti/tags").json()[0]["name"]), ver))

try:
    q = queue.Queue()
    thread_updater = Thread(target=updater.updater, args=(q,))
    thread_arbo = Thread(target=logic.arbo)
    thread_updater.start()
    thread_arbo.start()
    while True:
        if not q.empty():
            q.get()
            thread_arbo.join()
            time.sleep(5)
            thread_arbo = Thread(target=logic.arbo)
except KeyboardInterrupt:
    sys.exit(0)
