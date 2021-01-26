import datetime
import json
import queue
import time
from threading import Thread

import pandas
import requests
from binance.client import Client
from colorama import Fore
from colorama import Style

from trade import Operation

_list = []
_trade_list = []
exchange_list = []
login_data = json.loads(open("keydict.txt", "r").readline().strip().replace("\n", ""))
try:
    trt_apikey = str(login_data["trt_apikey"])
    trt_secret = str(login_data["trt_secret"])
    exchange_list.append("trt")
except:
    trt_apikey = ""
    trt_secret = ""
    pass
try:
    krk_apikey = str(login_data["krk_apikey"])
    krk_secret = str(login_data["krk_secret"])
    exchange_list.append("krk")
except:
    krk_apikey = ""
    krk_secret = ""
    pass
try:
    bnb_apikey = str(login_data["bnb_apikey"])
    bnb_secret = str(login_data["bnb_secret"])
    exchange_list.append("bnb")
except:
    bnb_apikey = ""
    bnb_secret = ""
    pass

taker_fee_krk = .0024
taker_fee_trt = .002
taker_fee_bnb = .00075
save_interval = 20
save_trade_interval = 180
fee_interval = 100
rate = 100
prod_threshold = 0.1
sleep_check_order = 1

_params_krk = {"pair": "BTCEUR", "count": "2"}
_params_trt = {}
bnb_que = queue.Queue()
trt_que = queue.Queue()
all_balance = dict()


def main():
    op = Operation(trt_apikey, trt_secret, krk_apikey, krk_secret, bnb_apikey, bnb_secret, exchange_list)
    fee = op.feethreading()
    taker_fee_trt = float(fee["feetrt"]) / 1000
    taker_fee_bnb = 75 * float(fee["fee" + exchange_list[1]]) / 100
    print("GOT FEE FROM EXCHANGE; %s: %f;    %s: %f" % (
        exchange_list[0].upper(), taker_fee_trt, exchange_list[1].upper(), taker_fee_bnb))
    checkbalance = True
    while 1:
        print(f"{Fore.LIGHTCYAN_EX}[i] %s{Style.RESET_ALL}" % (datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        if checkbalance:
            print(f"{Fore.YELLOW}[#] RETRIEVING BALANCE{Style.RESET_ALL}")
            all_balance = op.balancethreading()
            checkbalance = False
        last_bid = 0
        last_ask = 0
        depth = 0
        time.sleep(1 / rate)
        _start_time = time.time()
        _query_time = time.time()

        bnb_thread = Thread(target=lambda q, arg1, arg2, arg3, arg4: q.put(query(arg1, arg2, arg3, arg4)),
                            args=(bnb_que, "bnb", _params_krk, bnb_apikey, bnb_secret))
        trt_thread = Thread(target=lambda q, arg1, arg2, arg3, arg4: q.put(query(arg1, arg2, arg3, arg4)),
                            args=(trt_que, "trt", _params_trt, bnb_apikey, bnb_secret))

        bnb_thread.start()
        trt_thread.start()
        bnb_thread.join()
        trt_thread.join()
        resp_bnb = bnb_que.get()
        resp_trt = trt_que.get()
        _query_time = time.time() - _query_time
        loaded_json_trt = json.loads(resp_trt)
        asks_krk = round(float(resp_bnb['asks'][0][0]), 2)
        bids_krk = round(float(resp_bnb['bids'][0][0]), 2)
        asks_trt = round(loaded_json_trt['asks'][0]['price'], 2)
        bids_trt = round(loaded_json_trt['bids'][0]['price'], 2)

        print(f"[i] ASK %s : %.2f                              EUR BAL : {Fore.RED}%.8f{Style.RESET_ALL}" % (
            exchange_list[1].upper(), asks_krk, all_balance["bnbeur"]))
        print(f"[i] BID %s : %.2f                              BTC BAL : {Fore.RED}%.8f{Style.RESET_ALL}" % (
            exchange_list[0].upper(), bids_trt, all_balance["trtbtc"]))
        print("[i]                           DIFFERENCE:", round(bids_trt - asks_krk, 2))
        print(f"[i]                           DIFF + FEE: {Fore.RED}%.2f{Style.RESET_ALL}"
              % (round((bids_trt * (1 - taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb)), 2)))
        print(f"[i] ASK %s : %.2f                              EUR BAL : {Fore.RED}%.8f{Style.RESET_ALL}" % (
            exchange_list[0].upper(), asks_trt, all_balance["trteur"]))
        print(f"[i] BID %s : %.2f                              BTC BAL : {Fore.RED}%.8f{Style.RESET_ALL}" % (
            exchange_list[1].upper(), bids_krk, all_balance["bnbbtc"]))
        print("[i]                           DIFFERENCE:", round(bids_krk - asks_trt, 2))
        print(f"[i]                           DIFF + FEE: {Fore.RED}%.2f{Style.RESET_ALL}"
              % (round((bids_krk * (1 - taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt)), 2)))
        print("[i] FETCHED FEE       %s: %.4f%%;      %s: %.4f%%" % (
            exchange_list[0].upper(), taker_fee_trt * 100, exchange_list[1].upper(), taker_fee_bnb * 100))

        if (bids_trt * (1 - taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb)) > 0:
            low_balance = False
            print(f"{Fore.CYAN}[#] %.2f < %.2f BUY %s | SELL TRT DIFF: %.2f (MENO FEE): %.3f" % (
                asks_krk, bids_trt, exchange_list[1].upper(), bids_trt - asks_krk,
                (bids_trt * (1 + taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb))))
            depth = min(loaded_json_trt['bids'][0]['amount'],
                        float(resp_bnb['asks'][0][0]))
            balance = min(all_balance["trtbtc"], all_balance["bnbeur"] / asks_krk)
            if balance < depth:
                depth = balance
                print(f"{Fore.MAGENTA}[#] PARTIAL FILLING, BALANCE LOWER THAN DEPTH{Style.RESET_ALL}")
                if depth == 0:
                    print(f"{Fore.RED}[#] BALANCE IS LOW, PLEASE DEPOSIT TO CONTINUE{Style.RESET_ALL}")
                    low_balance = True
            if not low_balance:
                print(f"{Fore.CYAN}[#] DEPTH %f BTC" % depth)
                eff = (depth * bids_trt * (1 - taker_fee_trt)) - (depth * asks_krk * (1 + taker_fee_bnb))
                prod = eff / (depth * bids_trt)
                print("[#] GAIN DOPO FEE EFF %f € | PROD %f ¢/€" % (eff, prod * 100))
                print(f"[#] NEED %.3f EUR | %f BTC{Style.RESET_ALL}" % (asks_krk * depth, depth))
                last_ask = asks_krk
                last_bid = bids_trt
                if prod * 100 > prod_threshold:
                    checkbalance = True
                    print(f"{Fore.GREEN}[#] TRADE{Style.RESET_ALL}")
                    resp_dict = op.tradethreading("sell", "trt", "BTCEUR", depth, last_bid, "buy", "bnb", "BTCEUR",
                                                  depth,
                                                  last_ask)

                    if resp_dict['bnb'] != "ERROR" or resp_dict['trt'][1] == "ERROR":
                        print(f"{Fore.RED}[$] TRADE ERROR MSG: [%s, %s]{Style.RESET_ALL}" % (
                            resp_dict["trt"][0].upper(), resp_dict["bnb"]))
                        status = op.orderthreading(resp_dict["trt"][0],
                                                   resp_dict[exchange_list[1]])
                        if status["trt"] != "executed" or status["bnb"] == "NEW":
                            op.cancelthreading(resp_dict["trt"], resp_dict["bnb"])
                    else:
                        print(f"{Fore.GREEN}[#] SOUNDS GOOD! ORDER NO:[%s, %s]{Style.RESET_ALL}" % (
                            resp_dict["trt"][0], resp_dict["bnb"]))
                        time.sleep(sleep_check_order)
                        status = op.orderthreading(resp_dict["trt"][0],
                                                   resp_dict[exchange_list[1]])
                        _trade_list.append(
                            [datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "buy", exchange_list[1], depth,
                             last_ask,
                             "sell", "trt", last_bid, all_balance["bnbbtc"], all_balance["trtbtc"],
                             all_balance["bnbeur"], all_balance["trteur"]])
                        if status["trt"] != "executed" or status["bnb"] == "NEW":
                            op.cancelthreading(resp_dict["trt"], resp_dict["bnb"])
                        # EXECUTED OR SUCCESS
                        # IF BOTH ORDER ARE NOT COMPLETED, DELETE ORDER

        elif (bids_krk * (1 - taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt)) > 0:
            low_balance = False
            print(f"{Fore.CYAN}[!] %.2f < %.2f BUY TRT | SELL %s DIFF: %.2f (MENO FEE): %.3f{Style.RESET_ALL}" % (
                asks_trt, bids_krk, exchange_list[1].capitalize(), bids_krk - asks_trt,
                (bids_krk * (1 + taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt))))
            depth = min(loaded_json_trt['asks'][0]['amount'],
                        float(resp_bnb['bids'][0][0]))
            balance = min(all_balance["bnbbtc"], all_balance["trteur"] / asks_trt)
            if balance < depth:
                depth = balance
                print(f"{Fore.CYAN}[#] PARTIAL FILLING, BALANCE LOWER THAN DEPTH{Style.RESET_ALL}")
                if depth == 0:
                    print(f"{Fore.MAGENTA}[#] BALANCE IS LOW, PLEASE DEPOSIT TO CONTINUE{Style.RESET_ALL}")
                    low_balance = True
            if not low_balance:
                print(f"{Fore.CYAN}[!] DEPTH %f BTC" % depth)
                eff = (depth * bids_krk * (1 - taker_fee_bnb)) - (depth * asks_trt * (1 + taker_fee_trt))
                prod = eff / (depth * bids_krk)
                print("[i] GAIN DOPO FEE EFF %f € | PROD %f ¢/€" % (eff, prod * 100))
                print(f"[i] NEED %.3f EUR | %f BTC{Style.RESET_ALL}" % (asks_trt * depth, depth))
                last_ask = asks_trt
                last_bid = bids_krk
                if prod * 100 > prod_threshold:
                    checkbalance = True
                    print(f"{Fore.GREEN}[#] TRADE{Style.RESET_ALL}")
                    resp_dict = op.tradethreading("buy", "trt", "BTCEUR", depth, last_ask,
                                                  "sell", exchange_list[1], "BTCEUR", depth, last_bid)
                    if resp_dict['bnb'] != "ERROR" or resp_dict['trt'][1] == "ERROR":
                        print(f"{Fore.RED}[$] TRADE ERROR MSG: [%s, %s]{Style.RESET_ALL}" % (
                            resp_dict["trt"][0].upper(), resp_dict["bnb"]))
                        status = op.orderthreading(resp_dict["trt"][0],
                                                   resp_dict[exchange_list[1]])
                        if status["trt"] != "executed" or status["bnb"] == "NEW":
                            op.cancelthreading(resp_dict["trt"], resp_dict["bnb"])
                    else:
                        print(f"{Fore.GREEN}[#] SOUNDS GOOD! ORDER NO:[%s, %s]{Style.RESET_ALL}" % (
                            resp_dict["trt"][0], resp_dict["bnb"]))
                        time.sleep(sleep_check_order)
                        status = op.orderthreading(resp_dict["trt"][0],
                                                   resp_dict[exchange_list[1]])  # executed or success
                        _trade_list.append(
                            [datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "buy", "trt", depth, last_ask,
                             "sell", exchange_list[1], last_bid, all_balance["bnbbtc"], all_balance["trtbtc"],
                             all_balance["bnbeur"], all_balance["trteur"]])
                        if status["trt"] != "executed" or status["bnb"] == "NEW":
                            op.cancelthreading(resp_dict["trt"], resp_dict["bnb"])

        _end_time = time.time()
        if last_ask != 0:
            _list.append([_end_time, time.time(), last_ask, last_bid, depth, eff, int(_query_time * 1000),
                          (int((_end_time - _start_time) * 1000) - int(_query_time * 1000)),
                          int((_end_time - _start_time) * 1000)])
        if int(_end_time % save_interval) == 0:
            print(f"{Fore.YELLOW}[!] SAVING...{Style.RESET_ALL}")
            if _list:
                save_data(_list)
        if int(_end_time % save_trade_interval):
            print(f"{Fore.YELLOW}[!] SAVING TRADE LIST...{Style.RESET_ALL}")
            if _trade_list:
                save_trade(_trade_list)
        if int(_end_time % fee_interval) == 0:
            print(f"{Fore.YELLOW}[!] FETCHING FEE DATA...{Style.RESET_ALL}")
            fee = op.feethreading()
            taker_fee_trt = float(fee["fee" + exchange_list[0]]) / 100
            taker_fee_krk = float(fee["fee" + exchange_list[1]]) / 100

        print("[-] ------------------------------------------------- %d ms (%d ms(q) + %d ms(p))" % (
            int((_end_time - _start_time) * 1000), int(_query_time * 1000),
            (int((_end_time - _start_time) * 1000) - int(_query_time * 1000))))


def save_data(_list):
    df = pandas.DataFrame(_list)
    try:
        df.to_csv('file.csv', index=False, sep=';', mode='a', header=False, decimal=',')
    except FileNotFoundError:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO{Style.RESET_ALL}")
    _list.clear()


def save_trade(_list):
    df = pandas.DataFrame(_list)
    try:
        df.to_csv('file_trade.csv', index=False, sep=';', mode='a', header=False, decimal=',')
    except FileNotFoundError:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO TRADELIST{Style.RESET_ALL}")
    _list.clear()


def query(exchange, params, apikey, secret):
    if exchange == "trt":
        resp_trt = requests.get('https://api.therocktrading.com/v1/funds/BTCEUR/orderbook', params=params)
        return resp_trt.text
    elif exchange == "krk":
        resp_krk = requests.get('https://api.kraken.com/0/public/Depth', params=params)
        return resp_krk.text
    elif exchange == "bnb":
        client = Client(apikey, secret)

        while 1:
            try:
                resp_bnb = client.get_order_book(symbol="BTCEUR")
                return resp_bnb
            except requests.exceptions.ConnectionError:
                print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")
                time.sleep(1)


if __name__ == "__main__":
    main()
