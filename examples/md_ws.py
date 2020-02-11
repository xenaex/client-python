import asyncio
import logging
import sys
import inspect

from xena.websocket import XenaMDWebsocketClient
import xena.proto.constants as constants

loop = None


async def connect(ws):
    while True:
        try:
            await ws.connect()
            break
        except Exception as e:
            print("exception {}".format(e))
            await asyncio.sleep(1)


async def example_of_dom():
    global loop
    
    async def handle(ws, msg):
        print(msg)

    async def on_connection_close(ws, e):
        await connect(ws)
        await ws.dom("BTC/USDT", handle, market_depth=10, aggregation=5)

    ws = XenaMDWebsocketClient(loop)
    ws.on_connection_close(on_connection_close)
    await connect(ws)

    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_candles():
    global loop
    
    async def handle(ws, msg):
        print(msg)

    async def on_connection_close(ws, e):
        await connect(ws)
        await ws.candles("BTC/USDT", handle, timeframe="1h", throttle_interval=250, throttle_unit=constants.ThrottleTimeUnit_Milliseconds)

    ws = XenaMDWebsocketClient(loop)
    ws.on_connection_close(on_connection_close)
    await connect(ws)

    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_trades():
    global loop
    
    async def handle(ws, msg):
        print(msg)

    async def on_connection_close(ws, e):
        await connect(ws)
        trade_stream_id = await ws.trades("BTC/USDT", handle)

        #  repeated subscription to the same stream is prohibited and will raise KeyError
        try:
            await ws.trades("BTC/USDT", handle)
        except KeyError as e:
            print(e)

        await ws.unsubscribe(trade_stream_id)
        await ws.trades("BTC/USDT", handle)

    ws = XenaMDWebsocketClient(loop)
    ws.on_connection_close(on_connection_close)
    await connect(ws)

    while True:
        await asyncio.sleep(20, loop=loop)


async def example_of_marketwatch():
    global loop
    
    async def handle(ws, msg):
        print(msg)

    async def on_connection_close(ws, e):
        await connect(ws)
        await ws.market_watch(handle)

    ws = XenaMDWebsocketClient(loop)
    ws.on_connection_close(on_connection_close)
    await connect(ws)

    while True:
        await asyncio.sleep(20, loop=loop)


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
