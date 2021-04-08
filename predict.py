import csv
import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.models import Sequential

prediction_days = 2
start_date = '25/03/2021'
end_date = '03/04/2021'

data = pd.read_csv(r'filev2server.csv', index_col="DATE", parse_dates=True, delimiter=",")
data.index = pd.to_datetime(data.index)
data = data.stack().str.replace(',', '.').unstack()
data_train = data[(data.index >= '2021-03-25') & (data.index < '2021-03-29')]["TRT-BNB"]
print("primo",data_train['TRT-BNB'].astype(str).astype(float))
data_train.astype(str).astype(float).plot()
plt.show()
scaler = MinMaxScaler(feature_range=(0, 1))
data_train = np.array(data_train).reshape(-1, 1)
scaled_data = scaler.fit_transform(data_train)

x_train = []
y_train = []

for x in range(prediction_days, len(scaled_data)):
    x_train.append(scaled_data[x - prediction_days:x, 0])
    y_train.append(scaled_data[x, 0])

x_train, y_train = np.array(x_train), np.array(y_train)
x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
print("ytrain",y_train)
model = Sequential()

model.add(LSTM(units=50, return_sequences=True, input_shape=(x_train.shape[1], 1)))
model.add(Dropout(0.2))
model.add(LSTM(units=50,return_sequences=True))
model.add(Dropout(0.2))
model.add(LSTM(units=25))
model.add(Dropout(0.2))
model.add(Dense(units=1))

model.compile(optimizer='adam', loss='mean_squared_error')
model.fit(x_train, y_train, epochs=2, batch_size=128)

start_test = '04/02/2021'
end_test = '07/02/2021'

''' Test model with existing data '''

data_test = data[(data.index >= '2021-04-01') & (data.index < '2021-04-04')]["TRT-BNB"]
print("train",data_test['TRT-BNB'].astype(str).astype(float))
data_test.astype(str).astype(float).plot()
plt.show()
scaler = MinMaxScaler(feature_range=(0, 1))
data_test = np.array(data_test).reshape(-1, 1)
scaled_data = scaler.fit_transform(data_test)
print("scaled",scaled_data)
print(data_test[len(data_test) - 1])
print(data_test[1])

model_input = np.array(data_test).reshape(-1, 1)
model_input = scaler.transform(model_input)
x_test = []
for x in range(100, len(model_input)):
    x_test.append(model_input[x - 100:x, 0])

x_test = np.array(x_test)
x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))
print("xtest",x_test.shape)
predicted_prices = model.predict(x_test)
predicted_prices = scaler.inverse_transform(predicted_prices)

real_data =data[(data.index >= '2021-04-05') & (data.index < '2021-04-06')]["TRT-BNB"]
real_data = np.array(real_data)
real_data = np.array(real_data).reshape(-1, 1)
real_data = scaler.transform(real_data)
trial=np.array(real_data)
trial=np.reshape(trial, (trial.shape[0], trial.shape[1], 1))
print ("bobotto")
prediction = model.predict(trial)
print("due",prediction)

prediction = scaler.inverse_transform(prediction)

print("predicted",prediction)
