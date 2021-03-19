import datetime
import getpass
import json
import os
import socket
import sys
import threading
import time
from multiprocessing import Process
from multiprocessing.pool import ThreadPool

import gnupg
import mysql.connector
import pandas
import requests
from colorama import Fore
from colorama import Style
from openpyxl import load_workbook

import data_visual
from trade import Operation

_print_list = []


def arbo():
    d = {}
    with open("config.txt") as f:
        for line in f:
            (key, val) = line.replace(" ", "").split("=")
            val = val.split("#")[0]
            d[key] = val
    gpg = gnupg.GPG(d["gpg"][:-1])
    _list = []
    _trade_list = []
    exchange_list = []
    print(f"""{Fore.RED}                                                                                          
                                                                                              
                                                                   .%%%#                      
                                                               *#%%%%%%%%,                    
                                                           /#%%%%%%%%%%%%%%                   
                                                       %%%%%%%%%%%%%%%%%%%%%                  
                                                   #%%%%%%%%%%%%%%%%%%%%%%%%%%                
                                                  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%               
                                                  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%#             
                                      /%/        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%#            
                                  %#%%%%%%      (%%%%%%%%%%%%(     *#%%%%%%%%%%%%%%           
                              %%%%%%%%%%%%%%    %%%%%%%#%.           #%%%%%%%%%%%%            
                         ,#%%%%%%%%%%%%%%%%%%  %%%%%%                 (%%%%%%%%%%             
                     (%%%%%%%%%%%%%%%%%%%%%%%%%#/                       %%%%%%%%*             
                    %%%%%%%%%%%%%%%%%%%%%%%%%%%%                         #%%%%%#              
                   #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%                         %%%#               
                   %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%                         %%                
                  %%%%%%%%%%%%%#    .%%%%%%%%%%%%%%%*                     .%#                 
                 .%%%%%%%%#,          %%%%%%%%%%%%%  #                /%*                     
                 %%%%%%                *%%%%%%%%%%(   %.          %%                          
                (%#                      #%%%%%%%%     .%    .##                              
                ,%                        (#%%%%#        ##/                                  
                  #                         %%%%                                              
                   ((                        #%                                               
                     #                      #%                                                
                      #*                #%                                                    
                        %          *%(                                                        
                         %.    #%.                                                            
                           %%                                                                 
                                                                                              
      {Style.RESET_ALL}""")
    passphrase = getpass.getpass("Please provide master password to continue:")
    with open("telegram.gpg", "rb") as tg_f:
        status_tg = gpg.decrypt_file(file=tg_f, passphrase=passphrase)
    with open("keydict.gpg", "rb") as kd_f:
        status_kd = gpg.decrypt_file(file=kd_f, passphrase=passphrase)
    with open("dbinfo.gpg", "rb") as db_f:
        status_db = gpg.decrypt_file(file=db_f, passphrase=passphrase)
    printin_data = json.loads(str(status_kd).strip().replace("\n", ""))
    tg_data = json.loads(str(status_tg).strip().replace("\n", ""))
    db_data = json.loads(str(status_db).strip().replace("\n", ""))
    try:
        trt_apikey = str(printin_data["trt_apikey"])
        trt_secret = str(printin_data["trt_secret"])
        exchange_list.append("trt")
    except:
        exit(1)
    try:
        krk_apikey = str(printin_data["krk_apikey"])
        krk_secret = str(printin_data["krk_secret"])
        exchange_list.append("krk")
    except:
        krk_apikey = ""
        krk_secret = ""
    try:
        bnb_apikey = str(printin_data["bnb_apikey"])
        bnb_secret = str(printin_data["bnb_secret"])
        exchange_list.append("bnb")
    except:
        exit(3)
    all_balance = dict()
    time_list = []
    print(f"{Fore.GREEN}\nThank you{Style.RESET_ALL}")

    while not check_api_connection():
        time.sleep(1)
    op = Operation(trt_apikey, trt_secret, krk_apikey, krk_secret, bnb_apikey, bnb_secret, exchange_list)
    op.threadCreation()
    time.sleep(2)
    fee = op.feethreading()
    taker_fee_trt = float(fee["fee" + exchange_list[0] + "taker"]) / 100
    taker_fee_bnb = float(fee["fee" + exchange_list[1] + "taker"])
    maker_fee_trt = float(fee["fee" + exchange_list[0] + "maker"]) / 100
    maker_fee_bnb = float(fee["fee" + exchange_list[1] + "maker"])
    print("GOT FEE FROM EXCHANGE; %s: %f;    %s: %f" % (
        exchange_list[0].upper(), taker_fee_trt, exchange_list[1].upper(), taker_fee_bnb))
    checkbalance = True
    _tglist = []
    if d["graph"].lower() == "true":
        g = Process(target=data_visual.ru)
        g.start()
    f = open("version", "r")
    ver = f.read()
    all_balance = op.balancethreading()
    s = socket.socket()
    print(str(d["dip"]))
    last_h = 0
    try:
        s.connect((str(d["dip"]).rstrip("\n"), 30630))
    except ConnectionRefusedError:
        pass
    pool = ThreadPool()
    already_saved = False
    while 1:
        try:
            eff = 0
            prod = 0
            if checkbalance:
                print(f"{Fore.YELLOW}[#] RETRIEVING BALANCE{Style.RESET_ALL}")
                all_balance = op.balancethreading()
                checkbalance = False
            time.sleep(1 / int(d["rate"]))
            _start_time = time.time()
            _query_time = time.time()
            price_dict = op.querythread()
            _query_time = time.time() - _query_time
            try:
                asks_data_bnb = price_dict["bnb"]['asks'][0]
                bids_data_bnb = price_dict["bnb"]['bids'][0]
                asks_data_trt = price_dict["trt"]['asks'][0]
                bids_data_trt = price_dict["trt"]['bids'][0]
            except TypeError:
                print(f"{Fore.RED}[#] ERROR WHILE FETCHING DATA [typeError - nonetype]{Style.RESET_ALL}")
                continue
            asks_krk = round(float(price_dict["bnb"]['asks'][0][0]), 2)
            bids_krk = round(float(price_dict["bnb"]['bids'][0][0]), 2)
            asks_trt = round(float(price_dict["trt"]['asks'][0]['price']), 2)
            bids_trt = round(float(price_dict["trt"]['bids'][0]['price']), 2)
            last_bid = 0
            last_ask = 0
            depth = 0
            bal_list = False
            os.system('cls' if os.name == 'nt' else 'clear')
            a = datetime.datetime.now()
            only_see = bool(int(d["only_see"]))
            if not str(a.microsecond)[:-5]:
                small_index = 0
            else:
                small_index = str(a.microsecond)[:-5]
            _trade_list.clear()
            print(f"{Fore.MAGENTA}[!] ARBOBOTTI VERSION %s, MURINEDDU CAPITAL 2021{Style.RESET_ALL}\n" % (ver))
            print(
                f"{Fore.LIGHTCYAN_EX}[i] %s{Style.RESET_ALL}          INDEX: {Fore.LIGHTCYAN_EX}%s - %s{Style.RESET_ALL}        THREAD_POOL:{Fore.LIGHTCYAN_EX} %s{Style.RESET_ALL}         ONLY_SEE: {Fore.LIGHTCYAN_EX} %d{Style.RESET_ALL}" % (
                    a.strftime("%d/%m/%Y %H:%M:%S"), str(int(time.time()))[-4:], small_index, str(op.len), only_see))

            print(f"[i] ASK %s : %.2f                              EUR %s BAL : {Fore.RED}%.5f{Style.RESET_ALL}" % (
                exchange_list[1].upper(), asks_krk, exchange_list[1].upper(), all_balance["bnbeur"]))
            print(f"[i] BID %s : %.2f                              BTC %s BAL : {Fore.RED}%.8f{Style.RESET_ALL}" % (
                exchange_list[0].upper(), bids_trt, exchange_list[0].upper(), all_balance["trtbtc"]))
            print("[i]                           DIFFERENCE: %s" % (num(round(bids_trt - asks_krk, 2))))
            print(f"[i]                           DIFF + FEE: {Fore.RED}%s{Style.RESET_ALL}"
                  % (num(round((bids_trt * (1 - taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb)), 2))))
            print(f"[i] ASK %s : %.2f                              EUR %s BAL : {Fore.RED}%.5f" % (
                exchange_list[0].upper(), asks_trt, exchange_list[0].upper(), all_balance["trteur"]))
            print(
                f"{Style.RESET_ALL}[i] BID %s : %.2f                              BTC %s BAL : {Fore.RED}%.8f{Style.RESET_ALL}" % (
                    exchange_list[1].upper(), bids_krk, exchange_list[1].upper(), all_balance["bnbbtc"]))
            print(
                f"[i]                           DIFFERENCE: %s                             TOT EUR: {Fore.GREEN}%.8f{Style.RESET_ALL}" % (
                    num(round(bids_krk - asks_trt, 2)), all_balance["bnbeur"] + all_balance["trteur"]))
            print(
                f"[i]                           DIFF + FEE: {Fore.RED}%s{Style.RESET_ALL}                             TOT BTC: {Fore.GREEN}%.8f{Style.RESET_ALL}                       PF VALUE: {Fore.GREEN}%.4f{Style.RESET_ALL}"
                % (num(round((bids_krk * (1 - taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt)), 2)),
                   all_balance["bnbbtc"] + all_balance["trtbtc"], all_balance["bnbeur"] + all_balance["trteur"] + (
                           (all_balance["bnbbtc"] + all_balance["trtbtc"]) * bids_trt)))
            print("[i] FETCHED TAKER FEE       %s: %.4f%%;      %s: %.4f%%" % (
                exchange_list[0].upper(), taker_fee_trt * 100, exchange_list[1].upper(), taker_fee_bnb * 100))
            print("[i] FETCHED MAKER FEE       %s: %.4f%%;      %s: %.4f%%" % (
                exchange_list[0].upper(), maker_fee_trt * 100, exchange_list[1].upper(), maker_fee_bnb * 100))

            if (bids_trt * (1 - taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb)) > 0:
                low_balance = False
                print(f"{Fore.CYAN}[#] %.2f < %.2f BUY %s | SELL TRT DIFF: %.2f (MENO FEE): %.3f" % (
                    asks_krk, bids_trt, exchange_list[1].upper(), bids_trt - asks_krk,
                    (bids_trt * (1 + taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb))))
                depth = float(min(bids_data_trt['amount'],
                                  float(asks_data_bnb[1])))
                balance = min(all_balance["trtbtc"], all_balance["bnbeur"] / asks_krk)
                if balance < depth:
                    depth = round(float(balance * float(d["max_each_trade"])), 4)
                    print(f"{Fore.MAGENTA}[#] PARTIAL FILLING, BALANCE LOWER THAN DEPTH{Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}[#] DEPTH %f{Style.RESET_ALL}" % (depth))

                    if depth == 0:
                        print(f"{Fore.RED}[#] BALANCE IS LOW, PLEASE DEPOSIT TO CONTINUE{Style.RESET_ALL}")
                        low_balance = True
                else:
                    print(f"{Fore.GREEN}[#] COMPLETE FILLING{Style.RESET_ALL}")
                    depth = round(float(depth * float(d["max_each_trade"])), 4)
                    print(f"{Fore.GREEN}[#] DEPTH %f{Style.RESET_ALL}" % (depth))

                if not low_balance and depth > float(d["min_balance"]):
                    print(f"{Fore.CYAN}[#] DEPTH %f BTC" % depth)
                    eff = (depth * bids_trt * (1 - taker_fee_trt)) - (depth * asks_krk * (1 + taker_fee_bnb))
                    prod = eff / (depth * bids_trt)
                    print("[#] GAIN DOPO FEE EFF %f € | PROD %f ¢/€" % (eff, prod * 100))
                    print(f"[#] NEED %.3f EUR | %f BTC{Style.RESET_ALL}" % (asks_krk * depth, depth))
                    last_ask = asks_krk
                    last_bid = bids_trt
                    if prod * 100 > float(d["prod_threshold"]) and not only_see:
                        checkbalance = True
                        print(f"{Fore.GREEN}[#] TRADE{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}[H] SELL %f BTC ON TRT, BUYING %f (%f) BTC ON BNB{Style.RESET_ALL}" % (
                            depth, depth, depth * last_ask))
                        resp_dict = op.tradethreading("sell", "trt", "BTCEUR", depth, last_bid, "buy", "bnb", "BTCEUR",
                                                      depth,
                                                      last_ask)
                        print("BNB", resp_dict["bnb"], "\nTRT", resp_dict["trt"])
                        try:
                            status = (resp_dict["bnb"]["status"], resp_dict["trt"]["status"])
                        except KeyError:
                            print(f"{Fore.RED}[!] ERROR RETRIEVING STATUS{Style.RESET_ALL}")
                            status = (resp_dict["bnb"]["status"], resp_dict["trt"]["errors"][0]["message"])
                        if status[0] == "ERROR" or status[1] == "ERROR":
                            print(f"{Fore.RED}[$] TRADE ERROR MSG: [%s, %s]{Style.RESET_ALL}" % (
                                resp_dict["trt"][0].upper(), resp_dict["bnb"]))
                            time.sleep(20)
                        else:
                            print(f"{Fore.GREEN}[#] SOUNDS GOOD! ORDER STATUS:[%s, %s]{Style.RESET_ALL}" % (
                                resp_dict["trt"]["status"].upper(), resp_dict["bnb"]["status"]))
                            bal_list = True
                            time.sleep(int(d["sleep_check_order"]))
                            _trade_list.append(
                                [datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "BUY", exchange_list[1].upper(),
                                 str(depth).replace(",", "."),
                                 str(last_ask).replace(".", ","),
                                 "SELL", "TRT", str(last_bid).replace(".", ","), float(all_balance["bnbbtc"]),
                                 float(all_balance["trtbtc"]),
                                 float(all_balance["bnbeur"]), float(all_balance["trteur"]),
                                 float(all_balance["trteur"] + all_balance["bnbeur"] + (
                                         all_balance["bnbbtc"] + all_balance["trtbtc"]) * last_ask)])
                            pass
                            # EXECUTED OR SUCCESS
                            # IF BOTH ORDER ARE NOT COMPLETED, DELETE ORDER
                else:
                    print(f"{Fore.RED}[$] TOO LOW BALANCE, PLEASE DEPOSIT{Style.RESET_ALL}")
                    checkbalance = True
            elif (bids_krk * (1 - taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt)) > 0:
                low_balance = False
                depth = float(min(asks_data_trt['amount'],
                                  float(bids_data_bnb[1])))
                balance = min(all_balance["bnbbtc"], all_balance["trteur"] / asks_trt)
                print(
                    f"{Fore.CYAN}[!] %.2f < %.2f BUY TRT | SELL %s DIFF: %.2f (MENO FEE): %.3f | DEPTH: %.8f | MINBAL: %.8f{Style.RESET_ALL}" % (
                        asks_trt, bids_krk, exchange_list[1].upper(), bids_krk - asks_trt,
                        (bids_krk * (1 + taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt)), depth, balance))
                if balance < depth:
                    depth = round(float(balance * float(d["max_each_trade"])), 4)
                    print(f"{Fore.MAGENTA}[#] PARTIAL FILLING, BALANCE LOWER THAN DEPTH{Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}[#] DEPTH %f{Style.RESET_ALL}" % (depth))
                    if depth == 0:
                        print(f"{Fore.MAGENTA}[#] BALANCE IS LOW, PLEASE DEPOSIT TO CONTINUE{Style.RESET_ALL}")
                        low_balance = True
                else:
                    print(f"{Fore.GREEN}[#] COMPLETE FILLING{Style.RESET_ALL}")
                    depth = round(float(depth * float(d["max_each_trade"])), 4)
                    print(f"{Fore.GREEN}[#] DEPTH %f{Style.RESET_ALL}" % (depth))

                if not low_balance and (depth > float(d["min_balance"])):
                    print(f"{Fore.CYAN}[!] DEPTH %f BTC" % depth)
                    eff = (depth * bids_krk * (1 - taker_fee_bnb)) - (depth * asks_trt * (1 + taker_fee_trt))
                    prod = eff / (depth * bids_krk)
                    print("[i] GAIN DOPO FEE EFF %f € | PROD %f ¢/€" % (eff, prod * 100))
                    print(f"[i] NEED %.3f EUR | %f BTC{Style.RESET_ALL}" % (asks_trt * depth, depth))
                    last_ask = asks_trt
                    last_bid = bids_krk
                    if prod * 100 > float(d["prod_threshold"]) and not only_see:
                        checkbalance = True
                        print(f"{Fore.GREEN}[#] TRADE{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}[H] SELL %f BTC ON BNB, BUYING %f (%f) BTC ON TRT{Style.RESET_ALL}" % (
                            depth, depth, depth * last_ask))
                        resp_dict = op.tradethreading("buy", "trt", "BTCEUR", depth, last_ask,
                                                      "sell", exchange_list[1], "BTCEUR", depth, last_bid)
                        print("BNB", resp_dict["bnb"], "\nTRT", resp_dict["trt"])
                        try:
                            status = (resp_dict["bnb"]["status"], resp_dict["trt"]["status"])
                        except KeyError:
                            print(f"{Fore.RED}[!] ERROR RETRIEVING STATUS{Style.RESET_ALL}")
                            status = (resp_dict["bnb"]["status"], resp_dict["trt"]["errors"][0]["message"])
                        if status[0] == "ERROR" or status[1] == "ERROR":
                            print(f"{Fore.RED}[$] TRADE ERROR MSG: [%s, %s]{Style.RESET_ALL}" % (
                                resp_dict["trt"][0].upper(), resp_dict["bnb"]))
                            time.sleep(20)
                            pass
                        else:
                            print(f"{Fore.GREEN}[#] SOUNDS GOOD! ORDER NO:[%s, %s]{Style.RESET_ALL}" % (
                                resp_dict["trt"]["status"].upper(), resp_dict["bnb"]["status"]))
                            bal_list = True
                            time.sleep(int(d["sleep_check_order"]))
                            _trade_list.append(
                                [datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "BUY", "TRT",
                                 str(depth).replace(".", ","), str(last_ask).replace(".", ","),
                                 "SELL", exchange_list[1].upper(), str(last_bid).replace(".", ","),
                                 float(all_balance["bnbbtc"]),
                                 float(all_balance["trtbtc"]),
                                 float(all_balance["bnbeur"]), float(all_balance["trteur"]),
                                 float(all_balance["trteur"] + all_balance["bnbeur"] + (
                                         all_balance["bnbbtc"] + all_balance["trtbtc"]) * last_ask)])
                else:
                    print(f"{Fore.RED}[$] TOO LOW BALANCE, PLEASE DEPOSIT{Style.RESET_ALL}")
                    checkbalance = True
            _end_time = time.time()
            totaltime = _end_time - _start_time
            time_list.append(int(totaltime * 1000))
            _list.append([datetime.datetime.now(), asks_krk, bids_krk, asks_trt, bids_trt,
                          all_balance["bnbbtc"], all_balance["trtbtc"], all_balance["bnbeur"],
                          all_balance["trteur"], eff, prod, int(totaltime * 1000), round(bids_trt - asks_krk, 2),
                          round((bids_trt * (1 - taker_fee_trt)) - (asks_krk * (1 + taker_fee_bnb)), 2),
                          round(bids_krk - asks_trt, 2),
                          round((bids_krk * (1 - taker_fee_bnb)) - (asks_trt * (1 + taker_fee_trt)), 2)])
            if int(_end_time % int(d["save_interval"])) == 0 and not already_saved:
                print(f"{Fore.YELLOW}[!] SAVING...{Style.RESET_ALL}")
                if _list:
                    save_data_thread = threading.Thread(target=save_data, args=(_list, d["sep"],))
                    save_data_thread.start()
                    already_saved = True
                    try:
                        data = arbomonitor(s, only_see, last_h)
                        if data == "go":
                            only_see = True
                    except Exception:
                        try:
                            s.close()
                            s.connect((str(d["dip"]), 30630))
                        except ConnectionRefusedError:
                            pass
                        except socket.gaierror:
                            pass
            if int(str(int(_end_time))[-1]) > 1:
                already_saved = False
            if int(_end_time % int(d["balance_interval"])) == 0:
                checkbalance = True
            if _trade_list:
                all_balance = op.balancethreading()
                time.sleep(1)
                _trade_list.append(
                    ["", "", "", "", "", "", "", "", float(all_balance["bnbbtc"]), float(all_balance["trtbtc"]),
                     float(all_balance["bnbeur"]),
                     float(all_balance["trteur"]),
                     ((all_balance["bnbbtc"] + all_balance["trtbtc"]) * last_ask) +
                     float(all_balance["bnbeur"]) +
                     float(all_balance["trteur"])])
                print(f"{Fore.YELLOW}[!] SAVING TRADE LIST...{Style.RESET_ALL}")
                save_trade_thread = threading.Thread(target=save_trade, args=(_trade_list, d["sep"], db_data, tg_data,))
                save_trade_thread.start()
                save_trade_thread.join()
                _trade_list.clear()
            if int(_end_time % int(d["fee_interval"])) == 0:
                print(f"{Fore.YELLOW}[!] FETCHING FEE DATA...{Style.RESET_ALL}")
                fee = op.feethreading()
                taker_fee_trt = float(fee["fee" + exchange_list[0] + "taker"]) / 100
                taker_fee_bnb = float(fee["fee" + exchange_list[1] + "taker"])
                maker_fee_trt = float(fee["fee" + exchange_list[0] + "maker"]) / 100
                maker_fee_bnb = float(fee["fee" + exchange_list[1] + "maker"])
            last_h = sum(time_list[-100:]) / min(100, len(time_list))
            print(
                f"[-] ------------------------------------------------- {Fore.YELLOW}%d ms{Style.RESET_ALL} (%d ms(q) + %d ms(p)) - avg last %d ({Fore.YELLOW}%d ms{Style.RESET_ALL}) - global avg ({Fore.YELLOW}%d ms{Style.RESET_ALL})" % (
                    int(totaltime * 1000), int(_query_time * 1000),
                    (int(totaltime * 1000) - int(_query_time * 1000)), min(100, len(time_list)),
                    sum(time_list[-100:]) / min(100, len(time_list)), sum(time_list) / len(time_list)))
        except KeyboardInterrupt:
            sys.exit()


def save_data(_list, sep):
    df = pandas.DataFrame(_list)
    try:
        df.to_csv('filev2.csv', index=False, sep=',', mode='a', header=False, decimal=',')
        # append(df, filename='filev2.xlsx', startrow=None, sheet_name='Sheet1', truncate_sheet=True,engine="openpyxl")
        _list.clear()
    except FileNotFoundError:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO DATAprint [file not found]{Style.RESET_ALL}")
    except PermissionError:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO DATAprint [resource busy]{Style.RESET_ALL}")
    except:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO DATAprint [generic error]{Style.RESET_ALL}")


def save_trade(_list, sep, db_data, tg_data):
    print(_list)
    df = pandas.DataFrame(_list)
    try:
        # with open('file_trade.xlsx', 'a') as f:
        df.to_csv("file_trade.csv", sep=',', mode='a', index=False, header=False, decimal=',')
        # append(df, filename='file_trade.xlsx', startrow=None, sheet_name='Sheet1', truncate_sheet=True,engine="openpyxl")
    except FileNotFoundError:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO TRADELIST [file not found]{Style.RESET_ALL}")
    except PermissionError:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO TRADELIST [resource busy]{Style.RESET_ALL}")
    except TypeError as err:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO TRADELIST [type error]{Style.RESET_ALL}")
        print(err)
    except:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO DATAprint [generic error]{Style.RESET_ALL}")
    telegram(_list, tg_data)
    try:
        db(_list, db_data)
    except Exception as err:
        print(f"{Fore.RED}[ERR] ERRORE SALVATAGGIO DATABASE [generic error]{Style.RESET_ALL}")
        print(err)
        exit(100)
    pass


def append(df, filename, startrow=None, sheet_name='Sheet1', truncate_sheet=True, engine="xlrd"):
    writer = pandas.ExcelWriter(filename, engine=engine)
    try:
        writer.book = load_workbook(filename)
        if startrow is None and sheet_name in writer.book.sheetnames:
            startrow = writer.book[sheet_name].max_row
        if truncate_sheet and sheet_name in writer.book.sheetnames:
            idx = writer.book.sheetnames.index(sheet_name)
            writer.book.remove(writer.book.worksheets[idx])
            writer.book.create_sheet(sheet_name, idx)
        writer.sheets = {ws.title: ws for ws in writer.book.worksheets}
    except FileNotFoundError:
        print("e diocan pero")
    if startrow is None:
        startrow = 0
    df.to_excel(writer, sheet_name, startrow=startrow)
    writer.save()


def db(_list, db_data):
    server = db_data["dbhost"]
    database = db_data["dbname"]
    username = db_data["dbuser"]
    password = db_data["dbpass"]
    port = int(db_data["dbport"])
    conn = mysql.connector.connect(host=server, user=username, password=password, port=port, database=database)
    cursor = conn.cursor()
    date = datetime.datetime.strptime(_list[0][0], "%d/%m/%Y %H:%M:%S").strftime('%Y-%m-%d %H:%M:%S')
    add_trade = (
        "INSERT INTO `tradelist` "
        "(`side1`,`exch1`,`ask`,`side2`,`exch2`,"
        "`bid`,`depth`,"
        "`bnbbtc_in`,`trtbtc_in`,`bnbeur_in`,`trteur_in`,`bal_in`,"
        "`bnbbtc_en`,`trtbtc_en`,`bnbeur_en`,`trteur_en`,`bal_en`,`gain`,`date`,"
        "`order_id_1`,`order_id_2`,`success`) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);")
    data_trade = (
        _list[0][1], _list[0][2], _list[0][4].replace(",", "."), _list[0][5], _list[0][6],
        _list[0][7].replace(",", "."), _list[0][3].replace(",", "."),
        _list[0][8], _list[0][9], _list[0][10], _list[0][11], _list[0][12],
        _list[1][8], _list[1][9], _list[1][10], _list[1][11], _list[1][12], round(_list[1][12] - _list[0][12], 5), date,
        "1337", "1337", "1")
    cursor.execute(add_trade, data_trade)
    conn.commit()
    cursor.close()
    conn.close()


def telegram(_list, tg_data):
    message = ("EXECUTED TRADE AT " + str(_list[0][0]) + ":\nBOUGHT <b>" + str(
        round(float(_list[0][3].replace(",", ".")), 8)) + "</b> $BTC <b>" + str(
        _list[0][4]) + "</b> ON <code>" + str(
        _list[0][2]) + "</code> SOLD <b>" + str(_list[0][7]) + "</b> ON <code>" + str(
        _list[0][6]) + "</code>. CALCULATED GAIN = <b>" + str(
        round(_list[1][12] - _list[0][12], 5)) + "€</b>").replace(" ", "%20")
    bot_token = tg_data["token"]
    bot_chatID = tg_data["app_id"]
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=HTML&text=' + message
    requests.get(send_text)


def num(num):
    s = str(abs(num))
    if num >= 0:
        sign = "+"
    else:
        sign = "-"
    spc = 7 - len(s)
    s = sign + (" " * spc) + s
    if (int(num) - num) == 0:
        s = s + "0"
    if s[6] == ".":
        s = s + "0"
        s = kill_char(s, 1)
    return s


def kill_char(string, n):
    begin = string[:n]
    end = string[n + 1:]
    return begin + end


def arbomonitor(s, only_see, last_h):
    data = s.recv(1024)
    send_json = json.dumps(
        {"timestamp": str(int(datetime.datetime.now(datetime.timezone.utc).timestamp())), "status": only_see,
         "latency": int(last_h)})
    byt = send_json.encode()
    s.send(byt)
    return data.decode()


def check_api_connection():
    trt_conn = requests.get("https://www.therocktrading.com/it/")
    if not trt_conn.ok:
        print("HTTP " + str(trt_conn.status_code) + ", error 10")
        return False
    else:
        trt_conn = requests.get("https://api.therocktrading.com/")
        if not trt_conn.ok:
            print("HTTP " + str(trt_conn.status_code) + ", error 12")
            return False
    bnb_conn = requests.get("https://api1.binance.com/")
    if not bnb_conn.ok:
        print("HTTP " + str(bnb_conn.status_code) + ", error 11")
        return False
    else:
        bnb_conn = requests.get("https://api.therocktrading.com/")
        if not bnb_conn.ok:
            print("HTTP " + str(bnb_conn.status_code) + ", error 13")
            return False
        else:
            bnb_conn = requests.get("https://api1.binance.com/wapi/v3/systemStatus.html")
            if bnb_conn.json()["status"] != 0:
                print("HTTP " + str(bnb_conn.status_code) + ", error 14")
                return False
    return True
