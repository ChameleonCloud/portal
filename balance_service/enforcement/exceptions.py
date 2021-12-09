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
        self.message = message

        if "code" not in self.kwargs:
            self.kwargs["code"] = self.code

        if not message:
            try:
                self.message = self.msg_fmt % kwargs
            except KeyError:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception("Exception in string format operation")
                for name, value in kwargs.items():
                    LOG.error("%(name)s: %(value)s", {"name": name, "value": value})

                self.message = self.msg_fmt

        super(EnforcementException, self).__init__(message)


class BillingError(EnforcementException):
    msg_fmt = "Not authorized"
    code = 403
