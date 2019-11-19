import asyncio
import logging
import sys
import inspect
from datetime import datetime, timedelta

from xena.rest import XenaMDClient

loop = None


async def example_of_candles():
    rest = XenaMDClient(loop)
    ts_from = int((datetime.today() - timedelta(days=1)).timestamp() * 1000000000) # from in nanosecond's
    res = await rest.candles("BTC/USDT", timeframe='1m', ts_from=ts_from)
    print(res)


async def example_of_dom():
    rest = XenaMDClient(loop)
    res = await rest.dom("BTC/USDT")
    print(res)


async def example_of_trades():
    rest = XenaMDClient(loop)
    ts_from = ts_from=int((datetime.today() - timedelta(days=10)).timestamp()) * 1000000000 # nanoseconds
    ts_to =  int(datetime.now().timestamp())*1000000000 # nanoseconds
    res = await rest.trades("XBTUSD", ts_from=ts_from, ts_to=ts_to)
    print(res)

async def example_of_instruments():
    rest = XenaMDClient(loop)
    res = await rest.instruments()
    print(res)


async def example_of_server_time():
    rest = XenaMDClient(loop)
    res = await rest.server_time()
    print(res)


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
