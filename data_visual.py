import threading

import matplotlib.pyplot as plt
import pandas
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button

fig = plt.figure(figsize=(15, 7))
(ax1, ax2) = fig.subplots(1, 2)
ax1p = ax1.twinx()
ax2p = ax2.twinx()
last_n = 200
interval = 5000
_p = True
show_price=True


def exe():
    anim = FuncAnimation(fig, animate, interval=interval)
    plt.show()


def ru():
    axcut1 = plt.axes([0.89, 0.001, 0.1, 0.075])
    axcut2 = plt.axes([0.78, 0.001, 0.1, 0.075])
    axcut3 = plt.axes([0.67, 0.001, 0.1, 0.075])
    axcut4 = plt.axes([0.56, 0.001, 0.1, 0.075])
    axcut5 = plt.axes([0.45, 0.001, 0.035, 0.075])
    axcut6 = plt.axes([0.34, 0.001, 0.035, 0.075])
    bcut_1000 = Button(axcut1, 'LAST 1000')
    bcut_1000.on_clicked(_10)
    bcut_500 = Button(axcut2, 'LAST 500')
    bcut_500.on_clicked(_5)
    bcut_200 = Button(axcut3, 'LAST 200')
    bcut_200.on_clicked(_2)
    bcut_g = Button(axcut4, 'GLOBAL')
    bcut_g.on_clicked(_g)
    exe()


def _10(event):
    global last_n
    last_n = 1000


def _5(event):
    global last_n
    last_n = 500


def _2(event):
    global last_n
    last_n = 200


def _g(event):
    global last_n
    df = pandas.read_csv("filev2.csv", sep=';')
    last_n = len(df)


def _p(event):
    global _p
    _p = False


def _r(event):
    global _p
    _p = True


def animate(i):
    if _p:
        s1 = []
        y1 = []
        s2 = []
        p1 = []
        p2 = []
        p1x = []
        p2x = []
        ax1.clear()
        ax1p.clear()
        ax2.clear()
        ax2p.clear()
        df = pandas.read_csv("filev2.csv", sep=';')
        _list = df.values.tolist()
        event = threading.Event()
        for i in range(last_n):
            s1.append(float(_list[len(df) - last_n + i][13].replace(",", ".")))  # sell trt
            p1.append(float(_list[len(df) - last_n + i][3].replace(",", ".")) / float(
                _list[len(df) - last_n + i - 1][4].replace(",", ".")))
            p2.append(float(_list[len(df) - last_n + i][4].replace(",", ".")) / float(
                _list[len(df) - last_n + i - 1][2].replace(",", ".")))
            p1x.append(float(_list[len(df) - last_n + i][3].replace(",", ".")))
            p2x.append(float(_list[len(df) - last_n + i][4].replace(",", ".")))
            y1.append(i)
            s2.append(float(_list[len(df) - last_n + i][15].replace(",", ".")))
        ax1.grid()
        ax2.grid()
        ax1.set_title("BUT BNB SELL TRT")
        ax2.set_title("BUT TRT SELL BNB")
        ax1.plot(y1, s1, "b")
        ax2.plot(y1, s2, "g")
        if show_price:
            ax1p.plot(y1, p2x, "r--")
            ax2p.plot(y1, p1x, "r--")
        else:
            ax1p.plot(y1, p1, "r--")
            ax2p.plot(y1, p2, "r--")
