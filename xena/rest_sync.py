import logging
import time
from datetime import datetime
from hashlib import sha256
import requests
from ecdsa import SigningKey

import xena.proto.common_pb2 as common_pb2
import xena.proto.market_pb2 as market_pb2
import xena.proto.order_pb2 as order_pb2
import xena.proto.positions_pb2 as positions_pb2
import xena.proto.constants as constants
import xena.serialization as serialization
import xena.helpers as helpers
import xena.exceptions as exceptions


class XenaSyncClient:

    def __init__(self, url):
        self._log = logging.getLogger(__name__)
        self._url = url

    def _get_headers(self):
        return {
            'Accept': 'application/json',
            'User-Agent': 'xena/python'
        }

    def _request(self, method, path, **kwargs):
        uri = self.URL + path
        msg = kwargs.pop('msg', None)
        kwargs['headers'] = self._get_headers()
        with requests.Session() as session:
            with getattr(session, method)(uri, **kwargs) as response:
                return self._handle_response(response, msg)

    def _handle_response(self, response, msg=None):
        if not str(response.status_code).startswith('2'):
            raise exceptions.RequestException(response, response.status_code, response.text)

        return serialization.from_json(response.text, to=msg)

    def _get(self, path, **kwargs):
        return self._request('get', path, **kwargs)

    def _post(self, path, **kwargs):
        return self._request('post', path, **kwargs)


class XenaMDSyncClient(XenaSyncClient):
    """All docs look up at XenaMDClient"""

    URL = 'https://api.xena.exchange'

    def __init__(self):
        super().__init__(self.URL)
        self._log = logging.getLogger(__name__)

    def candles(self, symbol, timeframe='1m', ts_from="", ts_to=""):
        return self._get('/market-data/candles/'+symbol+'/'+timeframe, msg=market_pb2.MarketDataRefresh, params={
            "from": ts_from,
            "to": ts_to,
        })

    def dom(self, symbol, throttling=500, aggregation=0, market_depth=0):
        return self._get('/market-data/dom/'+symbol, msg=market_pb2.MarketDataRefresh, params={
            "throttling": throttling,
            "aggr": aggregation,
            "depth": market_depth,
        })

    def trades(self, symbol, ts_from="", ts_to="", page=1, limit=0):
        return self._get('/market-data/trades/'+symbol, msg=market_pb2.MarketDataRefresh, params={
            "from": ts_from,
            "to": ts_to,
            "page": page,
            "limit": limit
        })

    def server_time(self):
        resp = self._get('/market-data/server-time', msg=common_pb2.Heartbeat)
        return datetime.fromtimestamp(resp.TransactTime/1000000000)

    def instruments(self):
        return self._get('/public/instruments', msg=common_pb2.Instrument)


class XenaTradingSyncClient(XenaSyncClient):
    """All docs look up at XenaTradingClient"""

    URL = 'https://api.xena.exchange/trading'

    def __init__(self, api_key, api_secret):
        super().__init__(self.URL)

        self._api_key = api_key
        self._api_secret = api_secret
        self._log = logging.getLogger(__name__)

    def _get_headers(self):
        timestamp = int(time.time() * 1000000000)
        auth_payload = 'AUTH' + str(timestamp)
        signing_key = SigningKey.from_der(bytes.fromhex(self._api_secret))

        headers = super()._get_headers()
        headers.update({
            'X-Auth-Api-Key': self._api_key,
            'X-Auth-Api-Payload': auth_payload,
            'X-Auth-Api-Signature': signing_key.sign(auth_payload.encode('utf-8'), hashfunc=sha256).hex(),
            'X-Auth-Api-Nonce': str(timestamp),
        })

        return headers

    def new_order(self, cmd):
        return self._post('/order/new', data=serialization.to_json(cmd))

    def market_order(self, account, client_order_id, symbol, side, qty, **kwargs):
        return self.new_order(helpers.market_order(account, client_order_id, symbol, side, qty, **kwargs))

    def limit_order(self, account, client_order_id, symbol, side, price, qty, **kwargs):
        return self.new_order(helpers.limit_order(account, client_order_id, symbol, side, price, qty, **kwargs))

    def stop_order(self, account, client_order_id, symbol, side, stop_price, qty, **kwargs):
        return self.new_order(helpers.stop_order(account, client_order_id, symbol, side, stop_price, qty, **kwargs))

    def mit_order(self, account, client_order_id, symbol, side, stop_price, qty, **kwargs):
        return self.new_order(helpers.mit_order(account, client_order_id, symbol, side, stop_price, qty, **kwargs))

    def cancel(self, cmd):
        if not isinstance(cmd, order_pb2.OrderCancelRequest):
            raise ValueError("Command has to be OrderCancelRequest")

        return self._post('/order/cancel', data=serialization.to_json(cmd))

    def cancel_by_client_id(self, account, cancel_id, client_order_id, symbol, side):
        cmd = order_pb2.OrderCancelRequest()
        cmd.MsgType = constants.MsgType_OrderCancelRequestMsgType
        cmd.ClOrdId = cancel_id
        cmd.OrigClOrdId = client_order_id
        cmd.Symbol = symbol
        cmd.Side = side
        cmd.TransactTime = int(time.time() * 1000000000)
        cmd.Account = account
        return self.cancel(cmd)

    def cancel_by_order_id(self, account, cancel_id, order_id, symbol, side):
        cmd = order_pb2.OrderCancelRequest()
        cmd.MsgType = constants.MsgType_OrderCancelRequestMsgType
        cmd.ClOrdId = cancel_id
        cmd.OrderId = order_id
        cmd.Symbol = symbol
        cmd.Side = side
        cmd.TransactTime = int(time.time() * 1000000000)
        cmd.Account = account
        return self.cancel(cmd)

    def mass_cancel(self, account, cancel_id, symbol="", side="", position_effect=constants.PositionEffect_Default):
        cmd = order_pb2.OrderMassCancelRequest
        cmd.MsgType = constants.MsgType_OrderMassCancelRequest
        cmd.MassCancelRequestType = constants.MassCancelRequestType_CancelOrdersForASecurity if symbol != "" else constants.MassCancelRequestType_CancelAllOrders
        cmd.ClOrdId = cancel_id
        cmd.Account = account
        cmd.Symbol = symbol
        cmd.Side = side
        cmd.PositionEffect = position_effect
        cmd.TransactTime = int(time.time() * 1000000000)
        return self._post('/order/mass-cancel', data=serialization.to_json(cmd))

    def replace(self, cmd):
        if not isinstance(cmd, order_pb2.OrderCancelReplaceRequest):
            raise ValueError("Command has to be OrderCancelRequest")

        return self._post('/order/replace', data=serialization.to_json(cmd))

    def collapse_positions(self, account, symbol):
        request_id = str(time.time())
        cmd = positions_pb2.PositionMaintenanceRequest()
        cmd.MsgType = constants.MsgType_PositionMaintenanceRequest
        cmd.Symbol = symbol
        cmd.Account = account
        cmd.PosReqId = request_id
        cmd.PosTransType = constants.PosTransType_Collapse
        cmd.PosMaintAction = constants.PosMaintAction_Replace
        return self._post('/position/maintenance', data=serialization.to_json(cmd))

    def positions(self, account):
        return self._get('/accounts/' + str(account) + '/positions')

    def positions_for_symbol(self, account, symbol):
        result = []
        for p in self.positions(account):
            if p.Symbol == symbol:
                result.append(p)

        return result

    def aggregate_positions_volume(self, account, symbol):
        positions = self.positions_for_symbol(account, symbol)
        if not positions:
            return "0"

        result = helpers.aggregate_positions_volume(positions)
        if symbol not in result:
            return "0"

        return result[symbol]

    def positions_history(self, account, id=0, parentid=0, symbol="", open_ts_from=0, open_ts_to=0, close_ts_from=0, close_ts_to=0, page=1, limit=0):
        return self._get('/accounts/' + str(account) + '/positions-history', params={
            "id": id,
            "parentid": parentid,
            "symbol": symbol,
            "openfrom": open_ts_from,
            "opento": open_ts_to,
            "closefrom": close_ts_from,
            "closeto": close_ts_to,
            "page": page,
            "limit": limit
        })

    def order(self, account, client_order_id="", order_id=""):
        if client_order_id == "" and order_id == "":
            raise ValueError("client_order_id or order_id is required")

        return self._get('/accounts/' + str(account) + '/order', params={
            "client_order_id": client_order_id,
            "order_id": order_id,
        })

    def orders(self, account):
        """ Depricated """
        return self.active_orders(account)

    def active_orders(self, account, symbol=""):
        return self._get('/accounts/' + str(account) + '/active-orders', params={
            "symbol": symbol,
        })

    def last_order_statuses(self, account, symbol="", ts_from=0, ts_to=0, page=1, limit=0):
        return self._get('/accounts/' + str(account) + '/last-order-statuses', params={
            "symbol": symbol,
            "from": ts_from,
            "to": ts_to,
            "page": page,
            "limit": limit
        })
    
    def order_history(self, account, symbol="", client_order_id="", order_id="", ts_from=0, ts_to=0, page=1, limit=0):
        return self._get('/accounts/' + str(account) + '/order-history', params={
            "symbol": symbol,
            "client_order_id": client_order_id,
            "order_id": order_id,
            "from": ts_from,
            "to": ts_to,
            "page": page,
            "limit": limit
        })

    def trade_history(self, account, trade_id="", client_order_id="", symbol="", ts_from=0, ts_to=0, page=1, limit=0):
        return self._get('/accounts/' + str(account) + '/trade-history', params={
            "trade_id": trade_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "from": ts_from,
            "to": ts_to,
            "page": page,
            "limit": limit
        })

    def balance(self, account):
        return self._get('/accounts/' + str(account) + '/balance')

    def margin_requirements(self, account):
        return self._get('/accounts/' + str(account) + '/margin-requirements')


    def accounts(self):
        response = self._get('/accounts')
        result = []
        for item in response['accounts']:
            result.append(item['id'])

        return result

    def heartbeat(self, group_id, interval_in_sec):
        """Send application heartbeat"""

        cmd = order_pb2.ApplicationHeartbeat()
        cmd.MsgType = constants.MsgType_ApplicationHeartbeat
        cmd.GrpID = group_id
        cmd.HeartBtInt = interval_in_sec

        self._post('/order/heartbeat', data=serialization.to_json(cmd))
