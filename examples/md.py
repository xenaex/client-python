import asyncio
import logging

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

    async def handle(ws, msg):
        print(msg)

    await ws.candles("BTC/USDT", handle, timeframe="1h", throttle_interval=250, throttle_unit=constants.ThrottleTimeUnit_Milliseconds)
    await ws.dom("BTC/USDT", handle)
    trade_stream_id = await ws.trades("BTC/USDT", handle)
    await ws.market_watch(handle)

    #  repeated subscription to the same stream is prohibited and will raise KeyError
    try:
        await ws.trades("BTC/USDT", handle)
    except KeyError as e:
        print(e)

    await ws.unsubscribe(trade_stream_id)
    await ws.trades("BTC/USDT", handle)


async def example():
    global loop

    async def on_connection_close(ws, e):
        await connect(ws)

    ws = XenaMDWebsocketClient(loop)
    ws.on_connection_close(on_connection_close)
    await connect(ws)


    while True:
        await asyncio.sleep(20, loop=loop)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(example())
