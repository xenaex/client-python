import simplejson as json
import google.protobuf.descriptor as descriptor

import xena.proto.constants as constants
import xena.proto.auth_pb2 as auth_pb2
import xena.proto.common_pb2 as common_pb2
import xena.proto.margin_pb2 as margin_pb2
import xena.proto.market_pb2 as market_pb2
import xena.proto.order_pb2 as order_pb2
import xena.proto.balance_pb2 as balance_pb2
import xena.proto.positions_pb2 as positions_pb2
import xena.exceptions as exceptions


TYPES = {
    constants.MsgType_UnknownMsgType: None,
    constants.MsgType_RejectMsgType: order_pb2.Reject,
    constants.MsgType_ExecutionReportMsgType: order_pb2.ExecutionReport,
    constants.MsgType_OrderCancelRejectMsgType: order_pb2.OrderCancelReject,
    constants.MsgType_LogonMsgType: auth_pb2.Logon,
    constants.MsgType_TradeCaptureReportMsgType: market_pb2.MarketDataRefresh,
    constants.MsgType_OrderMassStatusRequest: order_pb2.OrderStatusRequest,
    constants.MsgType_AccountStatusReportRequest: balance_pb2.AccountStatusReportRequest,
    constants.MsgType_AccountStatusReport: balance_pb2.BalanceIncrementalRefresh,
    constants.MsgType_AccountStatusUpdateReport: balance_pb2.BalanceIncrementalRefresh,
    constants.MsgType_NewOrderSingleMsgType: order_pb2.NewOrderSingle,
    constants.MsgType_NewOrderListMsgType: order_pb2.NewOrderList,
    constants.MsgType_OrderCancelRequestMsgType: order_pb2.OrderCancelRequest,
    constants.MsgType_OrderCancelReplaceRequestMsgType: order_pb2.OrderCancelReplaceRequest,
    constants.MsgType_OrderStatusRequest: order_pb2.OrderStatusRequest,
    constants.MsgType_ListStatus: order_pb2.ListStatus,
    constants.MsgType_MarketDataRequest: market_pb2.MarketDataRequest,
    constants.MsgType_MarketDataSnapshotFullRefresh: market_pb2.MarketDataRefresh,
    constants.MsgType_MarketDataIncrementalRefresh: market_pb2.MarketDataRefresh,
    constants.MsgType_MarketDataRequestReject: market_pb2.MarketDataRequestReject,
    constants.MsgType_OrderMassStatusResponse: order_pb2.OrderMassStatusResponse,
    constants.MsgType_PositionMaintenanceRequest: positions_pb2.PositionMaintenanceRequest,
    constants.MsgType_PositionMaintenanceReport: positions_pb2.PositionMaintenanceReport,
    constants.MsgType_RequestForPositions: positions_pb2.PositionsRequest,
    constants.MsgType_PositionReport: positions_pb2.PositionReport,
    constants.MsgType_MassPositionReport: positions_pb2.MassPositionReport,
    constants.MsgType_MarginRequirementReport: margin_pb2.MarginRequirementReport,
    constants.MsgType_Heartbeat: common_pb2.Heartbeat
}

def to_json(msg):
    """Convert protobuf message to json string"""

    result = {}
    _read_from(result, msg)
    return json.dumps(result)


def to_fix_json(msg):
    """Convert protobuf message to json string with fix protocol fields"""

    result = {}
    _read_from(result, msg, use_fix=True)
    return json.dumps(result, separators=(',', ':'))


def _read_from(result, msg, use_fix=False):
    for field in msg.DESCRIPTOR.fields:
        value = getattr(msg, field.name)
        field_name = _get_field_name(field, use_fix)
        if field.type == descriptor.FieldDescriptor.TYPE_MESSAGE:
            if field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
                if value:
                    result[field_name] = []
                    for in_value in value:
                        in_result = {}
                        _read_from(in_result, in_value, use_fix)
                        result[field_name].append(in_result)
            else:
                if value != field.default_value:
                    result[field_name] = {}
                    _read_from(result[field_name], value, use_fix)
        else:
            if field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
                if value:
                    result[field_name] = []
                    for in_value in value:
                        result[field_name].append(in_value)
            else:
                if value != field.default_value:
                    result[field_name] = value


def from_json(raw_data):
    """Convert json string to protobuf message"""

    data = json.loads(raw_data)
    if isinstance(data, list):
        result = []
        for element in data:
            if isinstance(element, dict):
                result.append(from_dict(element))
            else:
                return data

        return result

    return from_dict(data)


def from_dict(data):
    """Convert dict to protobuf message"""

    if "msgType" in data:
        if data["msgType"] == constants.MsgType_UnknownMsgType:
            raise exceptions.UnknownMsgTypeException(constants.MsgType_UnknownMsgType)

        msg_type = data["msgType"]
        if msg_type not in TYPES or TYPES[msg_type] is None:
            raise exceptions.UnknownMsgTypeException(msg_type)

        msg = TYPES[msg_type]()
        _fill_from(msg, data)
        return msg

    return data


def from_fix_json(raw_data):
    """Convert json string with fix protocol names to protobuf message"""

    data = json.loads(raw_data)

    if "35" not in data or data["35"] == constants.MsgType_UnknownMsgType:
        raise exceptions.UnknownMsgTypeException(constants.MsgType_UnknownMsgType)

    msg_type = data["35"]
    if msg_type not in TYPES or TYPES[msg_type] is None:
        raise exceptions.UnknownMsgTypeException(msg_type)

    msg = TYPES[msg_type]()
    _fill_from(msg, data, use_fix=True)

    return msg

def _fill_from(msg, data, use_fix=False):
    for field in msg.DESCRIPTOR.fields:
        field_name = _get_field_name(field, use_fix)
        if field_name in data:
            value = data[field_name]
            if field.type == descriptor.FieldDescriptor.TYPE_MESSAGE:
                if field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
                    for in_value in value:
                        attr = getattr(msg, field.name).add()
                        _fill_from(attr, in_value, use_fix)
                else:
                    attr = getattr(msg, field.name)
                    _fill_from(attr, value, use_fix)
            else:
                if field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
                    attr = getattr(msg, field.name)
                    for in_value in value:
                        attr.append(in_value)
                else:
                    setattr(msg, field.name, data[field_name])


def _get_field_name(field, use_fix=False):
    if use_fix:
        return str(field.number)

    if hasattr(field, "json_name"):
        return field.json_name

    return field.name
