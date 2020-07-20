# common.py
#
# Module common infrastructure
#

_FORMATTERS = dict()

def register_formatter(descriptor):
    """Decorator that registers a formatter class"""
    def passthrough(cls):
        _FORMATTERS[descriptor] = cls
        return cls
    return passthrough

def get_formatter(descriptor):
    if not descriptor in _FORMATTERS:
        print("descriptor must be one of:")
        print(_FORMATTERS.keys())
    return _FORMATTERS[descriptor]
