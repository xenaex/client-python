import aiohttp
import logging
import time
from hashlib import sha256
from ecdsa import SigningKey

import xena.proto.common_pb2 as common_pb2
import xena.proto.market_pb2 as market_pb2
import xena.proto.auth_pb2 as auth_pb2
import xena.proto.order_pb2 as order_pb2
import xena.proto.positions_pb2 as positions_pb2
import xena.proto.balance_pb2 as balance_pb2
import xena.proto.common_pb2 as common_pb2
import xena.proto.constants as constants
import xena.serialization as serialization
import xena.helpers as helpers
import xena.exceptions as exceptions


class XenaClient:

    def __init__(self, url, loop):
        self._log = logging.getLogger(__name__)
        self._loop = loop
        self._url = url

    def _get_headers(self):
        return {
            'Accept': 'application/json',
            'User-Agent': 'xena/python'
        }

    async def _request(self, method, path, **kwargs):
        uri = self.URL + path 
        msg = kwargs.pop('msg', None)
        kwargs['headers'] = self._get_headers()
        async with aiohttp.ClientSession(loop=self._loop) as session:
            async with getattr(session, method)(uri, **kwargs) as response:
                return await self._handle_response(response, msg)

    async def _handle_response(self, response, msg=None):
        if not str(response.status).startswith('2'):
            raise exceptions.RequestException(response, response.status, await response.text())

        return serialization.from_json(await response.text(), to=msg)

    async def _get(self, path, **kwargs):
        return await self._request('get', path, **kwargs)

    async def _post(self, path, **kwargs):
        return await self._request('post', path, **kwargs)


class XenaMDClient(XenaClient):

    URL = 'https://api.xena.exchange'
    #  URL = 'http://localhost/api'

    def __init__(self, loop):
        super().__init__(self.URL, loop)
        self._log = logging.getLogger(__name__)

    async def candles(self, symbol, timeframe='1m', ts_from="", ts_to=""):
        """Get candles for :symbol with :timeframe from :ts_from to :ts_to,
        if :ts_from or :ts_to not supplied it will return last 2 candles

        :param symbol: required
        :type symbol: str
        :param timeframe: timeframe of bars
        :type timeframe: str '1m', '15m' '30m', '1h', '3h', '6h', '24h'
        :param ts_from: show candles from
        :type ts_from: int unixtimestamp
        :param ts_from: show candles to
        :type ts_to: int unixtimestamp

        :returns: xena.proto.market_pb2.MarketDataRefresh
        """

        return await self._get('/market-data/candles/'+symbol+'/'+timeframe, msg=market_pb2.MarketDataRefresh(), params={
            "from": ts_from,
            "to": ts_to,
        })
    
    async def dom(self, symbol, aggr=0):
        """Get L2 snapshot for :symbol 

        :param symbol: required
        :type symbol: str
        :param aggr: aggregate leveles 
        :type timeframe: int [0,5,10,25,50,100,250]

        :returns: xena.proto.market_pb2.MarketDataRefresh
        """

        return await self._get('/market-data/dom/'+symbol, msg=market_pb2.MarketDataRefresh(), params={
            "aggr": aggr
        })
    
    async def instruments(self):
        """Get list of instruments
        
        :returns: xena.proto.common_pb2.Instrument
        """ 

        return await self._get('/public/instruments', msg=common_pb2.Instrument())



class XenaTradingClient(XenaClient):

    URL = 'https://api.xena.exchange/trading'
    #  URL = 'http://localhost/api/trading'

    def __init__(self, api_key, api_secret, loop):
        super().__init__(self.URL, loop)

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

    async def order(self, cmd):
        return await self._post('/order/new', data=serialization.to_json(cmd))

    async def market_order(self, account, client_order_id, symbol, side, qty, **kwargs):
        return await self.order(helpers.market_order(account, client_order_id, symbol, side, qty, **kwargs))

    async def limit_order(self, account, client_order_id, symbol, side, price, qty, **kwargs):
        """Create limit order and send request"""

        return await self.order(helpers.limit_order(account, client_order_id, symbol, side, price, qty, **kwargs))

    async def stop_order(self, account, client_order_id, symbol, side, stop_price, qty, **kwargs):
        """Create stop order and send request"""

        return await self.order(helpers.stop_order(account, client_order_id, symbol, side, stop_price, qty, **kwargs))

    async def mit_order(self, account, client_order_id, symbol, side, stop_price, qty, **kwargs):
        """Create "market if touched" order and send request"""

        return await self.order(helpers.mit_order(account, client_order_id, symbol, side, stop_price, qty, **kwargs))

    async def cancel(self, cmd):
        """Wrapper for send_cmd with convenient methond name for sending cancel commnads"""

        if not isinstance(cmd, order_pb2.OrderCancelRequest):
            raise ValueError("Command has to be OrderCancelRequest")

        return await self._post('/order/cancel', data=serialization.to_json(cmd))

    async def cancel_by_client_id(self, account, cancel_id, client_order_id, symbol, side):
        """Create cancel request by OrderCancelRequest.OrigClOrdId and send request"""

        cmd = order_pb2.OrderCancelRequest()
        cmd.MsgType = constants.MsgType_OrderCancelRequestMsgType
        cmd.ClOrdId = cancel_id
        cmd.OrigClOrdId = client_order_id
        cmd.Symbol = symbol
        cmd.Side = side
        cmd.TransactTime = int(time.time() * 1000000000)
        cmd.Account = account
        return await self.cancel(cmd)

    async def cancel_by_order_id(self, account, cancel_id, order_id, symbol, side):
        """Create cancel request by OrderCancelRequest.OrderId and send request"""

        cmd = order_pb2.OrderCancelRequest()
        cmd.MsgType = constants.MsgType_OrderCancelRequestMsgType
        cmd.ClOrdId = cancel_id
        cmd.OrderId = order_id
        cmd.Symbol = symbol
        cmd.Side = side
        cmd.TransactTime = int(time.time() * 1000000000)
        cmd.Account = account
        return await self.cancel(cmd)

    async def replace(self, cmd):
        """Wrapper for post with convenient methond name for sending replace commnads"""

        if not isinstance(cmd, order_pb2.OrderCancelReplaceRequest):
            raise ValueError("Command has to be OrderCancelRequest")

        return await self._post('/order/replace', data=serialization.to_json(cmd))

    async def collapse_positions(self, account, symbol):
        """Send request to collapse positions"""

        request_id = str(time.time())
        cmd = positions_pb2.PositionMaintenanceRequest()
        cmd.MsgType = constants.MsgType_PositionMaintenanceRequest
        cmd.Symbol = symbol
        cmd.Account = account
        cmd.PosReqId = request_id
        cmd.PosTransType = constants.PosTransType_Collapse
        cmd.PosMaintAction = constants.PosMaintAction_Replace
        return await self._post('/position/maintenance', data=serialization.to_json(cmd))
    
    async def positions(self, account):
        """Request list of open positions for :account
        
        :param account: required
        :type account: int
        :returns: list of xena.proto.positions_pb2.PositionReport
        """

        return await self._get('/accounts/' + str(account) + '/positions')
    
    async def positions_history(self, account, id=0, parentid=0, symbol="", open_ts_from=0, open_ts_to=0, close_ts_from=0, close_ts_to=0, page=1, limit=0):
        """Request position history for :account
        
        :param account: required
        :type account: int
        :param id: show specific position
        :type id: int
        :param parentid: filter positions by parent_id
        :type parentid: int
        :param symbol: filter positions by symbol
        :type sybmol: string
        :param open_ts_from: show positions which PositionOpenTime greater than open_ts_from
        :type open_ts_from: int unixtimestamp
        :param open_ts_from: show trades which PositionOpenTime less than open_ts_to
        :type open_ts_to: int unixtimestamp
        :param close_ts_from: show positions which SettlDate greater than close_ts_from
        :type close_ts_from: int unixtimestamp
        :param close_ts_from: show trades which SettlDate less than close_ts_to
        :type close_ts_to: int unixtimestamp
        :param page: use for pagination to move through pages
        :type page: int
        :param limit: number of position to return
        :type limit: int
        :returns: list of last xena.proto.order_pb2.ExecutionReport for each active order
        """

        return await self._get('/accounts/' + str(account) + '/positions-history', params={
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
    
    async def orders(self, account):
        """Request active orders for :account
        
        :param account: required
        :type account: int
        :returns: list of last xena.proto.order_pb2.ExecutionReport for each active order
        """

        return await self._get('/accounts/' + str(account) + '/orders')
    
    async def trade_history(self, account, trade_id="", client_order_id="", symbol="", ts_from=0, ts_to=0, page=1, limit=0):
        """Request trade history for :account
        
        :param account: required
        :type account: int
        :param trade_id: show trades for specific trade_id
        :type trade_id: string
        :param client_order_id: show trades fro specific client order_id 
        :type client_order_id: string
        :param symbol: filter trades by symbol
        :type sybmol: string
        :param ts_from: show trades which TransactTime greater than ts_from
        :type ts_from: int unixtimestamp
        :param ts_from: show trades which TransactTime less than ts_to
        :type ts_to: int unixtimestamp
        :param page: use for pagination to move through pages
        :type page: int
        :param limit: number of trades to return
        :type limit: int
        :returns: list of xena.proto.order_pb2.ExecutionReport with ExecType == ExecType_Trade
        """

        return await self._get('/accounts/' + str(account) + '/trade-history', params={
            "trade_id": trade_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "from": ts_from,
            "to": ts_to,
            "page": page,
            "limit": limit
        })
    
    async def balance(self, account):
        """Request balances for :account
        
        :param account: required
        :type account: int
        :returns: xena.proto.balance_pb2.BalanceSnapshotRefresh
        """

        return await self._get('/accounts/' + str(account) + '/balance')
    
    async def margin_requirements(self, account):
        """Request margin requirements for :account
        
        :param account: required
        :type account: int
        :returns: xena.proto.margin_pb2.MarginRequirementReport
        """

        return await self._get('/accounts/' + str(account) + '/margin-requirements')
    
    
    async def accounts(self):
        """Request list of acconts id
        :returns: list of int
        """

        response = await self._get('/accounts')
        result = []
        for item in response['accounts']:
            result.append(item['id'])
        
        return result
