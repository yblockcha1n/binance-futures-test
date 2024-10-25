from typing import Dict, Optional
from binance.um_futures import UMFutures
from binance.error import ClientError
import logging
from pathlib import Path
import os
import math
import json
import sys
from decimal import Decimal, ROUND_DOWN
import time
import configparser

class SymbolInfo:
    def __init__(self, symbol_data: Dict):
        self.symbol = symbol_data['symbol']
        self.price_precision = symbol_data['pricePrecision']
        self.quantity_precision = symbol_data['quantityPrecision']
        self.min_price = float(symbol_data['filters'][0]['minPrice'])
        self.max_price = float(symbol_data['filters'][0]['maxPrice'])
        self.tick_size = float(symbol_data['filters'][0]['tickSize'])
        self.min_qty = float(symbol_data['filters'][1]['minQty'])
        self.max_qty = float(symbol_data['filters'][1]['maxQty'])
        self.step_size = float(symbol_data['filters'][1]['stepSize'])
        self.min_notional = float(symbol_data['filters'][5]['notional'])

    def round_step_size(self, quantity: float) -> float:
        """数量をstep_sizeに合わせて丸める（切り捨て）"""
        step_size = Decimal(str(self.step_size))
        quantity = Decimal(str(quantity))
        return float(quantity.quantize(step_size.normalize(), rounding=ROUND_DOWN))

    def round_tick_size(self, price: float) -> float:
        """価格をtick_sizeに合わせて丸める（切り捨て）"""
        tick_size = Decimal(str(self.tick_size))
        price = Decimal(str(price))
        return float(price.quantize(tick_size.normalize(), rounding=ROUND_DOWN))

class TradingParameters:
    def __init__(self, symbol: str, leverage: int, side: str, 
                 order_type: str, usdt_amount: float, reduce_only: bool = False):
        self.symbol = symbol
        self.leverage = leverage
        self.side = "BUY" if side.upper() == "LONG" else "SELL"
        self.order_type = order_type.upper()
        self.usdt_amount = usdt_amount
        self.reduce_only = reduce_only

class BinanceFuturesClient:
    def __init__(self, is_testnet: bool = False):
        """
        Binance Futures クライアントの初期化
        Args:
            is_testnet (bool): テストネットを使用するかどうか（デフォルトはメインネット）
        """
        self._validate_environment()
        self.config = self._load_configs()
        self.trading_params = self._load_trading_parameters()
        self.client = self._initialize_client(is_testnet)
        self._setup_logging()
        self.symbol_info = self._get_symbol_info(self.trading_params.symbol)
        self.logger.info(f"Symbol info loaded: {vars(self.symbol_info)}")
        
        # 実行前の確認
        if not is_testnet:
            self._confirm_mainnet_execution()

    def _validate_environment(self):
        """必要なディレクトリとファイルの存在確認"""
        required_dirs = ['logs', 'settings']
        required_files = ['settings/config.ini', 'settings/parameter.ini']
        
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                
        for file_path in required_files:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Required file not found: {file_path}")

    def _confirm_mainnet_execution(self):
        """メインネットでの実行確認"""
        print("\n" + "!"*50)
        print("WARNING: You are about to execute trades on MAINNET")
        print("Symbol:", self.trading_params.symbol)
        print("Side:", self.trading_params.side)
        print("Order Type:", self.trading_params.order_type)
        print("USDT Amount:", self.trading_params.usdt_amount)
        print("Leverage:", self.trading_params.leverage)
        print("Reduce Only:", self.trading_params.reduce_only)
        print("!"*50 + "\n")
        
        confirmation = input("Type 'YES' to confirm the execution on MAINNET: ")
        if confirmation != "YES":
            self.logger.info("Mainnet execution cancelled by user")
            sys.exit("Execution cancelled")

    def _load_configs(self) -> Dict:
        """API設定ファイルの読み込み"""
        config = configparser.ConfigParser()
        config_path = Path("settings/config.ini")
        config.read(config_path)
        
        required_keys = ['API_KEY', 'API_SECRET']
        for key in required_keys:
            if not config['BINANCE'].get(key):
                raise ValueError(f"Missing required config key: {key}")
                
        return config

    def _initialize_client(self, is_testnet: bool) -> UMFutures:
        """Binance Futuresクライアントの初期化"""
        api_key = self.config['BINANCE']['API_KEY']
        api_secret = self.config['BINANCE']['API_SECRET']
        
        # テストネットとメインネットのbase_urlを明示的に設定
        if is_testnet:
            base_url = "https://testnet.binancefuture.com"
        else:
            base_url = "https://fapi.binance.com"
            
        client = UMFutures(
            key=api_key,
            secret=api_secret,
            base_url=base_url
        )
        
        # APIキーの有効性確認
        try:
            client.account()
        except ClientError as e:
            raise ValueError(f"Invalid API credentials: {str(e)}")
            
        return client

    def prepare_and_place_order(self) -> Dict:
        """パラメータに基づいて注文を準備して発注"""
        try:
            # アカウントの残高確認
            account_info = self.client.account()
            available_balance = float(next(
                asset['availableBalance'] 
                for asset in account_info['assets'] 
                if asset['asset'] == 'USDT'
            ))
            
            if available_balance < self.trading_params.usdt_amount:
                raise ValueError(
                    f"Insufficient balance. Required: {self.trading_params.usdt_amount} USDT, "
                    f"Available: {available_balance} USDT"
                )

            # レバレッジを設定
            self._set_leverage(self.trading_params.symbol, self.trading_params.leverage)
            
            # 現在価格を取得
            current_price = self._get_current_price(self.trading_params.symbol)
            
            # 数量を計算
            quantity = self._calculate_quantity(
                self.trading_params.usdt_amount, 
                current_price
            )
            
            # 指値価格を設定
            price = None
            if self.trading_params.order_type == "LIMIT":
                adjustment = 0.99 if self.trading_params.side == "BUY" else 1.01
                raw_price = current_price * adjustment
                price = self.symbol_info.round_tick_size(raw_price)

            order_params = {
                "symbol": self.trading_params.symbol,
                "side": self.trading_params.side,
                "order_type": self.trading_params.order_type,
                "quantity": quantity,
                "reduce_only": self.trading_params.reduce_only
            }
            
            if price:
                order_params["price"] = price
                order_params["time_in_force"] = "GTC"
                
            self.logger.info(f"Placing order with params: {order_params}")
            
            # 最終確認（メインネットの場合）
            if not hasattr(self, '_confirmed_mainnet') and not self.client.base_url.startswith('https://testnet'):
                print("\nOrder Details:")
                print(json.dumps(order_params, indent=2))
                confirmation = input("\nType 'CONFIRM' to place the order: ")
                if confirmation != "CONFIRM":
                    raise ValueError("Order cancelled by user")
                self._confirmed_mainnet = True
                
            response = self.place_order(**order_params)
            
            # 注文後の情報ログ
            self.logger.info("Order placed successfully")
            self.logger.info(f"Order Response: {json.dumps(response, indent=2)}")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in prepare_and_place_order: {str(e)}")
            raise

    def get_position_info(self) -> Dict:
        """現在のポジション情報を取得"""
        try:
            positions = self.client.get_position_risk(
                symbol=self.trading_params.symbol
            )
            self.logger.info(f"Position info retrieved: {positions}")
            return positions
        except ClientError as e:
            self.logger.error(f"Failed to get position info: {e.error_message}")
            raise

if __name__ == "__main__":
    try:
        # メインネットで実行（is_testnet=False）
        client = BinanceFuturesClient(is_testnet=False)
        
        # 注文を発注
        order_response = client.prepare_and_place_order()
        print("\nOrder Response:")
        print(json.dumps(order_response, indent=2))
        
        # 少し待機してポジション情報を確認
        time.sleep(2)
        position_info = client.get_position_info()
        print("\nPosition Info:")
        print(json.dumps(position_info, indent=2))
        
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        sys.exit(1)