import json
import queue
import time
from threading import Thread

import pandas as pd
import requests

from trade import Operation

_list = []
login_data = dict(open("keydict.txt", "r").readline().strip())

trt_apikey = str(login_data["trt_apikey"])
trt_secret = str(login_data["trt_secret"])
krk_apikey = str(login_data["krk_apikey"])
krk_secret = str(login_data["krk_secret"])

taker_fee_krk = .0013
taker_fee_trt = .0020
save_interval = 20
rate = 10

_params_krk = {"pair": "BTCEUR", "count": "4"}
_params_trt = {}
krk_que = queue.Queue()
trt_que = queue.Queue()
krk_que_trade = queue.Queue()
trt_que_trade = queue.Queue()
krk_que_balance = queue.Queue()
trt_que_balance = queue.Queue()


def main():
    op = Operation(trt_apikey, trt_secret, krk_apikey, krk_secret)
    while 1:
        last_bid = 0
        last_ask = 0
        depth = 0
        _start_time = time.time()
        time.sleep(1 / rate)
        _query_time = time.time()

        krk_thread = Thread(target=lambda q, arg1, arg2: q.put(query(arg1, arg2)), args=(krk_que, "krk", _params_krk))
        trt_thread = Thread(target=lambda q, arg1, arg2: q.put(query(arg1, arg2)), args=(trt_que, "trt", _params_trt))

        krk_thread.start()
        trt_thread.start()
        krk_thread.join()
        trt_thread.join()
        resp_krk = krk_que.get()
        resp_trt = trt_que.get()
        _query_time = time.time() - _query_time
        loaded_json_krk = json.loads(resp_krk)
        loaded_json_trt = json.loads(resp_trt)
        asks_krk = float(loaded_json_krk['result']['XXBTZEUR']['asks'][0][0])
        bids_krk = float(loaded_json_krk['result']['XXBTZEUR']['bids'][0][0])
        asks_trt = loaded_json_trt['asks'][0]['price']
        bids_trt = loaded_json_trt['bids'][0]['price']

        print("[i]", asks_krk)
        print("[i]", bids_trt)

        print("[i]", asks_trt)
        print("[i]", bids_krk)
        # Trade.dotrade("trt", "BTCEUR", "buy", 1, 1, apikey, secret)
        if (bids_trt * (1 + taker_fee_trt)) - (asks_krk * (1 + taker_fee_krk)) > 0:
            print("[!] %f < %f BUY KRK | SELL TRT DIFF: %f (MENO FEE): %f" % (
                asks_krk, bids_trt, bids_trt - asks_krk,
                (bids_trt * (1 + taker_fee_trt)) - (asks_krk * (1 + taker_fee_krk))))
            depth = min(loaded_json_trt['bids'][0]['amount'],
                        float(loaded_json_krk['result']['XXBTZEUR']['asks'][0][1]))
            print("[i] DEPTH %f BTC" % depth)
            eff = (depth * bids_trt * (1 + taker_fee_trt)) - (depth * asks_krk * (1 + taker_fee_krk))
            prod = eff / (depth * bids_trt)
            print("[i] GAIN DOPO FEE EFF %f | PROD(c) %f c/EUR" % (eff, prod * 100))
            print("[i] NEED %f EUR | %f BTC" % (asks_krk * depth, depth))
            last_ask = asks_krk
            last_bid = bids_trt
            if prod * 100 > 0.3 and eff > 1:
                print("[#] TRADE")
                op.dotrade("buy", "krk", "BTCEUR", depth, last_ask,
                           "sell", "trt", "BTCEUR", depth, last_bid)
                resp_trt_trade = json.loads(trt_que_trade.get())
                resp_krk_trade = json.loads(krk_que_trade.get())
                print(resp_trt_trade, resp_krk_trade)

        elif (bids_krk * (1 + taker_fee_krk)) - (asks_trt * (1 + taker_fee_trt)) > 0:
            print("[!] %f < %f BUY TRT | SELL KRK DIFF: %f (MENO FEE): %f" % (
                asks_trt, bids_krk, bids_krk - asks_trt,
                (bids_krk * (1 + taker_fee_krk)) - (asks_trt * (1 + taker_fee_trt))))
            depth = min(loaded_json_trt['asks'][0]['amount'],
                        float(loaded_json_krk['result']['XXBTZEUR']['bids'][0][1]))
            print("[!] DEPTH %f BTC" % depth)
            eff = (depth * bids_krk * (1 + taker_fee_krk)) - (depth * asks_trt * (1 + taker_fee_trt))
            prod = eff / (depth * bids_krk)
            print("[!] GAIN DOPO FEE EFF %f | PROD(c) %f c/EUR" % (eff, prod * 100))
            print("[!] NEED %f EUR | %f BTC" % (asks_trt * depth, depth))
            last_ask = asks_trt
            last_bid = bids_krk
            if prod * 100 > 0.3 and eff > 1:
                print("[#] TRADE")
                op.dotrade("buy", "trt", "BTCEUR", depth, last_ask,
                           "sell", "krk", "BTCEUR", depth, last_bid)
                resp_trt_trade = json.loads(trt_que_trade.get())
                resp_krk_trade = json.loads(krk_que_trade.get())
                print(resp_trt_trade, resp_krk_trade)

        _end_time = time.time()
        print("[i] TIME: ", int(_end_time % 100))
        if last_ask != 0:
            _list.append([_end_time, time.time(), last_ask, last_bid, depth, eff, int(_query_time * 1000),
                          (int((_end_time - _start_time) * 1000) - int(_query_time * 1000)),
                          int((_end_time - _start_time) * 1000)])
        if int(_end_time % save_interval) == 0:
            print("[!] SALVATAGGIO")
            if _list:
                save(_list)

        print("[-] ------------------------------------------- %d ms (%d ms(q) + %d ms(p))" % (
            int((_end_time - _start_time) * 1000), int(_query_time * 1000),
            (int((_end_time - _start_time) * 1000) - int(_query_time * 1000))))


def save(list):
    df = pd.DataFrame(list)
    try:
        df.to_csv('file.csv', index=False, sep=';', mode='a', header=False, decimal=',')
    except:
        print("[ERR] ERRORE SALVATAGGIO")
    list.clear()


def query(exchange, params):
    if exchange == "trt":
        resp_trt = requests.get('https://api.therocktrading.com/v1/funds/BTCEUR/orderbook', params=params)
        return resp_trt.text
    else:
        if exchange == "krk":
            resp_krk = requests.get('https://api.kraken.com/0/public/Depth', params=params)
            return resp_krk.text


def balance():
    list = []
    resp_balance_trt_E = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5, arg6, arg7: q.put(
        Operation.balance(arg1, arg2, arg3, arg4)),
                                args=(trt_que_balance, "trt", "BTC", trt_apikey, trt_secret))
    resp_balance_trt_B = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5, arg6, arg7: q.put(
        Operation.balance(arg1, arg2, arg3, arg4)),
                                args=(krk_que_balance, "krk", "EUR", krk_apikey, krk_secret))
    resp_balance_trt_B.start()
    resp_balance_trt_E.start()
    resp_balance_trt_B.join()
    resp_balance_trt_E.join()
    list.append(trt_que_balance.get())

    list.append(trt_que_balance.get())


if __name__ == "__main__":
    main()
