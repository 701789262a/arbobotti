import datetime
import json
import queue
import time

import pandas
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
taker_fee_trt = .02
taker_fee_bnb = .00075
save_interval = 20
save_trade_interval = 50
fee_interval = 100
rate = 5
prod_threshold = 0.01
sleep_check_order = 2
min_balance = 10

bnb_que = queue.Queue()
trt_que = queue.Queue()
all_balance = dict()
time_list = []


def main():
    op = Operation(trt_apikey, trt_secret, krk_apikey, krk_secret, bnb_apikey, bnb_secret, exchange_list)
    fee = op.feethreading()
    taker_fee_trt = float(fee["feetrt"]) / 100
    taker_fee_bnb = 75 * float(fee["fee" + exchange_list[1]]) / 100
    print("GOT FEE FROM EXCHANGE; %s: %f;    %s: %f" % (
        exchange_list[0].upper(), taker_fee_trt, exchange_list[1].upper(), taker_fee_bnb))
    checkbalance = True
    while 1:

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
        price_dict = op.querythread()
        _query_time = time.time() - _query_time
        asks_data_bnb = price_dict["bnb"]['asks'][0]
        bids_data_bnb = price_dict["bnb"]['bids'][0]

        asks_data_trt = price_dict["trt"]['asks'][0]
        bids_data_trt = price_dict["trt"]['bids'][0]
        asks_krk = round(float(price_dict["bnb"]['asks'][0][0]), 2)
        bids_krk = round(float(price_dict["bnb"]['bids'][0][0]), 2)
        asks_trt = round(float(price_dict["trt"]['asks'][0]['price']), 2)
        bids_trt = round(float(price_dict["trt"]['bids'][0]['price']), 2)
        print(f"{Fore.LIGHTCYAN_EX}[i] %s{Style.RESET_ALL}" % (datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))

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
        print(
            f"[i]                           DIFFERENCE: %.2f                             TOT EUR: {Fore.GREEN}%.8f{Style.RESET_ALL}" % (
                round(bids_krk - asks_trt, 2), all_balance["bnbeur"] + all_balance["trteur"]))
        print(
            f"[i]                           DIFF + FEE: {Fore.RED}%.2f{Style.RESET_ALL}                            TOT BTC: {Fore.GREEN}%.8f{Style.RESET_ALL}                       PF VALUE: {Fore.GREEN}%.4f{Style.RESET_ALL}"
            % (round((bids_krk * (1 - taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt)), 2),
               all_balance["bnbbtc"] + all_balance["trtbtc"], all_balance["bnbeur"] + all_balance["trteur"] + (
                       (all_balance["bnbbtc"] + all_balance["trtbtc"]) * bids_trt)))
        print("[i] FETCHED FEE       %s: %.4f%%;      %s: %.4f%%" % (
            exchange_list[0].upper(), taker_fee_trt * 100, exchange_list[1].upper(), taker_fee_bnb * 100))

        if (bids_trt * (1 - taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb)) > 0:
            low_balance = False
            print(f"{Fore.CYAN}[#] %.2f < %.2f BUY %s | SELL TRT DIFF: %.2f (MENO FEE): %.3f" % (
                asks_krk, bids_trt, exchange_list[1].upper(), bids_trt - asks_krk,
                (bids_trt * (1 + taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb))))
            depth = min(bids_data_trt['amount'],
                        float(asks_data_bnb[1]))
            balance = min(all_balance["trtbtc"], all_balance["bnbeur"] / asks_krk)
            if balance < depth:
                depth = balance
                print(f"{Fore.MAGENTA}[#] PARTIAL FILLING, BALANCE LOWER THAN DEPTH{Style.RESET_ALL}")
                if depth == 0:
                    print(f"{Fore.RED}[#] BALANCE IS LOW, PLEASE DEPOSIT TO CONTINUE{Style.RESET_ALL}")
                    low_balance = True
            if not low_balance and (asks_krk * depth) > min_balance:
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

                    if resp_dict["bnb"] != "ERROR" or resp_dict["trt"][1] == "ERROR":
                        print(f"{Fore.RED}[$] TRADE ERROR MSG: [%s, %s]{Style.RESET_ALL}" % (
                            resp_dict["trt"][0].upper(), resp_dict["bnb"]))
                        op.cancelthreading()
                    else:
                        print(f"{Fore.GREEN}[#] SOUNDS GOOD! ORDER STATUS:[%s, %s]{Style.RESET_ALL}" % (
                            resp_dict["trt"][0], resp_dict["bnb"]))
                        time.sleep(sleep_check_order)
                        _trade_list.append(
                            [datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "buy", exchange_list[1], depth,
                             last_ask,
                             "sell", "trt", last_bid, all_balance["bnbbtc"], all_balance["trtbtc"],
                             all_balance["bnbeur"], all_balance["trteur"]])
                        op.cancelthreading()
                        # EXECUTED OR SUCCESS
                        # IF BOTH ORDER ARE NOT COMPLETED, DELETE ORDER

        elif (bids_krk * (1 - taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt)) > 0:
            low_balance = False
            print(f"{Fore.CYAN}[!] %.2f < %.2f BUY TRT | SELL %s DIFF: %.2f (MENO FEE): %.3f{Style.RESET_ALL}" % (
                asks_trt, bids_krk, exchange_list[1].upper(), bids_krk - asks_trt,
                (bids_krk * (1 + taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt))))
            depth = min(asks_data_trt['asks'][0]['amount'],
                        float(bids_data_bnb[1]))
            balance = min(all_balance["bnbbtc"], all_balance["trteur"] / asks_trt)
            if balance < depth:
                depth = balance
                print(f"{Fore.CYAN}[#] PARTIAL FILLING, BALANCE LOWER THAN DEPTH{Style.RESET_ALL}")
                if depth == 0:
                    print(f"{Fore.MAGENTA}[#] BALANCE IS LOW, PLEASE DEPOSIT TO CONTINUE{Style.RESET_ALL}")
                    low_balance = True
            if not low_balance and (asks_krk * depth) > min_balance:
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
                    if resp_dict['bnb'] == "ERROR" or resp_dict['trt'][1] == "ERROR":
                        print(f"{Fore.RED}[$] TRADE ERROR MSG: [%s, %s]{Style.RESET_ALL}" % (
                            resp_dict["trt"][0].upper(), resp_dict["bnb"]))
                        op.cancelthreading()
                    else:
                        print(f"{Fore.GREEN}[#] SOUNDS GOOD! ORDER NO:[%s, %s]{Style.RESET_ALL}" % (
                            resp_dict["trt"][0], resp_dict["bnb"]))
                        time.sleep(sleep_check_order)
                        _trade_list.append(
                            [datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "buy", "trt", depth, last_ask,
                             "sell", exchange_list[1], last_bid, all_balance["bnbbtc"], all_balance["trtbtc"],
                             all_balance["bnbeur"], all_balance["trteur"]])
                        op.cancelthreading()

        _end_time = time.time()
        totaltime = _end_time - _start_time
        time_list.append(int(totaltime * 1000))
        if last_ask != 0:
            _list.append([_end_time, time.time(), last_ask, last_bid, depth, eff, int(_query_time * 1000),
                          (int((_end_time - _start_time) * 1000) - int(_query_time * 1000)),
                          int((_end_time - _start_time) * 1000)])
        if int(_end_time % save_interval) == 0:
            print(f"{Fore.YELLOW}[!] SAVING...{Style.RESET_ALL}")
            if _list:
                save_data(_list)
        if int(_end_time % save_trade_interval) == 0:
            print(f"{Fore.YELLOW}[!] SAVING TRADE LIST...{Style.RESET_ALL}")
            if _trade_list:
                save_trade(_trade_list)
        if int(_end_time % fee_interval) == 0:
            print(f"{Fore.YELLOW}[!] FETCHING FEE DATA...{Style.RESET_ALL}")
            fee = op.feethreading()
            taker_fee_trt = float(fee["fee" + exchange_list[0]]) / 100
            taker_fee_krk = float(fee["fee" + exchange_list[1]]) / 100

        print(
            f"[-] ------------------------------------------------- {Fore.YELLOW}%d ms{Style.RESET_ALL} (%d ms(q) + %d ms(p)) - avg last %d ({Fore.YELLOW}%d ms{Style.RESET_ALL}) - global avg ({Fore.YELLOW}%d ms{Style.RESET_ALL})" % (
                int(totaltime * 1000), int(_query_time * 1000),
                (int(totaltime * 1000) - int(_query_time * 1000)), min(100, len(time_list)),
                sum(time_list[-100:]) / min(100, len(time_list)), sum(time_list) / len(time_list)))


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


if __name__ == "__main__":
    main()
