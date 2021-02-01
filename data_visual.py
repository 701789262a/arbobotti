import matplotlib.pyplot as plt
from threading import Thread
import time
from matplotlib.animation import FuncAnimation
import matplotlib.animation as animation
import pandas
fig = plt.figure(figsize=(15,7))
(ax1, ax2) = fig.subplots(1, 2)
def ru():
    print(";çiaone")
    anim= FuncAnimation(fig, animate, interval=23000)
    plt.show()



def animate(i):
    s1 = []
    y1=[]
    s2 = []
    df = pandas.read_csv("filev2.csv", sep=';')
    _list = df.values.tolist()
    for i in range(len(df)):
        s1.append(float(_list[i][13].replace(",","."))) #sell trt
        y1.append(i)
        s2.append(float(_list[i][15].replace(",", ".")))
    ax1.grid()
    ax2.grid()
    ax1.set_title("BUT BNB SELL TRT")
    ax2.set_title("BUT TRT SELL BNB")
    ax1.plot(y1,s1,"b")
    ax2.plot(y1, s2, "g")