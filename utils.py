import time
import ujson
from datetime import datetime

from pytz import timezone, UTC

ONE_HOUR_SECONDS = 60 * 60
ONE_WEEK_SECONDS = ONE_HOUR_SECONDS * 24 * 7


def beautiful_date(date, tehran=True):
    if tehran:
        date = date.replace(tzinfo=timezone('Asia/Tehran'))
        tz = 'Tehran'
    else:
        date = date.replace(tzinfo=UTC)
        tz = 'UTC'

    return date.strftime('%a %b %d %Y %H:%M:%S ' + tz)


def beautiful_now(tehran=True):
    return beautiful_date(datetime.today(), tehran=tehran)


def load_json(path, data_if_empty):
    if not path.is_file():
        save_json(path, data_if_empty)
        return data_if_empty

    with open(path, 'r') as data_file:
        return ujson.load(data_file)


def save_json(path, data):
    with open(path, 'w') as data_file:
        ujson.dump(data, data_file)


def human_format(num, precision=1, suffixes=['', 'k', 'm', 'b']):
    if abs(num) < 10000:
        return f'{num}'

    m = sum([abs(num / 1000.0 ** x) >= 1 for x in range(1, len(suffixes))])
    return f'{num/1000.0**m:.{precision}f}{suffixes[m]}'


def lprint(msg, include_time=True, tehran=True):
    time_prefix = f'{beautiful_now(tehran=tehran)}: ' if include_time else ''
    print(f'{time_prefix}{msg}')


def sleep_until(sleep_time):
    now = datetime.now()
    until = datetime.fromtimestamp(int(now.timestamp()) + sleep_time)
    lprint(f'sleeping for {sleep_time} seconds until {beautiful_date(until)}')
    time.sleep(sleep_time)
