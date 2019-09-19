import simplejson as json


class UnknownMsgTypeException(Exception):
    def __init__(self, msg_type):
        super().__init__('Unknown or unsupported MsgType "{}"'.format(msg_type))


class LoginException(Exception):
    pass


class RequestException(Exception):

    def __init__(self, response, status_code, text=None):
        self.error = None
        try:
            json_res = json.loads(text)
            if 'error' in json_res:
                self.error = json_res['error']
            if '1328' in json_res:
                self.error = json_res['1328']
        except Exception:
            pass

        self.status_code = status_code
        self.response = response
        self.request = getattr(response, 'request', None)

    def __str__(self):  # pragma: no cover
        if self.error is None:
            return 'RequestException({}): {}'.format(self.status_code, self.response)
        else:
            return 'RequestException({}): {}'.format(self.status_code, self.error)
