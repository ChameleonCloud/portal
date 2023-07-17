import logging

LOG = logging.getLogger(__name__)


class EnforcementException(Exception):
    """Base enforcement Exception.
    To correctly use this class, inherit from it and define
    a 'msg_fmt' and 'code' properties.
    """

    msg_fmt = "An unknown exception occurred"
    code = 403

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs
        self.kwargs.setdefault("code", self.code)
        try:
            self.message = message or self.msg_fmt % kwargs
        except KeyError:
            # kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            LOG.exception("Exception in string format operation")
            for name, value in self.kwargs.items():
                LOG.error("%(name)s: %(value)s", {"name": name, "value": value})
            self.message = self.msg_fmt
        super().__init__(self.message)


class BillingError(EnforcementException):
    msg_fmt = "Not authorized"


class LeasePastExpirationError(EnforcementException):
    msg_fmt = "Cannot create reservation beyond allocation expiration date"
