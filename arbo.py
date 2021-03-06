import os
import sys
import time
from threading import Thread
import asyncio
import requests
from colorama import Fore, Style

import logic


def main():
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
        loop = asyncio.get_event_loop()
        loop.run_until_complete(logic.arbo())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
