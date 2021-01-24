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
    def __init__(self, apikey_trt, secret_trt, apikey_krk, secret_krk, apikey_bnb, secret_bnb, exchange_list):
        self.apikey_trt = apikey_trt
        self.secret_trt = secret_trt
        self.apikey_krk = apikey_krk
        self.secret_krk = secret_krk
        self.apikey_bnb = apikey_bnb
        self.secret_bnb = secret_bnb
        self.exchange_list = exchange_list

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
            client = Client(self.apikey_bnb, self.secret_bnb)
            try:
                if side == "buy":
                    order = client.order_limit_buy(
                        symbol=fund_id,
                        quantity=amount,
                        price=price)
                    print("ciaone", order)
                elif side == "sell":
                    order = client.order_limit_sell(
                        symbol=fund_id,
                        quantity=amount,
                        price=price)
                    print("ciaone", order)
            except Exception:
                order = "ERR"
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
            client = Client(self.apikey_bnb, self.secret_bnb)
            d["bnbbtc"] = float(client.get_asset_balance(asset="BTC")["free"])
            d["bnbeur"] = float(client.get_asset_balance(asset="EUR")["free"])
            return d

    def balancethreading(self):
        d = dict()
        if "krk" in self.exchange_list:
            krk_balance = Thread(target=lambda q, arg1: q.put(
                self.balance(arg1)),
                                 args=(q2, "krk"))
            krk_balance.start()
        if "trt" in self.exchange_list:
            trt_balance = Thread(target=lambda q, arg1: q.put(
                self.balance(arg1)),
                                 args=(q1, "trt"))
            trt_balance.start()
        if "bnb" in self.exchange_list:
            bnb_balance = Thread(target=lambda q, arg1: q.put(
                self.balance(arg1)),
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
                self.order(arg1, arg2)),
                               args=(q2, "trt", order1))
            trt_order.start()
        if "krk" in self.exchange_list:
            krk_order = Thread(target=lambda q, arg1, arg2: q.put(
                self.order(arg1, arg2)),
                               args=(q2, "krk", order2))
            krk_order.start()
        if "bnb" in self.exchange_list:
            bnb_order = Thread(target=lambda q, arg1, arg2: q.put(
                self.order(arg1, arg2)),
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
    def cancel(self,exchange,order):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/BTCEUR/orders/" + order
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {"Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.delete(url, headers=_headers)
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
            client = Client(self.apikey_bnb, self.secret_bnb)
            resp = client.cancel_order(symbol="BTCEUR", orderId=order)
            d["status_bnb"] = resp["status"]
            return d

    def cancelthreading(self,order1,order2):
        d = dict()
        if "trt" in self.exchange_list:
            trt_cancel = Thread(target=lambda q, arg1, arg2: q.put(
                self.cancel(arg1, arg2)),
                               args=(q1, "trt", order1))
            trt_cancel.start()
        if "krk" in self.exchange_list:
            krk_cancel = Thread(target=lambda q, arg1, arg2: q.put(
                self.cancel(arg1, arg2)),
                               args=(q2, "krk", order2))
            krk_cancel.start()
        if "bnb" in self.exchange_list:
            bnb_cancel = Thread(target=lambda q, arg1, arg2: q.put(
                self.cancel(arg1, arg2)),
                               args=(q2, "bnb", order2))
            bnb_cancel.start()
        try:
            trt_cancel.join()

            d.update(q1.get())
        except:
            pass
        try:
            krk_cancel.join()

            d.update(q2.get())
        except:
            pass
        try:
            bnb_cancel.join()

            d.update(q2.get())
        except Exception:
            pass
        return d

    def order(self,exchange,order):
        nonce = str(int(time.time() * 1e6))
        d = dict()
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/BTCEUR/orders/"+order
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {"Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.get(url, headers=_headers)
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
            client = Client(self.apikey_bnb, self.secret_bnb)
            resp = client.get_order(symbol="BTCEUR",orderId=order)
            d["status_bnb"] = resp["status"]
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
            client = Client(self.apikey_bnb, self.secret_bnb)
            resp = client.get_trade_fee(symbol="BTCEUR")
            d["feebnb"] = resp["tradeFee"][0]["taker"]
            return d

    def feethreading(self):
        d = dict()
        if "krk" in self.exchange_list:
            krk_fee = Thread(target=lambda q, arg1: q.put(
                self.fee(arg1)),
                             args=(q1, "krk"))
            krk_fee.start()
        if "trt" in self.exchange_list:
            trt_fee = Thread(target=lambda q, arg1: q.put(
                self.fee(arg1)),
                             args=(q2, "trt"))
            trt_fee.start()
        if "bnb" in self.exchange_list:
            bnb_fee = Thread(target=lambda q, arg1: q.put(
                self.fee(arg1)),
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
                self.trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q1, exchange, fund_id, side, amount, price))
            trt_trade.start()
        if "krk" in self.exchange_list:
            krk_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.trade(arg1, arg2, arg3, arg4, arg5)),
                               args=(q2, exchange2, fund_id2, side2, amount2, price2))
            krk_trade.start()
        if "bnb" in self.exchange_list:
            bnb_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4, arg5: q.put(
                self.trade(arg1, arg2, arg3, arg4, arg5)),
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
            value = json.loads(q1.get())
            if value["errors"]:
                d["trt"] = value["errors"][0]["message"], "ERROR"
            else:
                d["trt"] = value["order"]
        except:
            d["trt"] = "ERROR"
        try:
            d[self.exchange_list[1]] = json.loads(q2.get())["order"]
        except:
            d[self.exchange_list[1]] = "ERROR"

        return d
