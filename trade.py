import binascii
import hashlib
import hmac
import json
import queue
import time
from threading import Thread

import binance
import krakenex
import pandas as pd
import requests
from binance import exceptions
from binance.client import Client
from colorama import Fore
from colorama import Style
from pykrakenapi import KrakenAPI

q1 = queue.Queue()
q2 = queue.Queue()
q3 = queue.Queue()


def create_sha256_signature(key, message):
    byte_key = binascii.unhexlify(key)
    message = message.encode()
    return hmac.new(byte_key, message, hashlib.sha256).hexdigest().upper()


class Operation:
    def __init__(self, apikey_trt, secret_trt, apikey_krk, secret_krk, apikey_bnb, secret_bnb, exchange_list):
        self.apikey_trt = apikey_trt
        self.secret_trt = secret_trt
        self.apikey_krk = apikey_krk
        self.secret_krk = secret_krk
        self.apikey_bnb = apikey_bnb
        self.secret_bnb = secret_bnb
        self.exchange_list = exchange_list
        self.client = Client(self.apikey_bnb, self.secret_bnb)
        self.trt = []
        self.bnb = []
        self.len = 0
        self.requests_used = 0


    def __trade(self, exchange, fund_id, side, amount, price):
        nonce = str(int(time.time() * 1e6))
        amount = round(amount, 8)
        if side == 'sell':
            price = price - 5000
        elif side == 'buy':
            price = price + 5000
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/" + fund_id + "/orders"
            payload_trt = {"fund_id": "BTCEUR", "side": side, "amount": amount, "price": price}
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()

            _headers = {'User-Agent': 'PyRock v1', "Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.post(url, data=json.dumps(payload_trt), headers=_headers)
            try:
                return json.loads(resp.text)
            except KeyError:
                return "ERROR"
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = k.add_standard_order(fund_id, side, "limit", str(amount), str(price))
            resp = str(resp).replace("\'", "\"")
            return resp
        elif exchange == "bnb":

            if side == "buy":
                order = self.client.order_market_buy(
                    symbol=fund_id,
                    quantity=round(amount, 5)
                )
            elif side == "sell":
                order = self.client.order_market_sell(
                    symbol=fund_id,
                    quantity=round(amount, 5)
                )
            return dict(order)

    def __balance(self, exchange):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        if exchange == "trt":

            url = "https://api.therocktrading.com/v1/balances"
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {"Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.get(url, headers=_headers)
            d["trtbtc"] = json.loads(resp.text)["balances"][0]["balance"]
            d["trteur"] = json.loads(resp.text)["balances"][8]["balance"]
            return d
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = k.get_account_balance()
            d["krkbtc"] = resp["vol"]["XXBT"]
            d["krkbch"] = resp["vol"]["BCH"]
            return d
        elif exchange == "bnb":
            is_fine = True
            while is_fine:
                try:
                    is_fine = False
                except ConnectionError:
                    print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")
            try:
                d["bnbbtc"] = float(self.client.get_asset_balance(asset="BTC")["free"])
                d["bnbeur"] = float(self.client.get_asset_balance(asset="EUR")["free"])
                self.requests_used = self.client.response.headers['x-mbx-used-weight-1m']
            except Exception:
                d["bnbbtc"] = float(self.client.get_asset_balance(asset="BTC")["free"])
                d["bnbeur"] = float(self.client.get_asset_balance(asset="EUR")["free"])
            return d

    def balancethreading(self):
        d = dict()
        if "krk" in self.exchange_list:
            krk_balance = Thread(target=lambda q, arg1: q.put(
                self.__balance(arg1)),
                                 args=(q2, "krk"))
            krk_balance.start()
        if "trt" in self.exchange_list:
            trt_balance = Thread(target=lambda q, arg1: q.put(
                self.__balance(arg1)),
                                 args=(q1, "trt"))
            trt_balance.start()
        if "bnb" in self.exchange_list:
            bnb_balance = Thread(target=lambda q, arg1: q.put(
                self.__balance(arg1)),
                                 args=(q2, "bnb"))
            bnb_balance.start()
        try:
            trt_balance.join()
            d.update(q1.get())
        except:
            pass
        try:
            krk_balance.join()
            d.update(q2.get())
        except:
            pass
        try:
            bnb_balance.join()
            d.update(q2.get())
        except:
            pass
        return d

    def orderthreading(self, order1, order2):
        d = dict()
        if "trt" in self.exchange_list:
            trt_order = Thread(target=lambda q, arg1, arg2: q.put(
                self.__order(arg1, arg2)),
                               args=(q2, "trt", order1))
            trt_order.start()
        if "krk" in self.exchange_list:
            krk_order = Thread(target=lambda q, arg1, arg2: q.put(
                self.__order(arg1, arg2)),
                               args=(q2, "krk", order2))
            krk_order.start()
        if "bnb" in self.exchange_list:
            bnb_order = Thread(target=lambda q, arg1, arg2: q.put(
                self.__order(arg1, arg2)),
                               args=(q3, "bnb", order2))
            bnb_order.start()
        try:
            krk_order.join()

            d.update(q1.get())
        except:
            pass
        try:
            trt_order.join()

            d.update(q2.get())
        except:
            pass
        try:
            bnb_order.join()

            d.update(q3.get())
        except Exception:
            pass
        return d

    def __order(self, exchange, order):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/BTCEUR/orders/" + order
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {"Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.get(url, headers=_headers)
            print("trt", resp)
            d["status_trt"] = json.loads(resp.text)["status"]
            return d
        elif exchange == "krk":
            print("FUNCTION NOT ENABLED ON KRAKEN EXCHANGE, USE OTHER EXCHANGES FOR THIS FEATURE TO WORK")
            exit(2)
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = pd.DataFrame(k.get_trade_volume("BTCEUR")[2])
            d["feekrk"] = resp["XXBTZEUR"][0]
            return d
        elif exchange == "bnb":
            resp = self.client.get_order(symbol="BTCEUR", orderId=order)
            print("binance", resp)
            d["status_bnb"] = resp["status"]
            return d

    def withdraw(self, exchange, coin, address, amount):
        if exchange == "trt":
            nonce = str(int(time.time() * 1e6))
            url = 'https://api.therocktrading.com/v1/atms/withdraw'
            payload_trt = {"currency": coin, "address": address, "amount": amount}
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()

            _headers = {'User-Agent': 'PyRock v1', "Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.post(url, data=json.dumps(payload_trt), headers=_headers)
            return json.loads(resp.text)['transaction_id']
        elif exchange == "bnb":
            resp = self.client.withdraw(asset=coin.upper(), address=address, amount=amount)
            return resp['id']

    def __fee(self, exchange):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/BTCEUR"
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {"Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.get(url, headers=_headers)
            d["feetrttaker"] = json.loads(resp.text)["buy_fee"]
            d["feetrtmaker"] = json.loads(resp.text)["sell_fee"]

            return d
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = pd.DataFrame(k.get_trade_volume("BTCEUR")[2])
            d["feekrk"] = resp["XXBTZEUR"][0]
            return d
        elif exchange == "bnb":
            resp = self.client.get_trade_fee(symbol="BTCEUR")
            print(resp)
            d["feebnbtaker"] = resp["tradeFee"][0]["taker"]
            d["feebnbmaker"] = resp["tradeFee"][0]["maker"]
            return d

    def feethreading(self):
        d = dict()
        if "krk" in self.exchange_list:
            krk_fee = Thread(target=lambda q, arg1: q.put(
                self.__fee(arg1)),
                             args=(q1, "krk"))
            krk_fee.start()
        if "trt" in self.exchange_list:
            trt_fee = Thread(target=lambda q, arg1: q.put(
                self.__fee(arg1)),
                             args=(q2, "trt"))
            trt_fee.start()
        if "bnb" in self.exchange_list:
            bnb_fee = Thread(target=lambda q, arg1: q.put(
                self.__fee(arg1)),
                             args=(q3, "bnb"))
            bnb_fee.start()
        try:
            krk_fee.join()

            d.update(q1.get())
        except:
            pass
        try:
            trt_fee.join()

            d.update(q2.get())
        except:
            pass
        try:
            bnb_fee.join()

            d.update(q3.get())
        except Exception:
            pass
        return d

    def tradethreading(self, side, exchange, fund_id, amount, price, side2, exchange2, fund_id2, amount2, price2):
        d = dict()
        if "trt" in self.exchange_list:
            trt_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.__trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q1, exchange, fund_id, side, amount, price))
            trt_trade.start()
        if "krk" in self.exchange_list:
            krk_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.__trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q2, exchange2, fund_id2, side2, amount2, price2))
            krk_trade.start()
        if "bnb" in self.exchange_list:
            bnb_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.__trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q2, exchange2, fund_id2, side2, amount2, price2))
            bnb_trade.start()

        try:
            trt_trade.join()
        except:
            pass
        try:
            krk_trade.join()
        except:
            pass
        try:
            bnb_trade.join()
        except:
            pass

        try:
            value = q1.get()
            d["trt"] = value
        except:
            d["trt"] = "ERROR"
        try:
            d[self.exchange_list[1]] = q2.get()
        except:
            d[self.exchange_list[1]] = "ERROR"

        return d

    def min_qty_trt(self):
        try:
            resp_trt = requests.get("https://api.therocktrading.com/v1/funds/?id=BTCEUR")
            return json.loads(resp_trt.text)
        except requests.exceptions.ConnectionError:
            print(f"{Fore.RED}[ERR] CHECK INTERNET CONNECTION{Style.RESET_ALL}")
        except json.decoder.JSONDecodeError:
            print(f"{Fore.RED}[ERR] ERROR WHILE CONVERTING TO JSON [expecting value]{Style.RESET_ALL}")

    def get_requests_used(self):
        return self.requests_used