import asyncio
import logging
import time
from hashlib import sha256
from ecdsa import SigningKey
import websockets

import xena.proto.common_pb2 as common_pb2
import xena.proto.market_pb2 as market_pb2
import xena.proto.auth_pb2 as auth_pb2
import xena.proto.order_pb2 as order_pb2
import xena.proto.positions_pb2 as positions_pb2
import xena.proto.balance_pb2 as balance_pb2
import xena.proto.constants as constants
import xena.serialization as serialization
import xena.helpers as helpers
import xena.exceptions as exceptions


class WebsocketClient:

    def __init__(self, loop, coro, url):
        self._loop = loop
        self._log = logging.getLogger(__name__)
        self._coro = coro
        self._socket = None
        self._url = url
        self._login_msg_fnc = None
        self._on_connection_close = []
        self._closed = False
        self._future_heartbeat = None
        self._future_read = None

        async def on_connection_close(client, exception):
            self._log.debug('connection closed: %s', exception)

        self._on_connection_close.append(on_connection_close)

    async def _heartbeat(self, interval):
        heartbeat = common_pb2.Heartbeat()
        heartbeat.MsgType = constants.MsgType_Heartbeat
        data = serialization.to_fix_json(heartbeat)

        try:
            while not self._closed:
                await self._socket.send(data)
                await asyncio.sleep(interval)
        except Exception as e:
            await self._close(e)

    async def _read(self):
        try:
            while True:
                evt = await self._socket.recv()
                await self._coro(evt)
        except Exception as e:
            await self._close(e)

    async def _connect(self):
        if self._socket is None:
            self._closed = False
            self._socket = await websockets.connect(self._url)

            if self._login_msg_fnc is not None:
                await self._socket.send(self._login_msg_fnc())

            evt = await self._socket.recv()
            logon = serialization.from_json(evt)
            if logon.MsgType != constants.MsgType_LogonMsgType:
                raise exceptions.LoginException('Got "{}" message instead of login'.format(logon.MsgType))

            if logon.RejectText != "":
                raise exceptions.LoginException(logon.RejectText)

            self._future_heartbeat = asyncio.ensure_future(self._heartbeat(logon.HeartBtInt), loop=self._loop)
            self._future_read = asyncio.ensure_future(self._read(), loop=self._loop)
            return logon

    async def _close(self, e):
        try:
            if self._socket is not None:
                self._socket = None

                # calling on_connection_close only if it's was not closed by hands
                if not self._closed:
                    for fnc in self._on_connection_close:
                        await fnc(self, e)
        except Exception as ex:
            self._log.exception("on self._close")

    def on_connection_close(self, callback):
        """Add callback thath will be called on connection closed

        :param callback: callback coroutine
        :type callback: async coroutine
        """

        self._on_connection_close.append(callback)

    async def send(self, msg):
        """Send message into socket

        :param msg: message
        :type msg: bytes
        """
        if self._closed:
            return

        if self._socket is None:
            await self._connect()
        await self._socket.send(msg)

    async def close(self):
        if self._closed:
            return

        self._closed = True

        if self._future_heartbeat is not None:
            self._future_heartbeat.cancel()
        
        if self._future_read is not None:
            self._future_read.cancel()

        if self._socket is not None:
            await self._socket.close()


class XenaMDWebsocketClient(WebsocketClient):
    """Websocket client for xena market data api
    For more information checkout market data api https://support.xena.exchange/support/solutions/articles/44000222067-market-data-api
    """

    URL = 'wss://api.xena.exchange/ws/market-data'

    def __init__(self, loop):
        super().__init__(loop, self._handle, self.URL)

        self._log = logging.getLogger(__name__)
        self._streams = {}
        self._md_response_types = [constants.MsgType_MarketDataSnapshotFullRefresh, constants.MsgType_MarketDataIncrementalRefresh, constants.MsgType_MarketDataRequestReject]

        async def on_connection_close(client, exception):
            self._streams = {}
        self._on_connection_close.append(on_connection_close)

    async def _handle(self, msg):
        try:
            msg = serialization.from_json(msg)
            if msg.MsgType in self._md_response_types:
                await self._streams[msg.MDStreamId](self, msg)
        except Exception as e:
            self._log.exception('md handler')

    async def connect(self):
        """Connect to server, make login request, on failure the method will raise xena.exceptions.LoginException or any other network exceptions

        :returns: xena.proto.auth_pb2.Logon
        """

        return await self._connect()

    async def subscribe(self, stream_id, callback, throttle_interval=500, throttle_unit=constants.ThrottleTimeUnit_Milliseconds, aggregation=0, market_depth=0):
        """Subsrcibe to :stream_id. If client already subsctibe to :stream_id, method will raise KeyError

        :param stream_id: required
        :type stream_id: str
        :param callback: callback coroutine to handle messages
        :type callback: async coroutine
        :param throttle_interval: throttling interval in throttle_unit: units, suppported intervals 0ms, 250ms, 1s
        :type throttle_interval: int
        :param throttle_unit: throttling units of throttle_interval:
        :type throttle_unit: string, sett constants.ThrottleTimeUnit_*
        :param aggregation: dom prices are rounded to TickSize*aggregation and than aggregated, available values are 0,5,10,25,50,100,250, used only for dom subscrition
        :type aggreagation: int
        :param market_depth: number of dom levels to return, available values are 0,10,20, used only for dom subscrition
        :type market_depth: int
        """

        if stream_id in self._streams:
            raise KeyError("Subscription for stream {} already exists".format(stream_id))

        request = market_pb2.MarketDataRequest()
        request.MsgType = constants.MsgType_MarketDataRequest
        request.SubscriptionRequestType = constants.SubscriptionRequestType_SnapshotAndUpdates
        request.MDStreamId = stream_id
        request.ThrottleType = constants.ThrottleType_OutstandingRequests
        request.ThrottleTimeInterval = throttle_interval
        request.ThrottleTimeUnit = throttle_unit
        request.AggregatedBook = aggregation
        request.MarketDepth = market_depth

        data = serialization.to_fix_json(request)
        await self.send(data)

        self._streams[stream_id] = callback

    async def unsubscribe(self, stream_id):
        """Unsubsctibe from :stream_id stream. If subsctibtion doesn't exists, the method will raise KeyError

        :param stream_id: required
        :type stream_id: str
        """

        if stream_id not in self._streams:
            raise KeyError("Subscription for stream {} doesn't exists".format(stream_id))

        request = market_pb2.MarketDataRequest()
        request.MsgType = constants.MsgType_MarketDataRequest
        request.SubscriptionRequestType = constants.SubscriptionRequestType_DisablePreviousSnapshot
        request.MDStreamId = stream_id

        data = serialization.to_fix_json(request)
        await self.send(data)
        del self._streams[stream_id]

    async def candles(self, symbol, callback, timeframe="1m", throttle_interval=250, throttle_unit=constants.ThrottleTimeUnit_Milliseconds):
        """Subsrcibe to candles stream for symbol :symbol.
        The first messge to callback will be xena.proto.market_pb2.MarketDataRefresh message with MsgType_MarketDataSnapshotFullRefresh,
        then callback will continue to receive xena.proto.market_pb2.MarketDataRefresh with with MsgType_MarketDataIncrementalRefresh.
        If stream for :sybmol or :timefram does not exist the message will be xena.proto.market_pb2.MarketDataReject.

        :param symbol: required
        :type symbol: str
        :param callback: callback coroutine to handle messages
        :type callback: async coroutine
        :param timeframe: timeframe of bars
        :type timeframe: str '1m', '15m' '30m', '1h', '3h', '6h', '24h'
        :param throttle_interval: throttling interval in throttle_unit: units, suppported intervals 0ms, 250ms, 1s
        :type throttle_interval: int
        :param throttle_unit: throttling units of throttle_interval:
        :type throttle_unit: string, sett constants.ThrottleTimeUnit_*

        :returns: stream id to use in usubscribe
        """

        if symbol == "":
            raise ValueError("Symbol can not be empty")

        stream_id = "candles:{}:{}".format(symbol, timeframe)
        await self.subscribe(stream_id, callback, throttle_interval, throttle_unit)
        return stream_id

    async def dom(self, symbol, callback, throttle_interval=500, throttle_unit=constants.ThrottleTimeUnit_Milliseconds, aggregation=0, market_depth=0):
        """
        Subsrcibe to dom stream for symbol :sybmol.
        The first messge to callback will be xena.proto.market_pb2.MarketDataRefresh message with MsgType_MarketDataSnapshotFullRefresh,
        then callback will continue to receive xena.proto.market_pb2.MarketDataRefresh with with MsgType_MarketDataIncrementalRefresh.

        If stream for :sybmol or :timefram does not exist the message will be xena.proto.market_pb2.MarketDataReject.

        :param symbol: required
        :type symbol: str
        :param callback: callback coroutine to handle messages
        :type callback: async coroutine
        :param throttle_interval: throttling interval in throttle_unit: units, suppported intervals 0ms, 500ms, 1s
        :type throttle_interval: int
        :param throttle_unit: throttling units of throttle_interval:
        :type throttle_unit: string, sett constants.ThrottleTimeUnit_*
        :param aggregation: dom prices are rounded to TickSize*aggregation and than aggregated, available values are 0,5,10,25,50,100,250
        :type aggreagation: int
        :param market_depth: number of dom levels to return, available values are 0,10,20
        :type market_depth: int

        :returns: stream id to use in usubscribe
        """

        if symbol == "":
            raise ValueError("Symbol can not be empty")

        stream_id = "DOM:{}:aggregated".format(symbol)
        await self.subscribe(stream_id, callback, throttle_interval, throttle_unit, aggregation, market_depth)
        return stream_id

    async def trades(self, symbol, callback, throttle_interval=500, throttle_unit=constants.ThrottleTimeUnit_Milliseconds):
        """Subsrcibe to trades stream for sybmol :sybmol.
        The first messge to callback will be xena.proto.market_pb2.MarketDataRefresh message with MsgType_MarketDataSnapshotFullRefresh,
        then callback will continue to receive xena.proto.market_pb2.MarketDataRefresh with with MsgType_MarketDataIncrementalRefresh.
        If stream for :sybmol does not exist the message will be xena.proto.market_pb2.MarketDataReject.

        :param symbol: required
        :type symbol: str
        :param callback: callback coroutine to handle messages
        :type callback: async coroutine
        :param throttle_interval: throttling interval in throttle_unit: units, suppported intervals 0ms, 500ms, 1s
        :type throttle_interval: int
        :param throttle_unit: throttling units of throttle_interval:
        :type throttle_unit: string, sett constants.ThrottleTimeUnit_*

        :returns: stream id to use in usubscribe
        """
 
        if symbol == "":
            raise ValueError("Symbol can not be empty")

        stream_id = "trades:{}".format(symbol)
        await self.subscribe(stream_id, callback, throttle_interval, throttle_unit)
        return stream_id

    async def market_watch(self, callback):
        """Subsrcibe to market watch stream.
        The callback will allways receive xena.proto.market_pb2.MarketDataRefresh message with MsgType_MarketDataSnapshotFullRefresh.

        :param symbol: required
        :type symbol: str
        :param callback: callback coroutine to handle messages
        :type callback: async coroutine
        :param throttle_interval: throttling interval in throttle_unit: units
        :type throttle_interval: int
        :param throttle_unit: throttling units of throttle_interval:
        :type throttle_unit: string, sett constants.ThrottleTimeUnit_*

        :returns: stream id to use in usubscribe
        """

        stream_id = "market-watch"
        await self.subscribe(stream_id, callback)
        return stream_id


class XenaTradingWebsocketClient(WebsocketClient):
    """Websocket client for xena trading api
    More information checkout out trading api documentation https://support.xena.exchange/support/solutions/articles/44000222082-ws-trading-api
    """

    URL = 'wss://api.xena.exchange/ws/trading'

    def __init__(self, api_key, api_secret, loop):
        super().__init__(loop, self._handle, self.URL)

        self._api_key = api_key
        self._api_secret = api_secret
        self._log = logging.getLogger(__name__)
        self._listeners = {}

    def _login_msg(self, accounts=None):
        def inner():
            timestamp = int(time.time() * 1000000000)
            auth_payload = 'AUTH' + str(timestamp)
            signing_key = SigningKey.from_der(bytes.fromhex(self._api_secret))

            msg = auth_pb2.Logon()
            msg.MsgType = constants.MsgType_LogonMsgType
            msg.SendingTime = timestamp
            msg.RawData = auth_payload
            msg.Username = self._api_key
            msg.Password = signing_key.sign(auth_payload.encode('utf-8'), hashfunc=sha256).hex()
            if accounts is not None:
                msg.Account.extend(accounts)

            return serialization.to_fix_json(msg)
        return inner

    async def _handle(self, msg):
        try:
            msg = serialization.from_json(msg)
            if msg.MsgType in self._listeners:
                await self._listeners[msg.MsgType](self, msg)

            # send to general listeners
            if "all" in self._listeners:
                await self._listeners["all"](self, msg)
        except Exception as e:
            self._log.exception('trade handler')

    def listen(self, callback):
        """ Add listener to all message types

        :param callback: callback coroutine
        :type callback: async coroutine
        """

        if "all" in self._listeners:
            raise ValueError("General listener for all messages altready exists")

        self._listeners["all"] = callback

    def listen_type(self, msg_types, callback):
        """ Add listener for msg_type

        :param msg_type: MsgType of message to listen or list of MsgType
        :type msg_type: str, contants.MsgType_*
        :param callback: callback coroutine
        :type callback: async coroutine
        """

        if isinstance(msg_types, list):
            for msg_type in msg_types:
                self.listen_type(msg_type, callback)
        else:
            if msg_types in self._listeners:
                raise KeyError("Listener for \"{}\" message type altready exists".format(msg_types))

            self._listeners[msg_types] = callback

    def remove_listener(self, msg_type):
        """Remove listener for :msg_type previously added  by listen_type()

        :param msg_type: MsgType of message to listen or list of MsgType
        :type msg_type: str, contants.MsgType_*
        """

        if msg_type in self._listeners:
            del self._listeners[msg_type]

    async def connect(self, accounts=None):
        """Connect to server, make login request, on failure the method will raise xena.exceptions.LoginException or any other network exceptions

        :returns: xena.proto.auth_pb2.Logon
        """

        self._login_msg_fnc = self._login_msg(accounts)
        return await self._connect()

    async def send_cmd(self, cmd):
        """ Serialize command and send bytes into websocet"""

        if not hasattr(cmd, "DESCRIPTOR"):
            raise ValueError("Command has to be protobuf object")

        await self.send(serialization.to_fix_json(cmd))

    async def account_status_report(self, account, request_id=""):
        """Request balances and margin requirements for :account
        To receive respose, client has to listen constants.MsgType_AccountStatusReport and 
        constants.MsgType_MarginRequirementReport for getting margin requirements report

        :param account: required
        :type account: int
        """

        cmd = balance_pb2.AccountStatusReportRequest()
        cmd.MsgType = constants.MsgType_AccountStatusReportRequest
        cmd.AccountStatusRequestId = request_id
        cmd.Account = account
        await self.send_cmd(cmd)

    async def positions(self, account, request_id=""):
        """Request all position for :account
        To receive respose, client has to listen constants.MsgType_MassPositionReport

        :param account: required
        :type account: int
        """

        cmd = positions_pb2.PositionsRequest()
        cmd.MsgType = constants.MsgType_RequestForPositions
        cmd.PosReqId = request_id
        cmd.Account = account
        await self.send_cmd(cmd)
    
    async def order(self, account, request_id="", client_order_id="", order_id=""):
        """Request order for :account by ClOrdId or OrderId
        To receive respose, client has to listen constants.MsgType_ExecutionReportMsgType

        :param account: required
        :type account: int
        """

        if client_order_id == "" and order_id == "":
            raise ValueError("client_order_id or order_id is required")

        cmd = order_pb2.OrderStatusRequest()
        cmd.MsgType = constants.MsgType_OrderStatusRequest
        cmd.OrdStatusReqId = request_id
        cmd.Account = account
        cmd.ClOrdId = client_order_id
        cmd.OrderId = order_id
        await self.send_cmd(cmd)
    
    async def orders(self, account, request_id=""):
        """ Depricated """
        await self.active_orders(account, request_id)

    async def active_orders(self, account, request_id="", symbol=""):
        """Request all active orders for :account
        To receive respose, client has to listen constants.MsgType_OrderMassStatusResponse

        :param account: required
        :type account: int
        :param symbol: filter trades by symbol
        :type sybmol: string
        """

        cmd = order_pb2.OrderMassStatusRequest()
        cmd.MsgType = constants.MsgType_OrderMassStatusRequest
        cmd.MassStatusReqType = constants.MassStatusReqType_ActiveOrders
        cmd.MassStatusReqId = request_id
        cmd.Account = account
        cmd.Symbol = symbol
        await self.send_cmd(cmd)
    
    async def last_order_statuses(self, account, request_id="", symbol="", ts_from=0, ts_to=0):
        """Request last statuses from order history for :account
        To receive respose, client has to listen constants.MsgType_OrderMassStatusResponse

        :param account: required
        :type account: int
        :param symbol: filter trades by symbol
        :type sybmol: string
        :param ts_from: show execution reports which TransactTime greater than ts_from
        :type ts_from: int unixtimestamp in nanoseconds
        :param ts_to: show execution reports which TransactTime less than ts_to, if present - ts_from is required
        :type ts_to: int unixtimestamp in nanoseconds
        """

        cmd = order_pb2.OrderMassStatusRequest()
        cmd.MsgType = constants.MsgType_OrderMassStatusRequest
        cmd.MassStatusReqType = constants.MassStatusReqType_DoneOrdersLastStatus
        cmd.MassStatusReqId = request_id
        cmd.Account = account
        cmd.Symbol = symbol
        
        if ts_from != 0:
            cmd.TransactTime.append(ts_from)

        if ts_to != 0:
            if ts_from == 0:
                raise ValueError("ts_from is required")
            cmd.TransactTime.append(ts_to)

        await self.send_cmd(cmd)
    
    async def order_history(self, account, request_id="", symbol="", ts_from=0, ts_to=0):
        """Request order history for :account
        To receive respose, client has to listen constants.MsgType_OrderMassStatusResponse

        :param account: required
        :type account: int
        :param symbol: filter trades by symbol
        :type sybmol: string
        :param ts_from: show execution reports which TransactTime greater than ts_from
        :type ts_from: int unixtimestamp in nanoseconds
        :param ts_to: show execution reports which TransactTime less than ts_to, if present - ts_from is required
        :type ts_to: int unixtimestamp in nanoseconds
        """

        cmd = order_pb2.OrderMassStatusRequest()
        cmd.MsgType = constants.MsgType_OrderMassStatusRequest
        cmd.MassStatusReqType = constants.MassStatusReqType_History
        cmd.MassStatusReqId = request_id
        cmd.Account = account
        cmd.Symbol = symbol
        
        if ts_from != 0:
            cmd.TransactTime.append(ts_from)

        if ts_to != 0:
            if ts_from == 0:
                raise ValueError("ts_from is required")
            cmd.TransactTime.append(ts_to)

        await self.send_cmd(cmd)

    async def trade_history(self, account, request_id="", symbol="", ts_from=0, ts_to=0):
        """Request all orders for :account
        To receive respose, client has to listen constants.MsgType_MassPositionReport.
        Response will contain last 1000 trades.

        :param account: required
        :type account: int
        :param symbol: filter trades by symbol
        :type sybmol: string
        :param ts_from: show trades which TransactTime greater than ts_from
        :type ts_from: int unixtimestamp in nanoseconds
        :param ts_to: show trades which TransactTime less than ts_to, if present - ts_from is required
        :type ts_to: int unixtimestamp in nanoseconds
        """

        cmd = order_pb2.TradeCaptureReportRequest()
        cmd.MsgType = constants.MsgType_TradeCaptureReportRequest
        cmd.TradeRequestID = request_id
        cmd.Account = account
        cmd.Symbol = symbol

        if ts_from != 0:
            cmd.TransactTime.append(ts_from)

        if ts_to != 0:
            if ts_from == 0:
                raise ValueError("ts_from is required")
            cmd.TransactTime.append(ts_to)

        await self.send_cmd(cmd)

    async def market_order(self, account, client_order_id, symbol, side, qty, **kwargs):
        """Create market order and send request"""

        await self.send_cmd(helpers.market_order(account, client_order_id, symbol, side, qty, **kwargs))

    async def limit_order(self, account, client_order_id, symbol, side, price, qty, **kwargs):
        """Create limit order and send request"""

        await self.send_cmd(helpers.limit_order(account, client_order_id, symbol, side, price, qty, **kwargs))

    async def stop_order(self, account, client_order_id, symbol, side, stop_price, qty, **kwargs):
        """Create stop order and send request"""

        await self.send_cmd(helpers.stop_order(account, client_order_id, symbol, side, stop_price, qty, **kwargs))

    async def mit_order(self, account, client_order_id, symbol, side, stop_price, qty, **kwargs):
        """Create "market if touched" order and send request"""

        await self.send_cmd(helpers.mit_order(account, client_order_id, symbol, side, stop_price, qty, **kwargs))

    async def cancel(self, cmd):
        """Wrapper for send_cmd with convenient methond name for sending cancel commnads"""

        if not isinstance(cmd, order_pb2.OrderCancelRequest):
            raise ValueError("Command has to be OrderCancelRequest")

        await self.send_cmd(cmd)

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
        await self.cancel(cmd)

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
        await self.cancel(cmd)

    async def mass_cancel(self, account, cancel_id, symbol="", side="", position_effect=constants.PositionEffect_Default):
        """ Create OrderMassCancelRequest and send request

        To receive respose, client has to listen constants.MsgType_MsgType_OrderMassCancelReport.
        Also each canceled order will send constants.ExecutionReport with ExecType == constants.ExecType_CanceledExec
        """

        cmd = order_pb2.OrderMassCancelRequest
        cmd.MsgType = constants.MsgType_OrderMassCancelRequest
        cmd.MassCancelRequestType = constants.MassCancelRequestType_CancelOrdersForASecurity if symbol != "" else constants.MassCancelRequestType_CancelAllOrders
        cmd.ClOrdId = cancel_id
        cmd.Account = account
        cmd.Symbol = symbol
        cmd.Side = side
        cmd.PositionEffect = position_effect
        cmd.TransactTime = int(time.time() * 1000000000)
        await self.send_cmd(cmd)


    async def replace(self, cmd):
        """Wrapper for send_cmd with convenient methond name for sending replace commnads"""

        if not isinstance(cmd, order_pb2.OrderCancelReplaceRequest):
            raise ValueError("Command has to be OrderCancelRequest")

        await self.send_cmd(cmd)

    async def collapse_positions(self, account, symbol, request_id):
        """Send request to collapse positions
        To receive respose, client has to listen constants.MsgType_PositionMaintenanceReport
        """

        cmd = positions_pb2.PositionMaintenanceRequest()
        cmd.MsgType = constants.MsgType_PositionMaintenanceRequest
        cmd.Symbol = symbol
        cmd.Account = account
        cmd.PosReqId = request_id
        cmd.PosTransType = constants.PosTransType_Collapse
        cmd.PosMaintAction = constants.PosMaintAction_Replace
        await self.send_cmd(cmd)

    async def heartbeat(self, group_id, intervalInSec):
        """Send application heartbeat"""

        cmd = order_pb2.ApplicationHeartbeat()
        cmd.MsgType = constants.MsgType_ApplicationHeartbeat
        cmd.GrpID = group_id
        cmd.HeartBtInt = intervalInSec
        await self.send_cmd(cmd)
