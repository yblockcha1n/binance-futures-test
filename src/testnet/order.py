import configparser
from typing import Dict, Optional, Tuple
from binance.um_futures import UMFutures
from binance.error import ClientError
import logging
from pathlib import Path
import os
import math

class SymbolInfo:
    def __init__(self, symbol_data: Dict):
        """
        シンボル情報を管理するクラス
        Args:
            symbol_data (Dict): exchange_infoから取得したシンボル情報
        """
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
        """数量をstep_sizeに合わせて丸める"""
        step_size = self.step_size
        precision = int(round(-math.log(step_size, 10), 0))
        return round(round(quantity / step_size) * step_size, precision)

    def round_tick_size(self, price: float) -> float:
        """価格をtick_sizeに合わせて丸める"""
        tick_size = self.tick_size
        precision = int(round(-math.log(tick_size, 10), 0))
        return round(round(price / tick_size) * tick_size, precision)

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
    def __init__(self, is_testnet: bool = True):
        """
        Binance Futures クライアントの初期化
        Args:
            is_testnet (bool): テストネットを使用するかどうか
        """
        self.config = self._load_configs()
        self.trading_params = self._load_trading_parameters()
        self.client = self._initialize_client(is_testnet)
        self._setup_logging()
        self.symbol_info = self._get_symbol_info(self.trading_params.symbol)
        self.logger.info(f"Symbol info loaded: {vars(self.symbol_info)}")

    def _load_configs(self) -> configparser.ConfigParser:
        """API設定ファイルの読み込み"""
        config = configparser.ConfigParser()
        config_path = Path("settings/config.ini")
        if not config_path.exists():
            raise FileNotFoundError("Config file not found at settings/config.ini")
        config.read(config_path)
        return config

    def _load_trading_parameters(self) -> TradingParameters:
        """トレードパラメータの読み込みと検証"""
        param_config = configparser.ConfigParser()
        param_path = Path("settings/parameter.ini")
        if not param_path.exists():
            raise FileNotFoundError("Parameter file not found at settings/parameter.ini")
        param_config.read(param_path)
        
        trading_section = param_config['TRADING']
        return TradingParameters(
            symbol=trading_section.get('SYMBOL'),
            leverage=trading_section.getint('LEVERAGE'),
            side=trading_section.get('SIDE'),
            order_type=trading_section.get('ORDER_TYPE'),
            usdt_amount=trading_section.getfloat('USDT_AMOUNT'),
            reduce_only=trading_section.getboolean('REDUCE_ONLY', False)
        )

    def _initialize_client(self, is_testnet: bool) -> UMFutures:
        """Binance Futuresクライアントの初期化"""
        api_key = self.config['BINANCE']['API_KEY']
        api_secret = self.config['BINANCE']['API_SECRET']
        
        base_url = "https://testnet.binancefuture.com" if is_testnet else None
        return UMFutures(
            key=api_key,
            secret=api_secret,
            base_url=base_url
        )

    def _setup_logging(self):
        """ログ設定"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{log_dir}/trading.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _get_symbol_info(self, symbol: str) -> SymbolInfo:
        """シンボル情報の取得"""
        try:
            exchange_info = self.client.exchange_info()
            symbol_info = next(
                (item for item in exchange_info['symbols'] if item['symbol'] == symbol),
                None
            )
            if not symbol_info:
                raise ValueError(f"Symbol {symbol} not found in exchange info")
            return SymbolInfo(symbol_info)
        except Exception as e:
            self.logger.error(f"Failed to get symbol info: {str(e)}")
            raise

    def _get_current_price(self, symbol: str) -> float:
        """現在の価格を取得"""
        try:
            ticker = self.client.mark_price(symbol=symbol)
            return float(ticker['markPrice'])
        except ClientError as e:
            self.logger.error(f"Failed to get current price: {e.error_message}")
            raise

    def _calculate_quantity(self, usdt_amount: float, current_price: float) -> float:
        """USDTベースの数量から実際の取引数量を計算"""
        try:
            # 最小注文金額のチェックと調整
            if usdt_amount < self.symbol_info.min_notional:
                self.logger.warning(
                    f"USDT amount {usdt_amount} is less than minimum notional {self.symbol_info.min_notional}. "
                    f"Adjusting to minimum notional."
                )
                usdt_amount = self.symbol_info.min_notional

            raw_quantity = usdt_amount / current_price
            
            # 最小数量チェック
            if raw_quantity < self.symbol_info.min_qty:
                # 最小数量を使用し、それに見合うようにUSDT金額を増やす
                raw_quantity = self.symbol_info.min_qty
                adjusted_usdt = raw_quantity * current_price
                if adjusted_usdt < self.symbol_info.min_notional:
                    raw_quantity = self.symbol_info.min_notional / current_price
                    self.logger.warning(
                        f"Adjusted quantity to meet minimum notional requirement. "
                        f"New quantity: {raw_quantity}"
                    )
            
            # 最大数量チェック
            if raw_quantity > self.symbol_info.max_qty:
                self.logger.warning(
                    f"Calculated quantity {raw_quantity} is more than maximum allowed {self.symbol_info.max_qty}. "
                    f"Adjusting to maximum quantity."
                )
                raw_quantity = self.symbol_info.max_qty
            
            # step sizeに合わせて丸める
            final_quantity = self.symbol_info.round_step_size(raw_quantity)
            
            # 最終チェック: 注文の名目価値
            notional_value = final_quantity * current_price
            if notional_value < self.symbol_info.min_notional:
                self.logger.warning(
                    f"Final order notional value ({notional_value} USDT) is less than minimum required "
                    f"({self.symbol_info.min_notional} USDT). Adjusting quantity."
                )
                final_quantity = math.ceil(self.symbol_info.min_notional / current_price * 1000) / 1000

            self.logger.info(
                f"Quantity calculation: USDT Amount: {usdt_amount}, "
                f"Price: {current_price}, "
                f"Final Quantity: {final_quantity}, "
                f"Notional Value: {final_quantity * current_price}"
            )
            
            return final_quantity

        except Exception as e:
            self.logger.error(f"Error in calculate quantity: {str(e)}")
            raise

    def _set_leverage(self, symbol: str, leverage: int):
        """レバレッジを設定"""
        try:
            self.client.change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            self.logger.info(f"Leverage set to {leverage}x for {symbol}")
        except ClientError as e:
            self.logger.error(f"Failed to set leverage: {e.error_message}")
            raise

    def prepare_and_place_order(self) -> Dict:
        """パラメータに基づいて注文を準備して発注"""
        try:
            # レバレッジを設定
            self._set_leverage(self.trading_params.symbol, self.trading_params.leverage)
            
            # 現在価格を取得
            current_price = self._get_current_price(self.trading_params.symbol)
            
            # 数量を計算
            quantity = self._calculate_quantity(
                self.trading_params.usdt_amount, 
                current_price
            )
            
            # 指値価格を設定（LIMIT注文の場合）
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
            return self.place_order(**order_params)
            
        except Exception as e:
            self.logger.error(f"Error in prepare_and_place_order: {str(e)}")
            raise

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        reduce_only: bool = False,
        price: Optional[float] = None,
        time_in_force: str = "GTC"
    ) -> Dict:
        """注文を発注する"""
        try:
            params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
                "reduceOnly": reduce_only
            }

            if order_type == "LIMIT":
                if price is None:
                    raise ValueError("Price is required for LIMIT orders")
                params.update({
                    "price": price,
                    "timeInForce": time_in_force
                })

            response = self.client.new_order(**params)
            self.logger.info(f"Order placed successfully: {response}")
            return response

        except ClientError as e:
            self.logger.error(f"Failed to place order: {e.error_message}")
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

    def get_exchange_info(self) -> Dict:
        """取引所の情報を取得"""
        try:
            return self.client.exchange_info()
        except ClientError as e:
            self.logger.error(f"Failed to get exchange info: {e.error_message}")
            raise

if __name__ == "__main__":
    try:
        client = BinanceFuturesClient(is_testnet=True)
        
        order_response = client.prepare_and_place_order()
        print("Order Response:", order_response)
        
        position_info = client.get_position_info()
        print("Position Info:", position_info)
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")