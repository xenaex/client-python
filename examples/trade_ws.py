import asyncio
import logging
import time
import inspect
import sys

from xena.websocket import XenaTradingWebsocketClient
import xena.proto.constants as constants
import xena.helpers as helpers

loop = None

def id(prefix):
    timestamp = int(time.time())
    return prefix + '-' + str(timestamp)


async def connect(ws):
    while True:
        try:
            await ws.connect()
            break
        except Exception as e:
            print("exception {}".format(e))
            await asyncio.sleep(1)


async def get_client():
    async def on_connection_close(ws, e):
        await connect(ws)

    #  api_key = 'NW2ARM7euG7TiCJBEAm6aI1pjP2j2PBzYv6BiQF3pYY='
    #  api_secret = '3077020101042020df97867f7caceda1d5abe9a77d2244705142719bb9f02cef57e95dde4d659ba00a06082a8648ce3d030107a14403420004ebb31e05abe41ba75371c0f23823f82b0ab963b9bb97b15cd13c42b810a5e5a1408076cb5d5ef54f927879d963695e65c10a077ed5e90779f8b99f2ba60a3ef1'
    api_key = 'EmfLDuT0hitGG7LjzIh-Xc4APzzanGd_Zq5ivAjczuI='
    api_secret = '307702010104205911735f6ce66390cc90976f90333ae416d8c07cf94be24f6f373c7f8fe74180a00a06082a8648ce3d030107a14403420004107fd20d2ab5c6299618f6bb611b2dc42d3c985fa0f77754955f9945e9e843212c79d684f7cbe56fa245029282ace128aba13fa709d0b23226087867dc436ff9'
    ws = XenaTradingWebsocketClient(api_key, api_secret, loop)
    ws.on_connection_close(on_connection_close)

    async def handle(ws, msg):
        print(msg)

    ws.listen_type([constants.MsgType_AccountStatusReport, constants.MsgType_MarginRequirementReport], handle)
    ws.listen_type(constants.MsgType_MassPositionReport, handle)
    ws.listen_type(constants.MsgType_OrderMassStatusResponse, handle)

    # repeated subscription to the same msg type is prohibited and will raise ValueError
    try:
        ws.listen_type(constants.MsgType_OrderMassStatusResponse, handle)
    except KeyError as e:
        print(e)

    await connect(ws)
    return ws


async def example_of_market_order():
    ws = await get_client()

    async def handle(ws, msg):
        print(msg)

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)
    await ws.market_order(8263200, id("market-order"), "BTC/USDT", constants.Side_Buy, "0.01")

    # or using helpers method
    cmd = helpers.market_order(8263200, id("market-order"), "BTC/USDT", constants.Side_Buy, "0.01")
    await ws.send_cmd(cmd)

    # looop
    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_limit_order():
    ws = await get_client()

    async def handle(ws, msg):
        print(msg)

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)
    await ws.limit_order(8263200, id("limit-order"), "BTC/USDT", constants.Side_Buy, "10000", "0.01")

    # or using helpers method
    cmd = helpers.limit_order(8263200, id("limit-order"), "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    await ws.send_cmd(cmd)

    # looop
    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_stop_order():
    ws = await get_client()

    async def handle(ws, msg):
        print(msg)

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)
    await ws.stop_order(8263200, id("stop-order"), "BTC/USDT", constants.Side_Sell, "10000", "0.01")

    # or using helpers method
    cmd = helpers.stop_order(8263200, id("stop-order"), "BTC/USDT", constants.Side_Sell, "10000", "0.01")
    await ws.send_cmd(cmd)

    # looop
    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_sltp_group():
    ws = await get_client()

    async def handle(ws, msg):
        print(msg)

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)

    cmd = helpers.limit_order(1012833459, id("limit-order-with-sltp"), "XBTUSD", constants.Side_Sell, "10000", "1")
    helpers.add_trailing_stop_loss(cmd, "500")
    helpers.add_take_profit(cmd, "10500")
    await ws.send_cmd(cmd)

    # or
    cmd = helpers.limit_order(1012833459, id("limit-order-with-sltp"), "XBTUSD", constants.Side_Sell, "10000", "1", trailing_offset="500", take_profit_price="10500")
    await ws.send_cmd(cmd)

    # looop
    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_stop_loss_for_existing_position():
    ws = await get_client()

    async def handle(ws, msg):
        print(msg)

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)

    # create stop order and fill PositionId and PositionEffect fields
    cmd = helpers.stop_order(1012833459, id("stop-order"), "XBTUSD", constants.Side_Sell, "10000", "1")
    helpers.for_position(cmd, 123456)
    await ws.send_cmd(cmd)

    # or
    cmd = helpers.stop_order(1012833459, id("stop-order"), "XBTUSD", constants.Side_Sell, "10000", "1", position_id=12345)
    await ws.send_cmd(cmd)

    # looop
    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_take_profit_for_existing_position():
    ws = await get_client()

    async def handle(ws, msg):
        print(msg)

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)

    # create limit order and fill PositionId and PositionEffect fields
    cmd = helpers.limit_order(1012833459, id("limit-order"), "XBTUSD", constants.Side_Sell, "10000", "1")
    helpers.for_position(cmd, 123456)
    await ws.send_cmd(cmd)

    # looop
    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_cancel():
    ws = await get_client()

    # example of three type of cancelation
    ids = [id("limit-order-1"), id("limit-order-2"), id("limit-order-3")]
    async def handle(msg):
        # order was successfully accepted
        if msg.ExecType == constants.ExecType_NewExec:
            if msg.ClOrdId == ids[0]:
                await ws.cancel_by_order_id(8263200, id("cancel-1"), msg.OrderId, "BTC/USDT", constants.Side_Buy)

            if msg.ClOrdId == ids[1]:
                await ws.cancel_by_client_id(8263200, id("cancel-2"), msg.ClOrdId, "BTC/USDT", constants.Side_Buy)

            if msg.ClOrdId == ids[2]:
                cmd = helpers.cancel_from_execution_report(id("cancel-3"), msg)
                await ws.cancel(cmd)

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)
    await ws.limit_order(8263200, ids[0], "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    await ws.limit_order(8263200, ids[1], "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    await ws.limit_order(8263200, ids[2], "BTC/USDT", constants.Side_Buy, "10000", "0.01")

    # looop
    while True:
        await asyncio.sleep(20, loop=loop)

async def example_of_receiving_all_order_and_canceling():
    ws = await get_client()

    # remove default listeners that was added in get_client()
    ws.remove_listener(constants.MsgType_OrderMassStatusResponse)

    done = asyncio.Event()
    orders = []
    async def handle(ws, msg):
        if msg.RejectReason:
            raise Exception(msg.Text)

        orders.extend(msg.Orders)
        done.set()

    ws.listen_type(constants.MsgType_OrderMassStatusResponse, handle)
    await ws.orders(1012833459)
    await done.wait()

    canceled = asyncio.Event()
    counter = 0
    async def handle_execution_report(ws, msg):
        nonlocal counter
        if msg.ExecType == constants.ExecType_CanceledExec:
            for o in orders:
                if o.OrderId == msg.OrderId:
                    counter += 1
       
            if counter == len(orders):
                canceled.set()

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle_execution_report)
    for order in orders:
        cmd = helpers.cancel_from_execution_report(id("cancel"), order)
        await ws.cancel(cmd)

    await canceled.wait()


async def example_of_replace():
    ws = await get_client()

    async def handle(ws, msg):
        # order was successfully accepted
        if msg.ExecType == constants.ExecType_NewExec:
            cmd = helpers.replace_from_execution_report(id("replace"), msg)
            # replacing order quantity
            cmd.OrderQty = "2"
            await ws.replace(cmd)

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)
    await ws.limit_order(1012833459, id("limit-order"), "XBTUSD", constants.Side_Buy, "10000", "1")

    # looop
    while True:
        await asyncio.sleep(20, loop=loop)

async def example_of_sync_limit_order():
    ws = await get_client()


    done = asyncio.Event()
    order_id = id("limit-order")
    fill_qty = "0"
    async def handle(ws, msg):
        nonlocal fill_qty
        # wait to fill order
        if msg.ExecType == constants.ExecType_Trade and msg.ClOrdId == order_id:
            fill_qty = msg.LastQty
            done.set()

    ws.listen_type(constants.MsgType_ExecutionReportMsgType, handle)
    await ws.limit_order(8263200, order_id, "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    await done.wait()
    assert fill_qty == "0.01"


async def example_of_getting_open_positions():
    ws = await get_client()

    # remove default listeners that was added in get_client()
    ws.remove_listener(constants.MsgType_MassPositionReport)

    done = asyncio.Event()
    positions = []
    async def handle(ws, msg):
        if msg.RejectReason:
            raise Exception(msg.Text)

        positions.extend(msg.OpenPositions)
        done.set()

    ws.listen_type(constants.MsgType_MassPositionReport, handle)
    await ws.positions(1012833459)
    await done.wait()
    print(positions)


async def example_of_getting_balances():
    ws = await get_client()

    # remove default listeners that was added in get_client()
    ws.remove_listener(constants.MsgType_AccountStatusReport)

    done = asyncio.Event()
    balances = []
    async def handle(ws, msg):
        if msg.RejectReason:
            raise Exception(msg.Text)

        if msg.AccountStatusRequestId == "req-id-1":
            print(msg)
            balances.extend(msg.Balances)
            done.set()

    ws.listen_type(constants.MsgType_AccountStatusReport, handle)
    await ws.account_status_report(8263118, request_id="req-id-1")
    #  await ws.account_status_report(1012833459, request_id="req-id-1")
    await done.wait()
    print(balances)


if __name__ == "__main__":
    examples = {name:obj for name,obj in inspect.getmembers(sys.modules[__name__])  if (inspect.isfunction(obj) and  name.startswith('example'))}
    
    if len(sys.argv) < 2:
        print("provide an example name")
        sys.exit()
        
    example = sys.argv[1]
    if example not in examples:
        print("uknown example")
        sys.exit()

    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(examples[example]())
