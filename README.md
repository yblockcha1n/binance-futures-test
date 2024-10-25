## 各種ログ

### src/testnet/order.py

パラメータ例
```ini
[TRADING]
SYMBOL = BTCUSDT
LEVERAGE = 125
SIDE = BUY
ORDER_TYPE = MARKET
USDT_AMOUNT = 100
REDUCE_ONLY = false
```

<details>

<summary>成功ログ</summary>

```
2024-10-26 01:32:02,936 - __main__ - INFO - Symbol info loaded: {'symbol': 'BTCUSDT', 'price_precision': 2, 'quantity_precision': 3, 'min_price': 261.1, 'max_price': 809, 'step_size': 0.001, 'min_notional': 100.0}
2024-10-26 01:32:02,985 - __main__ - INFO - Leverage set to 125x for BTCUSDT
2024-10-26 01:32:03,025 - __main__ - INFO - Quantity calculation: USDT Amount: 100.0, Price: 67398.54374468, Final Quantity: 0.002, Notional Value: 134.79708748936002
2024-10-26 01:32:03,025 - __main__ - INFO - Placing order with params: {'symbol': 'BTCUSDT', 'side': 'BUY', 'order_type': 'MARKET', 'quantity': 0.002, 'reduce_only': Fal
2024-10-26 01:32:03,123 - __main__ - INFO - Order placed successfully: {'orderId': 4063180293, 'symbol': 'BTCUSDT', 'status': 'NEW', 'clientOrderId': 'HtJDbeQMaLLqMSWcDq2', 'executedQty': '0.000', 'cumQty': '0.000', 'cumQuote': '0.00000', 'timeInForce': 'GTC', 'type': 'MARKET', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'MARKET', 'priceMatch': 'NONE', 'selfTradePreventionMode': 'NONE', 'goodTillDate': 0, 'updateTime': 1729873922419}
Order Response: {'orderId': 4063180293, 'symbol': 'BTCUSDT', 'status': 'NEW', 'clientOrderId': 'HtJDbeQMaLLqMSWcDq2oaP', 'price': '0.00', 'avgPrice': '0.00', 'origQty': e': '0.00000', 'timeInForce': 'GTC', 'type': 'MARKET', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0.00', 'workingTMARKET', 'priceMatch': 'NONE', 'selfTradePreventionMode': 'NONE', 'goodTillDate': 0, 'updateTime': 1729873922419}
2024-10-26 01:32:03,167 - __main__ - INFO - Position info retrieved: [{'symbol': 'BTCUSDT', 'positionAmt': '0.002', 'entryPrice': '67634.0', 'breakEvenPrice': '67661.0537091251', 'liquidationPrice': '0', 'leverage': '125', 'maxNotionalValue': '50000', 'marginType': 'cross', 'isolatedMargin': '0.00000000', 'isAutoAddMargin': 'false', 'pollet': '0', 'updateTime': 1729873922419, 'isolated': False, 'adlQuantile': 0}]
Position Info: [{'symbol': 'BTCUSDT', 'positionAmt': '0.002', 'entryPrice': '67634.0', 'breakEvenPrice': '67661.0536', 'markPrice': '67398.54374468', 'unRealizedProfit':
'maxNotionalValue': '50000', 'marginType': 'cross', 'isolatedMargin': '0.00000000', 'isAutoAddMargin': 'false', 'positionSide': 'BOTH', 'notional': '134.79708748', 'isolalse, 'adlQuantile': 0}]
```

</details>
