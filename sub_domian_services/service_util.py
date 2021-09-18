import datetime


def is_none_or_empty(val):
    if val is None:
        return True
    if isinstance(val, str):
        return len(val.strip()) == 0 or val.strip() == ''
    if isinstance(val, dict) or isinstance(val, list) or isinstance(val, tuple):
        return len(val) == 0


def default(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
