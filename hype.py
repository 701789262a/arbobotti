#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime, date
from uuid import uuid4
import requests
import getpass
from banking import Banking
from utils import loginrequired


class Hype(Banking):
    ENROLL_URL = "https://api.hype.it/v2/auth/hypeconnector.aspx"
    PROFILE_URL = "https://api.hype.it/v1/rest/u/profile"
    BALANCE_URL = "https://api.hype.it/v1/rest/u/balance"
    CARD_URL = "https://api.hype.it/v1/rest/your/card"
    MOVEMENTS_URL = "https://api.hype.it/v1/rest/m/last/{}"
    CHECK_IBAN_URL = "https://api.hype.it/v1/rest/payments/sct-transfers/check"
    INSTANT_URL = "https://api.hype.it/v1/rest/payments/sct-transfers/instantavailability"
    SEND_URL = "https://api.hype.it/v1/rest/payments/sct-transfers"

    APP_VERSION = "5.1.6"
    DEVICE_ID = str(uuid4()).replace("-", "") + "hype"
    DEVICE_INFO = json.dumps({
        "jailbreak": "false",
        "osversion": "13.3.1",
        "model": "iPhone11,2"
    })

    def __init__(self):
        self._username = None
        self.newids = None
        self.bin = None
        self.checksum = None
        super().__init__()

    @loginrequired
    def check_iban(self, limit=5):
        return self._api_request(method="GET", url=self.CHECK_IBAN_URL.format(limit))

    def login(self, username, password, birthdate):
        if isinstance(birthdate, datetime) or isinstance(birthdate, date):
            dob = birthdate.strftime("%d/%m/%Y")
        elif isinstance(birthdate, str):
            dob = datetime.fromisoformat(birthdate).strftime("%d/%m/%Y")
        elif birthdate is None:
            dob = None
        else:
            raise ValueError("Invalid birth date")
        enroll1 = self._session.post(
            self.ENROLL_URL,
            data={
                "additionalinfo": self.DEVICE_INFO,
                "codiceinternet": username,
                "datanascita": dob,
                "deviceid": self.DEVICE_ID,
                "function": "FREE/LOGINFIRSTSTEP.SPR",
                "pin": password,
                "platform": "IPHONE"
            },
            timeout=10
        )
        try:
            if enroll1.json()["Check"] != "OK":
                raise self.AuthenticationError("Login failed")
        except json.decoder.JSONDecodeError:
            raise self.AuthenticationError("Failed to parse response for login request")
        except KeyError:
            raise self.AuthenticationError("Login failed")
        enroll2 = self._session.post(
            self.ENROLL_URL,
            data={
                "additionalinfo": self.DEVICE_INFO,
                "deviceid": self.DEVICE_ID,
                "function": "INFO/ENROLLBIO.SPR",
                "platform": "IPHONE"
            },
            timeout=10
        )
        try:
            if enroll2.json()["ErrorMessage"] != "":
                raise self.AuthenticationError("Server returned error: " + enroll2.json()["ErrorMessage"])
        except json.decoder.JSONDecodeError:
            raise self.RequestException("Failed to parse response for bioToken request")
        except KeyError:
            raise self.AuthenticationError("Missing data in response for bioToken request")
        self.bin = enroll2.json()["Bin"]
        self._username = username

    def otp2fa(self, code):
        if self._username is None:
            raise Exception("Please login() before verifying OTP code")
        otp = self._session.post(
            self.ENROLL_URL,
            data={
                "additionalinfo": self.DEVICE_INFO,
                "codiceinternet": self._username,
                "deviceid": self.DEVICE_ID,
                "function": "FREE/LOGINSECONDSTEP.SPR",
                "pwd": str(code),
                "platform": "IPHONE"
            },
            timeout=10
        )
        try:
            if otp.json()["Check"] != "OK":
                raise self.AuthenticationError("OTP verification failed. Please login() again")
        except json.decoder.JSONDecodeError:
            raise self.RequestException("Failed to parse response for OTP verification request")
        except KeyError:
            raise self.AuthenticationError("OTP verification failed. Please login() again")
        self.checksum = otp.json()["Checksum"]
        self.token = self._session.cookies.get_dict()["token"]
        self.newids = self._session.cookies.get_dict()["newids"]
        self._session = requests.Session()
        self._session.headers.update({
            "hype_token": self.token,
            "newids": self.newids,
            "App-Version": self.APP_VERSION
        })

    @loginrequired
    def renew(self):
        """
        Token renewal
        """
        renewal = self._session.post(
            self.ENROLL_URL,
            data={
                "additionalinfo": self.DEVICE_INFO,
                "bin": self.bin,
                "checksum": self.checksum,
                "deviceid": self.DEVICE_ID,
                "function": "FREE/LOGINFIRSTSTEPFA.SPR",
                "platform": "IPHONE"
            },
            timeout=10
        )
        try:
            if renewal.json()["Check"] != "OK":
                raise self.AuthenticationError("Renewal failed")
        except json.decoder.JSONDecodeError:
            raise self.AuthenticationError("Failed to parse response for renewal request")
        except KeyError:
            raise self.AuthenticationError("Renewal failed")
        reenroll = self._session.post(
            self.ENROLL_URL,
            data={
                "additionalinfo": self.DEVICE_INFO,
                "deviceid": self.DEVICE_ID,
                "function": "INFO/ENROLLBIO.SPR",
                "platform": "IPHONE"
            },
            timeout=10
        )
        try:
            if reenroll.json()["ErrorMessage"] != "":
                raise self.AuthenticationError("Server returned error: " + reenroll.json()["ErrorMessage"])
        except json.decoder.JSONDecodeError:
            raise self.RequestException("Failed to parse response for bioToken request")
        except KeyError:
            raise self.AuthenticationError("Missing data in response for bioToken request")
        self.token = self._session.cookies.get_dict()["token"]
        self.newids = self._session.cookies.get_dict()["newids"]
        self._session = requests.Session()
        self._session.headers.update({
            "hype_token": self.token,
            "newids": self.newids,
            "App-Version": self.APP_VERSION
        })
        self.bin = reenroll.json()["Bin"]

    @loginrequired
    def get_movements(self, limit=5):
        return self._api_request(method="GET", url=self.MOVEMENTS_URL.format(limit))

    @loginrequired
    def check_instant(self, iban):
        return requests.post(self.INSTANT_URL, json={"iban": iban, "amount": 1}, headers=self._session.headers).json()

    def transfer(self, iban, to, amount,causal):
        resp = requests.post(self.SEND_URL, json={
            "iban": iban,
            "name": to,
            "causal": causal,
            "date": datetime.utcnow().isoformat(),
            "amount": amount,
            "isInstantPayment": "true"
        }, headers=self._session.headers).json()
        if resp['internalErrror'] == '009':
            otp = getpass.getpass('OTP REQUIRED: ')
            return requests.post(self.SEND_URL, json={'requestId': resp['requestId'], 'otp': otp},
                                 headers=self._session.headers).json()
