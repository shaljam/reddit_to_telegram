#!/usr/bin/env python

from telegram.ext import Updater
import logging
import praw
import time
import os.path
import requests

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater("473515704:AAFvU-mxPNHOD98iagHdfaCPAeOAduIw-1M")

    reddit = praw.Reddit(client_id='5HcYHPhZFHR14Q',
                         client_secret='1RVyYaa-0it7zu2hCI2JVo80tuw',
                         user_agent='telegram-poster')

    last_id = ''

    if os.path.isfile('last_id'):
        with open('last_id', mode='rt') as f:
            last_id = f.read()

    while True:
        print('getting submissions after {}'.format(last_id))
        start_time = time.time()
        first = True
        for submission in reddit.subreddit('gifs').hot(limit=10, params={'before': '{}'.format(last_id)}):
            if submission.distinguished and submission.distinguished == 'moderator':
                continue

            if first:
                last_id = submission.name

                with open('last_id', mode='wt') as f:
                    f.write(last_id)

                first = False

            caption = '❄     {}\n🙋     {}\n\n{}'.format(submission.title, submission.author.name, submission.shortlink)

            candidate_urls = []

            try:
                gif = submission.preview['images'][0]['variants']['gif']
                source = gif['source']

                candidate_urls.append(source)

                if 'resolutions' in gif and gif['resolutions']:
                    resolutions = gif['resolutions']
                    candidate_urls.extend(resolutions)
            except KeyError:
                pass

            if submission.media:
                try:
                    candidate_urls.append(
                        {'url': submission.media['reddit_video']['scrubber_media_url'], 'width': 200, 'height': 200})

                except KeyError:
                    pass

                try:
                    candidate_urls.append(
                        {'url': submission.media['oembed']['thumbnail_url'], 'width': 200, 'height': 200})

                except KeyError:
                    pass

            if not len(candidate_urls):
                continue

            dim = 'width'
            if candidate_urls[0]['height'] > candidate_urls[0]['width']:
                dim = 'height'

            candidate_urls.sort(key=lambda x: x[dim], reverse=True)

            while len(candidate_urls):
                selected_url = None
                for cr in candidate_urls:
                    if cr[dim] <= 400:
                        selected_url = cr
                        break

                if not selected_url:
                    selected_url = candidate_urls[-1]

                candidate_urls.remove(selected_url)

                url = selected_url['url']

                response = requests.head(url)
                if response.status_code == 200:
                    length = response.headers['Content-Length']

                    if int(length) > 20 * 1000 * 1000:
                        continue
                else:
                    continue

                # try downloading with telegram
                try:
                    updater.bot.send_video(chat_id='@GifsSubreddit', video=url, caption=caption,
                                           timeout=60)
                    print('sent {}, {}'.format(submission.name, submission.title))
                    break
                except Exception as e:
                    print('{} {}'.format(submission.name, e))
                    pass

                # download
                response = requests.get(url, stream=True)
                if response.status_code == 200 and response.headers['content-type'] == 'image/gif':
                    fname = submission.name
                    print('Downloading {}...'.format(fname))

                    with open(fname, 'wb') as fo:
                        for chunk in response.iter_content(4096):
                            fo.write(chunk)

                    uploaded = False
                    with open(fname, 'rb') as fo:
                        try:
                            updater.bot.send_video(chat_id='@GifsSubreddit', video=fo,
                                                   caption=caption,
                                                   timeout=60)
                            print('upload {}, {}'.format(submission.name, submission.title))
                            uploaded = True
                        except Exception as e:
                            print('{} {}'.format(submission.name, e))
                            pass

                    os.remove(fname)
                    if uploaded:
                        break
                else:
                    continue

        elapsed_time = time.time() - start_time

        if elapsed_time < 20:
            print('sleeping...')
            time.sleep(120)


if __name__ == '__main__':
    main()
