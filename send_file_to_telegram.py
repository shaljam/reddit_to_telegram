import os
from datetime import datetime

from telegram.ext import Updater

import ffmpeg_util
import utils


def send_to_telegram(file_name):
    print('{}: sending {} to telegram channel...'.format(utils.beautiful_now(), file_name))
    updater = Updater("473515704:AAFvU-mxPNHOD98iagHdfaCPAeOAduIw-1M")

    scaled_path = '{}-{}-scaled.mp4'.format(file_name, int(datetime.now().timestamp() * 1e3))
    scaled = ffmpeg_util.scale_video(file_name, scaled_path, 360)

    if not scaled:
        print('{}: failed to scale {}'.format(utils.beautiful_now(), file_name))
        return False

    print('{}: scaled {} to {}'
          .format(utils.beautiful_now(), file_name, os.path.getsize(file_name), os.path.getsize(scaled_path)))
    # os.remove(file_name)
    file_name = scaled_path

    print('{}: sending {} sized {} to telegram channel...'
          .format(utils.beautiful_now(), file_name, os.path.getsize(file_name)))

    with open(file_name, 'rb') as fo:
        try:
            updater.bot.send_video(chat_id='@GifsSubreddit', video=fo,
                                   caption='test 🤓',
                                   timeout=60)
            print('{}: uploaded {} to telegram.'.format(utils.beautiful_now(), file_name))
        except Exception as e:
            print('{} {}'.format(file_name, e))
            pass
