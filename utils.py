import ujson
from datetime import datetime
from pytz import timezone, UTC


ONE_WEEK_SECONDS = 60 * 60 * 24 * 7


def beautiful_now(tehran=True):
    date = datetime.today()

    if tehran:
        date = date.replace(tzinfo=timezone('Asia/Tehran'))
        tz = 'Tehran'
    else:
        date = date.replace(tzinfo=UTC)
        tz = 'UTC'

    return date.strftime('%a %b %d %Y %H:%M:%S ' + tz)


def load_json(path, data_if_empty):
    if not path.is_file():
        save_json(path, data_if_empty)
        return data_if_empty

    with open(path, 'r') as data_file:
        return ujson.load(data_file)


def save_json(path, data):
    with open(path, 'w') as data_file:
        ujson.dump(data, data_file)