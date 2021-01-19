import binascii
import hashlib
import hmac
import json
import queue
import time
from threading import Thread

import krakenex
import pandas as pd
import requests
from binance.client import Client
from pykrakenapi import KrakenAPI

q1 = queue.Queue()
q2 = queue.Queue()
q3 = queue.Queue()


def create_sha256_signature(key, message):
    byte_key = binascii.unhexlify(key)
    message = message.encode()
    return hmac.new(byte_key, message, hashlib.sha256).hexdigest().upper()


class Operation:
    def __init__(self, apikey_trt, secret_trt, apikey_krk, secret_krk, apikey_bnb, secret_bnb):
        self.apikey_trt = apikey_trt
        self.secret_trt = secret_trt
        self.apikey_krk = apikey_krk
        self.secret_krk = secret_krk
        self.apikey_bnb = apikey_bnb
        self.secret_bnb = secret_bnb

    def trade(self, exchange, fund_id, side, amount, price):
        nonce = str(int(time.time() * 1e6))
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/" + fund_id + "/orders"
            payload_trt = {"fund_id": "BTCEUR", "side": "sell", "amount": amount, "price": price}
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()

            _headers = {'User-Agent': 'PyRock v1', "Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.post(url, data=json.dumps(payload_trt), headers=_headers)
            return resp.text
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = k.add_standard_order(fund_id, side, "limit", str(amount), str(price))
            resp = str(resp).replace("\'", "\"")
            return resp
        elif exchange == "bnb":
            client = Client(self.apikey_bnb, self.apikey_bnb)
            if side == "buy":
                order = client.order_limit_buy(
                    symbol=fund_id,
                    quantity=amount,
                    price=price)
            elif side == "sell":
                order = client.order_limit_sell(
                    symbol=fund_id,
                    quantity=amount,
                    price=price)
            return order

    def balance(self, exchange):
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
            client = Client(self.apikey_bnb, self.apikey_bnb)
            d["bnbbtc"] = client.get_asset_balance(asset="BTC")
            d["bnbeur"] = client.get_asset_balance(asset="EUR")
            return d

    def fee(self, exchange):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/BTCEUR"
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {"Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.get(url, headers=_headers)
            d["feetrt"] = json.loads(resp.text)["buy_fee"]
            return d
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = pd.DataFrame(k.get_trade_volume("BTCEUR")[2])
            d["feekrk"] = resp["XXBTZEUR"][0]
            return d
        elif exchange == "bnb":
            client = Client(self.apikey_bnb, self.apikey_bnb)
            resp = client.get_trade_fee(symbol="BTCEUR")
            print(resp)

    def doop(self, side, exchange, fund_id, amount, price, side2, exchange2, fund_id2, amount2, price2, side3,
             exchange3, fund_id3, amount3, price3, case):
        if case == 1:

            d = dict()
            krk_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q1, exchange, fund_id, side, amount, price))
            trt_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q2, exchange2, fund_id2, side2, amount2, price2))
            bnb_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q3, exchange3, fund_id3, side3, amount3, price3))
            trt_trade.start()
            krk_trade.start()
            bnb_trade.start()
            trt_trade.join()
            krk_trade.join()
            bnb_trade.join()
            try:
                d["krk"] = json.loads(q1.get())["txid"]
            except:
                d["krk"] = "ERROR"
            try:
                d["trt"] = json.loads(q2.get())["order"]
            except:
                d["trt"] = "ERROR"

            return d
        if case == 2:
            d = dict()
            krk_balance = Thread(target=lambda q, arg1: q.put(
                self.balance(arg1)),
                                 args=(q1, exchange))
            trt_balance = Thread(target=lambda q, arg1: q.put(
                self.balance(arg1)),
                                 args=(q2, exchange2))
            bnb_balance = Thread(target=lambda q, arg1: q.put(
                self.balance(arg1)),
                                 args=(q3, exchange3))
            trt_balance.start()
            krk_balance.start()
            bnb_balance.start()
            trt_balance.join()
            krk_balance.join()
            bnb_balance.join()

            d = (q1.get(), q2.get(), q3.get())

            return d
        if case == 3:
            d = dict()
            krk_fee = Thread(target=lambda q, arg1: q.put(
                self.fee(arg1)),
                             args=(q1, exchange))
            trt_fee = Thread(target=lambda q, arg1: q.put(
                self.fee(arg1)),
                             args=(q2, exchange2))
            bnb_fee = Thread(target=lambda q, arg1: q.put(
                self.fee(arg1)),
                             args=(q3, exchange3))
            trt_fee.start()
            krk_fee.start()
            bnb_fee.start()
            trt_fee.join()
            krk_fee.join()
            bnb_fee.join()

            d = (q1.get(), q2.get(), q3.get())
            return d
