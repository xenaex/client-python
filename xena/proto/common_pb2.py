# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: common.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='common.proto',
  package='api',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n\x0c\x63ommon.proto\x12\x03\x61pi\" \n\rMsgTypeHeader\x12\x0f\n\x07MsgType\x18# \x01(\t\"E\n\tHeartbeat\x12\x0f\n\x07MsgType\x18# \x01(\t\x12\x11\n\tTestReqID\x18p \x01(\t\x12\x14\n\x0cTransactTime\x18< \x01(\x03\x62\x06proto3')
)




_MSGTYPEHEADER = _descriptor.Descriptor(
  name='MsgTypeHeader',
  full_name='api.MsgTypeHeader',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='MsgType', full_name='api.MsgTypeHeader.MsgType', index=0,
      number=35, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=21,
  serialized_end=53,
)


_HEARTBEAT = _descriptor.Descriptor(
  name='Heartbeat',
  full_name='api.Heartbeat',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='MsgType', full_name='api.Heartbeat.MsgType', index=0,
      number=35, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='TestReqID', full_name='api.Heartbeat.TestReqID', index=1,
      number=112, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='TransactTime', full_name='api.Heartbeat.TransactTime', index=2,
      number=60, type=3, cpp_type=2, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=55,
  serialized_end=124,
)

DESCRIPTOR.message_types_by_name['MsgTypeHeader'] = _MSGTYPEHEADER
DESCRIPTOR.message_types_by_name['Heartbeat'] = _HEARTBEAT
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

MsgTypeHeader = _reflection.GeneratedProtocolMessageType('MsgTypeHeader', (_message.Message,), dict(
  DESCRIPTOR = _MSGTYPEHEADER,
  __module__ = 'common_pb2'
  # @@protoc_insertion_point(class_scope:api.MsgTypeHeader)
  ))
_sym_db.RegisterMessage(MsgTypeHeader)

Heartbeat = _reflection.GeneratedProtocolMessageType('Heartbeat', (_message.Message,), dict(
  DESCRIPTOR = _HEARTBEAT,
  __module__ = 'common_pb2'
  # @@protoc_insertion_point(class_scope:api.Heartbeat)
  ))
_sym_db.RegisterMessage(Heartbeat)


# @@protoc_insertion_point(module_scope)
