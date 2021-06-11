# Arbobotti
### Usage

    pip3 install pandas python-binance krakenex lxml pykrakenapi openpyxl colorama matplotlib mysql.connector telebot telethon python-gnupg pusher py4j 


### File generated or needed
keydict.txt

    {"trt_apikey": [API KEY],"trt_secret":[SECRET KEY],
    "bnb_apikey":[API KEY],"bnb_secret":[SECREY KEY]}
    
config.yaml
    
    name: <istance name>
    taker_fee_krk: 0.0024
    taker_fee_trt: 0.002
    taker_fee_bnb: 0.00075
    save_interval: 20
    save_trade_interval: 50
    fee_interval: 100
    rate: 5
    prod_threshold: 0.15
    sleep_check_order: 20
    min_balance: 0.0005
    balance_interval: 50
    graph: True
    trade_tp: Taker
    max_each_trade: 0.85
    only_see: 1
    sep: ','
    gpg: /usr/bin/gpg
    dip: 51.75.126.181
    threshold: 60
    null: null
    balancing:
        banking: True
        threshold: 0.6
        IBAN: <SEPA IBAN>
        IBAN_exch_0: <SEPA IBAN>
        reference_exch_0: <TRT REFERENCE>
        recipient_exch_0: The Rock Trading srl
        IBAN_exch_1: <SEPA IBAN>
        reference_exch_1: 6940
        recipient_exch_1: Binance
        recipient: <RECIPIENT>
        username: <HYPE USERNAME>
    
version
    
    v1.0
    
### Start
    cd arbobotti
    py /arbo.py
