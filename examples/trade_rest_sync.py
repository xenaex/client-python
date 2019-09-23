import asyncio
import logging
import time
import sys
import inspect

import xena.proto.constants as constants
import xena.helpers as helpers
from xena.rest import XenaTradingSyncClient


def id(prefix):
    timestamp = int(time.time())
    return prefix + '-' + str(timestamp)


def get_client():
    api_key = 'EmfLDuT0hitGG7LjzIh-Xc4APzzanGd_Zq5ivAjczuI='
    api_secret = '307702010104205911735f6ce66390cc90976f90333ae416d8c07cf94be24f6f373c7f8fe74180a00a06082a8648ce3d030107a14403420004107fd20d2ab5c6299618f6bb611b2dc42d3c985fa0f77754955f9945e9e843212c79d684f7cbe56fa245029282ace128aba13fa709d0b23226087867dc436ff9'
    rest = XenaTradingSyncClient(api_key, api_secret)

    return rest


def example_of_market_order():
    rest = get_client()

    resp = rest.market_order(8263118, id("market-order"), "BTC/USDT", constants.Side_Buy, "0.01")
    print(resp)

    # or using helpers method
    cmd = helpers.market_order(8263118, id("market-order"), "BTC/USDT", constants.Side_Buy, "0.01")
    resp = rest.order(cmd)
    print(resp)


def example_of_limit_order():
    rest = get_client()

    resp = rest.limit_order(8263118, id("limit-order"), "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    print(resp)

    # or using helpers method
    cmd = helpers.limit_order(8263118, id("limit-order"), "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    restp = rest.order(cmd)
    print(resp)


def example_of_stop_order():
    rest = get_client()

    resp = rest.stop_order(8263118, id("stop-order"), "BTC/USDT", constants.Side_Sell, "8000", "0.01")
    print(resp)

    # or using helpers method
    cmd = helpers.stop_order(8263118, id("stop-order"), "BTC/USDT", constants.Side_Sell, "8000", "0.01")
    resp = rest.order(cmd)
    print(resp)


def example_of_sltp_group():
    rest = get_client()

    cmd = helpers.limit_order(1012833458, id("limit-order-with-sltp"), "XBTUSD", constants.Side_Buy, "10000", "1")
    helpers.add_trailing_stop_loss(cmd, "500")
    helpers.add_take_profit(cmd, "10500")
    resp = rest.order(cmd)
    print(resp)

    # or
    cmd = helpers.limit_order(1012833458, id("limit-order-with-sltp"), "XBTUSD", constants.Side_Buy, "10000", "1", trailing_offset="500", take_profit_price="10500")
    resp = rest.order(cmd)
    print(resp)


def example_of_stop_loss_for_existing_position():
    rest = get_client()

    # create stop order and fill PositionID and PositionEffect fields
    cmd = helpers.stop_order(1012833458, id("stop-order"), "XBTUSD", constants.Side_Sell, "10000", "1")
    helpers.for_position(cmd, 130723016)
    resp = rest.order(cmd)
    print(resp)

    # or
    cmd = helpers.stop_order(1012833458, id("stop-order"), "XBTUSD", constants.Side_Sell, "10000", "1", position_id=12345)
    resp = rest.order(cmd)
    print(resp)


def example_of_take_profit_for_existing_position():
    rest = get_client()

    # create limit order and fill PositionID and PositionEffect fields
    cmd = helpers.limit_order(1012833458, id("limit-order"), "XBTUSD", constants.Side_Sell, "10000", "1")
    helpers.for_position(cmd, 130723016)
    resp = rest.order(cmd)
    print(resp)


def example_of_cancel():
    rest = get_client()

    # example of three type of cancelation
    ids = [id("limit-order-1"), id("limit-order-2"), id("limit-order-3")]

    resps = []
    resp1 = rest.limit_order(8263118, ids[0], "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    resps.append(resp1)
    resp2 = rest.limit_order(8263118, ids[1], "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    resps.append(resp2)
    resp3 = rest.limit_order(8263118, ids[2], "BTC/USDT", constants.Side_Buy, "10000", "0.01")
    resps.append(resp3)

    for msg in resps:
        if msg.ExecType == constants.ExecType_NewExec:
            if msg.ClOrdId == ids[0]:
                cresp = rest.cancel_by_order_id(8263118, id("cancel-1"), msg.OrderId, "BTC/USDT", constants.Side_Buy)
                print(cresp)

            if msg.ClOrdId == ids[1]:
                cresp = rest.cancel_by_client_id(8263118, id("cancel-2"), msg.ClOrdId, "BTC/USDT", constants.Side_Buy)
                print(cresp)

            if msg.ClOrdId == ids[2]:
                cmd = helpers.cancel_from_execution_report(id("cancel-3"), msg)
                cresp = rest.cancel(cmd)
                print(cresp)


def example_of_replace():
    rest = get_client()

    resp = rest.limit_order(1012833458, id("limit-order"), "XBTUSD", constants.Side_Buy, "10000", "1")
    print(resp)

    cmd = helpers.replace_from_execution_report(id("replace"), resp)
    # replacing order quantity
    cmd.OrderQty = "2"
    resp = rest.replace(cmd)
    print(resp)


def example_of_positions_collapse():
    rest = get_client()
    for account in rest.accounts():
        if helpers.is_margin(account):
            resp = rest.collapse_positions(account, "XBTUSD")
            print(resp)


def example_of_positions():
    rest = get_client()
    for account in rest.accounts():
        if helpers.is_margin(account):
            resp = rest.positions(account)
            print(resp)


def example_of_positions_history():
    # look up documentation to get all available filters
    rest = get_client()
    for account in rest.accounts():
        if helpers.is_margin(account):
            resp = rest.positions_history(account)
            print(resp)


def example_of_orders():
    rest = get_client()
    for account in rest.accounts():
        resp = rest.orders(account)
        print(resp)


def example_of_trade_history():
    # look up documentation to get all available filters
    rest = get_client()
    for account in rest.accounts():
        resp = rest.trade_history(account)
        print(resp)


def example_of_balances():
    rest = get_client()
    for account in rest.accounts():
        resp = rest.balance(account)
        print(resp)


def example_of_margin_requirements():
    rest = get_client()
    for account in rest.accounts():
        if helpers.is_margin(account):
            resp = rest.margin_requirements(account)
            print(resp)


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
    examples[example]()
