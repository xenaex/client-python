import time

import xena.proto.order_pb2 as order_pb2
import xena.proto.constants as constants


def cancel_from_execution_report(cancel_id, execution_report):
    """Create OrderCancelRequest from given execution report
    For more info about OrderCancelRequest look at https://support.xena.exchange/support/solutions/articles/44000222082-ws-trading-api#order_cancel_request
    """

    cmd = order_pb2.OrderCancelRequest()
    cmd.MsgType = constants.MsgType_OrderCancelRequestMsgType
    cmd.ClOrdId = cancel_id
    cmd.OrigClOrdId = execution_report.ClOrdId
    cmd.Symbol = execution_report.Symbol
    cmd.Side = execution_report.Side
    cmd.TransactTime = int(time.time() * 1000000000)
    cmd.Account = execution_report.Account
    return cmd

def replace_from_execution_report(replace_id, execution_report):
    """Create OrderCancelReplaceRequest from given execution report
    For more info about OrderCancelReplaceRequest look at https://support.xena.exchange/support/solutions/articles/44000222082-ws-trading-api#order_cancel_replace_request
    """

    cmd = order_pb2.OrderCancelReplaceRequest()
    cmd.MsgType = constants.MsgType_OrderCancelReplaceRequestMsgType
    cmd.ClOrdId = replace_id
    cmd.OrigClOrdId = execution_report.ClOrdId
    cmd.Symbol = execution_report.Symbol
    cmd.Side = execution_report.Side
    cmd.TransactTime = int(time.time() * 1000000000)
    cmd.Account = execution_report.Account
    cmd.Price = execution_report.Price
    cmd.StopPx = execution_report.StopPx
    cmd.CapPrice = execution_report.CapPrice
    cmd.OrderQty = execution_report.OrderQty
    cmd.PegPriceType = execution_report.PegPriceType
    cmd.PegOffsetType = execution_report.PegOffsetType
    cmd.PegOffsetValue = execution_report.PegOffsetValue

    for element in execution_report.SLTP:
        sltp = cmd.SLTP.add()
        sltp.OrdType = element.OrdType
        sltp.Price = element.Price
        sltp.StopPx = element.StopPx
        sltp.CapPrice = element.CapPrice
        sltp.PegPriceType = element.PegPriceType
        sltp.PegOffsetType = element.PegOffsetType
        sltp.PegOffsetValue = element.PegOffsetValue

    return cmd

def order(
        account, client_order_id, ord_type, symbol, side, qty, price=None, stop_price=None,
        position_id=None, stop_loss_price=None, take_profit_price=None, trailing_offset=None, cap_price=None,
        time_in_force=None, exec_inst=[]
    ):
    """Create NewOrderSingle from given params
    For more info about NewOrderSingle look at https://support.xena.exchange/support/solutions/articles/44000222082-ws-trading-api#new_order_single
    More info about order types https://support.xena.exchange/support/solutions/articles/44000222011-order-types
    """

    cmd = order_pb2.NewOrderSingle()
    cmd.MsgType = constants.MsgType_NewOrderSingleMsgType
    cmd.OrdType = ord_type
    cmd.ClOrdId = client_order_id
    cmd.Symbol = symbol
    cmd.Side = side
    cmd.TransactTime = int(time.time() * 1000000000)
    cmd.OrderQty = qty
    cmd.Account = account

    if price is not None:
        cmd.Price = price

    if stop_price is not None:
        cmd.StopPx = stop_price

    if position_id is not None:
        for_position(cmd, position_id)

    if stop_loss_price is not None:
        add_stop_loss(cmd, stop_loss_price)

    if take_profit_price is not None:
        add_take_profit(cmd, take_profit_price)

    if trailing_offset is not None:
        add_trailing_stop_loss(cmd, trailing_offset, cap_price)

    if time_in_force is not None:
        cmd.TimeInForce = time_in_force

    for value in exec_inst:
        cmd.ExecInst.append(value)

    return cmd


def market_order(account, client_order_id, symbol, side, qty, **kwargs):
    """Wrapper around order() method to create simple market order"""

    return order(account, client_order_id, constants.OrdType_Market, symbol, side, qty, **kwargs)

def limit_order(account, client_order_id, symbol, side, price, qty, **kwargs):
    """Wrapper around order() method to create simple limit order"""

    kwargs["price"] = price
    return order(account, client_order_id, constants.OrdType_Limit, symbol, side, qty, **kwargs)

def stop_order(account, client_order_id, symbol, side, stop_price, qty, **kwargs):
    """Wrapper around order() method to create simple stop order"""

    kwargs["stop_price"] = stop_price
    return order(account, client_order_id, constants.OrdType_Stop, symbol, side, qty, **kwargs)

def mit_order(account, client_order_id, symbol, side, stop_price, qty, **kwargs):
    """Wrapper around order() method to create simple "market if toucehd" order"""

    kwargs["stop_price"] = stop_price
    return order(account, client_order_id, constants.OrdType_MarketIfTouched, symbol, side, qty, **kwargs)

def for_position(cmd, position_id):
    """ Helper to make order for position close"""

    cmd.PositionID = position_id
    cmd.PositionEffect = constants.PositionEffect_Close

def add_stop_loss(cmd, stop_price):
    """ Helper to add stop loss template.
    For more info look at SLTP group in api documentation (https://support.xena.exchange/support/solutions/articles/44000222082-ws-trading-api)
    """

    sltp = cmd.SLTP.add()
    sltp.OrdType = constants.OrdType_Stop
    sltp.StopPx = stop_price

def add_trailing_stop_loss(cmd, trailing_offset, cap_price=None):
    """ Helper to add trailing stop loss template
    For more info look at SLTP group in api documentation (https://support.xena.exchange/support/solutions/articles/44000222082-ws-trading-api)
    """

    sltp = cmd.SLTP.add()
    sltp.OrdType = constants.OrdType_Stop
    sltp.PegPriceType = constants.PegPriceType_TrailingStopPeg
    sltp.PegOffsetType = constants.PegOffsetType_BasisPoints
    sltp.PegOffsetValue = trailing_offset
    if cap_price is not None:
        sltp.CapPrice = cap_price

def add_take_profit(cmd, price):
    """ Helper to add take profit template.
    For more info look at SLTP group in api documentation (https://support.xena.exchange/support/solutions/articles/44000222082-ws-trading-api)
    """

    sltp = cmd.SLTP.add()
    sltp.OrdType = constants.OrdType_Limit
    sltp.Price = price
