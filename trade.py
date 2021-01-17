import binascii
import hashlib
import hmac
import json
import queue
import time
from threading import Thread

import krakenex
import requests
from pykrakenapi import KrakenAPI

q1 = queue.Queue()
q2 = queue.Queue()


def create_sha256_signature(key, message):
    byte_key = binascii.unhexlify(key)
    message = message.encode()
    return hmac.new(byte_key, message, hashlib.sha256).hexdigest().upper()


class Operation:
    def __init__(self, apikey_trt, secret_trt, apikey_krk, secret_krk):
        self.apikey_trt = apikey_trt
        self.secret_trt = secret_trt
        self.apikey_krk = apikey_krk
        self.secret_krk = secret_krk

    def trade(self,exchange, fund_id,type, amount, price):
        nonce = str(int(time.time() * 1e6))
        if exchange == "trt":
            url = "https://api.therocktrading.com/v1/funds/" + fund_id + "/orders"
            payload_trt = {"fund_id": fund_id, "side": type, "amount": amount, "price": price}
            signature = hmac.new(self.secret_trt.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()

            _headers = {'User-Agent': 'PyRock v1', "Content-Type": "application/json", "X-TRT-KEY": self.apikey_trt,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = str(requests.post(url, data=json.dumps(payload_trt), headers=_headers, timeout=30))
            return resp
        elif exchange == "krk":
            api = krakenex.API(self.apikey_krk, self.secret_krk)
            k = KrakenAPI(api)
            resp = k.add_standard_order(fund_id, type, "limit", str(amount), str(price))
            resp = str(resp).replace("\'", "\"")
            return resp

    def dotrade(self, type, exchange, fund_id, amount, price, type2, exchange2, fund_id2, amount2, price2):
        d = dict()
        trt_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4,arg5: q.put(
            self.trade(arg1, arg2, arg3, arg4,arg5)),
                           args=(q1, exchange, fund_id, type, amount, price))
        krk_trade = Thread(target=lambda q, arg1, arg2, arg3, arg4,arg5: q.put(
            self.trade(arg1, arg2, arg3, arg4,arg5)),
                           args=(q2, exchange2, fund_id2, type2, amount2, price2))
        trt_trade.start()
        krk_trade.start()
        trt_trade.join()
        krk_trade.join()
        d['trt'] = json.loads(q1.get())['order']
        d['krk'] = json.loads(q2.get())['txid']
        return d

    def balance(self,exchange, fund, apikey, secret):
        nonce = str(int(time.time() * 1e6))
        if exchange == "trt":

            url = "https://api.therocktrading.com/v1/balances/" + fund
            signature = hmac.new(secret.encode(), msg=(str(nonce) + url).encode(),
                                 digestmod=hashlib.sha512).hexdigest()
            _headers = {'User-Agent': 'PyRock v1', "Content-Type": "application/json", "X-TRT-KEY": apikey,
                        "X-TRT-SIGN": signature, "X-TRT-NONCE": nonce}
            resp = requests.post(url, headers=_headers, timeout=30)
            answ = json.loads(str(resp))['balance']
            return answ
        elif exchange == "krk":
            api = krakenex.API(apikey, secret)
            k = KrakenAPI(api)
            resp = k.get_trade_balance(asset=fund)
            resp = str(resp).replace("\'", "\"")
            return resp
