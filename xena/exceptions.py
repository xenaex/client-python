

class UnknownMsgTypeException(Exception):
    def __init__(self, msg_type):
        super().__init__('Unknown or unsupported MsgType "{}"'.format(msg_type))


class LoginException(Exception):
    pass
