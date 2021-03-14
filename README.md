# Arbobotti
### Usage

    pip install pandas
    pip install python-binance
    pip install krakenex
    pip install pykrakenapi
    pip install openpyxl
    pip install matplotlib
    pip install mysql.connector
    pip install telebot
    pip install telethon
    pip install gnupg


### File generated or needed
keydict.txt

    {"trt_apikey": [API KEY],"trt_secret":[SECRET KEY],
    "bnb_apikey":[API KEY],"bnb_secret":[SECREY KEY]}
    
config.txt
    
    taker_fee_krk = 0.0024
    taker_fee_trt = 0.02
    taker_fee_bnb = 0.00075
    save_interval = 20
    save_trade_interval = 50
    fee_interval = 100
    rate = 5
    prod_threshold = 0.01
    sleep_check_order = 2
    min_balance = 10
    balance_interval = 50
    graph = True
    
version
    
    v1.0
    
### Start
    cd arbobotti
    py /arbo.py
