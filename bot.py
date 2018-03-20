#!/usr/bin/env python

import logging
import os.path
import time
import random
from datetime import datetime
from pathlib import Path

import praw
import requests
from telegram.ext import Updater

import utils
from ffmpeg_util import scale_video

posts_to_get_every_time = 26
posts_path = Path('data/posts.json')
used_posts_path = Path('data/used_posts.json')
accepted_content_types = ['image/gif', 'video/mp4']

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def get_new_posts(max_count_to_get):
    print('{}: getting new posts...'.format(utils.beautiful_now()))

    reddit = praw.Reddit(client_id='5HcYHPhZFHR14Q',
                         client_secret='1RVyYaa-0it7zu2hCI2JVo80tuw',
                         user_agent='telegram-poster')

    posts = []

    print('{}: getting max {} hot submissions'.format(utils.beautiful_now(), max_count_to_get))

    for submission in reddit.subreddit('gifs').hot(limit=max_count_to_get):
        if submission.distinguished and submission.distinguished == 'moderator':
            continue

        caption = '🔥 {}\n❄     {}\n🙋     {}\n{}'.format(
            utils.human_format(submission.score),
            submission.title,
            submission.author.name,
            submission.shortlink)

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

        posts.append({
            'id': submission.name,
            'process_time': int(datetime.now().timestamp()),
            'caption': caption,
            'candidate_urls': candidate_urls
        })

    print('{}: got {} hot submissions'.format(utils.beautiful_now(), len(posts)))
    return posts


def send_to_telegram(post):
    post_id = post['id']

    print('{}: sending {} to telegram channel...'.format(utils.beautiful_now(), post_id))
    updater = Updater("473515704:AAFvU-mxPNHOD98iagHdfaCPAeOAduIw-1M")

    candidate_urls = post['candidate_urls']

    while len(candidate_urls):
        selected_url = candidate_urls[0]

        candidate_urls.remove(selected_url)

        url = selected_url['url']

        # download
        response = requests.get(url, stream=True)
        if not (response.status_code == 200 and response.headers['content-type'] in accepted_content_types):
            print('{}: failed to download {}'.format(utils.beautiful_now(), url))
            continue

        file_name = 'downloaded_videos/{}-{}'.format(post_id, int(datetime.now().timestamp() * 1e3))
        print('{}: downloading {} to {}'.format(utils.beautiful_now(), url, file_name))

        with open(file_name, 'wb') as fo:
            for chunk in response.iter_content(128):
                fo.write(chunk)

        scaled_path = '{}-scaled.mp4'.format(file_name)
        scaled = scale_video(file_name, scaled_path, 360)

        if not scaled:
            print('{}: failed to scale {} with file {}'.format(utils.beautiful_now(), post_id, file_name))
            return False

        print('{}: scaled {} to {}'
              .format(utils.beautiful_now(), post_id, os.path.getsize(file_name), os.path.getsize(scaled_path)))
        # os.remove(file_name)
        file_name = scaled_path

        print('{}: sending {} sized {} to telegram channel...'
              .format(utils.beautiful_now(), post_id, os.path.getsize(file_name)))

        uploaded = False
        with open(file_name, 'rb') as fo:
            try:
                updater.bot.send_video(chat_id='@GifsSubreddit', video=fo,
                                       caption=post['caption'],
                                       timeout=60)
                print('{}: uploaded {} to telegram.'.format(utils.beautiful_now(), post_id))
                uploaded = True
            except Exception as e:
                print('{} {}'.format(post_id, e))
                pass

        # os.remove(file_name)
        if uploaded:
            return post

    return False


def get_post_to_send():
    posts = utils.load_json(posts_path, [])
    used_posts = utils.load_json(used_posts_path, [])
    used_posts_ids = list(post['id'] for post in used_posts)

    def remove_used_or_old():
        now = int(datetime.now().timestamp())

        # remove posts used or more than a week old
        for post in posts[:]:
            if post['id'] in used_posts_ids:
                posts.remove(post)
                continue

            if (now - post['process_time']) > utils.ONE_WEEK_SECONDS:
                posts.remove(post)

    remove_used_or_old()

    while not len(posts):
        posts = get_new_posts(posts_to_get_every_time)

        remove_used_or_old()

    utils.save_json(posts_path, posts)

    return posts[0]


def send_a_gif():
    used_posts = utils.load_json(used_posts_path, [])

    while True:
        post = get_post_to_send()
        sent = send_to_telegram(post)

        used_posts.append({
            'id': post['id'],
            'send_time': int(datetime.now().timestamp())
        })
        utils.save_json(used_posts_path, used_posts)

        if sent:
            break

        seconds = 60
        print('{}: failed to send post {}, sleeping {} seconds...'.format(utils.beautiful_now(), post['id'], seconds))
        time.sleep(seconds)

    now = int(datetime.now().timestamp())

    for post in used_posts[:]:
        if (now - post['send_time']) > utils.ONE_WEEK_SECONDS:
            used_posts.remove(post)

    utils.save_json(used_posts_path, used_posts)


def main():
    print('{}: hi!'.format(utils.beautiful_now()))

    while True:
        send_a_gif()

        sleep_time = 60 * random.randint(50, 70)
        now = datetime.now()
        until = datetime.fromtimestamp(int(now.timestamp()) + sleep_time)
        print('{}: sleeping for {} seconds until {}'
              .format(utils.beautiful_date(now), sleep_time, utils.beautiful_date(until)))
        time.sleep(sleep_time)


if __name__ == '__main__':
    main()
