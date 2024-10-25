import configparser
from binance.um_futures import UMFutures
from binance.error import ClientError
import logging
from pathlib import Path
from typing import List, Dict

class OrderManager:
    def __init__(self, is_testnet: bool = True):
        """
        注文管理クラスの初期化
        Args:
            is_testnet (bool): テストネットを使用するかどうか
        """
        self.config = self._load_configs()
        self.client = self._initialize_client(is_testnet)
        self._setup_logging()

    def _load_configs(self) -> configparser.ConfigParser:
        """API設定ファイルの読み込み"""
        config = configparser.ConfigParser()
        config_path = Path("settings/config.ini")
        if not config_path.exists():
            raise FileNotFoundError("Config file not found at settings/config.ini")
        config.read(config_path)
        return config

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
        """ロギングの設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        未約定の注文を取得
        Args:
            symbol (str, optional): 特定の取引ペアの注文のみを取得
        Returns:
            List[Dict]: 未約定注文のリスト
        """
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol

            open_orders = self.client.get_orders(**params)
            self.logger.info(f"Retrieved {len(open_orders)} open orders")
            return open_orders

        except ClientError as e:
            self.logger.error(f"Failed to get open orders: {e.error_message}")
            raise

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """
        特定の注文をキャンセル
        Args:
            symbol (str): 取引ペア
            order_id (int): キャンセルする注文のID
        Returns:
            Dict: キャンセル結果
        """
        try:
            response = self.client.cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            self.logger.info(f"Successfully cancelled order {order_id}")
            return response

        except ClientError as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e.error_message}")
            raise

    def cancel_all_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        すべての未約定注文をキャンセル
        Args:
            symbol (str, optional): 特定の取引ペアの注文のみをキャンセル
        Returns:
            List[Dict]: キャンセル結果のリスト
        """
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol

            response = self.client.cancel_all_open_orders(**params)
            self.logger.info("Successfully cancelled all open orders")
            return response

        except ClientError as e:
            self.logger.error(f"Failed to cancel all orders: {e.error_message}")
            raise

    def get_order_status(self, symbol: str, order_id: int) -> Dict:
        """
        特定の注文のステータスを取得
        Args:
            symbol (str): 取引ペア
            order_id (int): 注文ID
        Returns:
            Dict: 注文の詳細情報
        """
        try:
            order_info = self.client.query_order(
                symbol=symbol,
                orderId=order_id
            )
            self.logger.info(f"Retrieved status for order {order_id}")
            return order_info

        except ClientError as e:
            self.logger.error(f"Failed to get order status: {e.error_message}")
            raise

# 使用例
if __name__ == "__main__":
    try:
        # 注文管理クライアントの初期化（テストネット使用）
        order_manager = OrderManager(is_testnet=True)
        
        # 特定のシンボルの未約定注文を取得
        symbol = "BTCUSDT"
        open_orders = order_manager.get_open_orders(symbol)
        print(f"Open orders for {symbol}:", open_orders)
        
        # すべての未約定注文をキャンセル
        if open_orders:
            cancel_result = order_manager.cancel_all_open_orders(symbol)
            print("Cancel result:", cancel_result)
        
        # # 特定の注文をキャンセルする例
        # if open_orders:
        #     first_order = open_orders[0]
        #     cancel_result = order_manager.cancel_order(
        #         symbol=first_order['symbol'],
        #         order_id=first_order['orderId']
        #     )
        #     print("Single order cancel result:", cancel_result)
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")