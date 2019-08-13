# Official Xena websocket client python library

For API documentation check out [Help Center](https://support.xena.exchange/support/solutions/folders/44000161002)


#### Install

```bash
    pip install python-xena
```


#### Market Data example

```python
	import asyncio

	from xena.websocket import XenaMDWebsocketClient
	import xena.proto.constants as constants

	loop = None

	async def main():
		global loop

		# create client instance and connect
		ws = XenaMDWebsocketClient(loop)
		await connect(ws)
		
		async def handle(ws, msg):
			print(msg)

		await ws.candles("BTC/USDT", handle, timeframe="1h", throttle_interval=250, throttle_unit=constants.ThrottleTimeUnit_Milliseconds)

		while True:
			await asyncio.sleep(20, loop=loop)


	if __name__ == "__main__":
		loop = asyncio.get_event_loop()
		loop.run_until_complete(main())
```

#### Trading Example

Register an account with [Xena](https://trading.xena.exchange/registration). Generate an API Key and assign relevant permissions.
	
```
	import asyncio
	import time

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

		api_key = ''
		api_secret = ''
		ws = XenaTradingWebsocketClient(api_key, api_secret, loop)
		ws.on_connection_close(on_connection_close)

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

	if __name__ == "__main__":
		loop = asyncio.get_event_loop()
		loop.run_until_complete(example_of_market_order())
```

For more examples check out "exmaples" folder
