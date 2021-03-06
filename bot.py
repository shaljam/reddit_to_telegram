#!/usr/bin/env python

import logging
import os.path
import random
import re
import textwrap
import time
import traceback
from datetime import datetime
from pathlib import Path

import praw
import youtube_dl
from praw.models import MoreComments
from prawcore.exceptions import PrawcoreException
from telegram.ext import Updater
from youtube_dl.utils import YoutubeDLError

import utils
from ffmpeg_util import scale_video, is_file_image
from utils import lprint

posts_path = Path('data/posts.json')
used_posts_path = Path('data/used_posts.json')
accepted_content_types = ['image/gif', 'video/mp4']
config_path = Path('config.json')

min_score = "min_score"
wait_from = "wait_from"  # minutes
wait_to = "wait_to"  # minutes
posts_to_get_every_time = "posts_to_get_every_time"
max_posts_every_time = "max_posts_every_time"
no_posts_wait_time = "no_posts_wait_time"  # minutes
min_comment_score = "min_comment_score"
main_channel_id = "main_channel_id"
comments_channel_id = "comments_channel_id"
max_line_chars = "max_line_chars"
c_telegram_api_key = "telegram_api_key"
c_reddit_client_id = "reddit_client_id"
c_reddit_client_secret = "reddit_client_secret"
c_reddit_user_agent = "reddit_user_agent"
c_max_comments_message_length = "max_comments_message_length"
c_min_time_since_created = "min_time_since_created"  # minutes
c_subreddits = "subreddits"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

config = utils.load_json(config_path, {})


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"' % (update, error))


def reload_config():
    global config

    lprint('reloading config')
    config = utils.load_json(config_path, {})


def get_new_posts(max_count_to_get):
    used_posts_ids = list(post['id'] for post in utils.load_json(used_posts_path, []))

    print('{}: getting new posts...'.format(utils.beautiful_now()))

    reddit = praw.Reddit(
        client_id=config[c_reddit_client_id],
        client_secret=config[c_reddit_client_secret],
        user_agent=config[c_reddit_user_agent],
    )

    posts = []

    print(
        '{}: getting max {} hot submissions'.format(
            utils.beautiful_now(), max_count_to_get
        )
    )
    subreddits = (
        [
            "aww",
            "WatchPeopleDieInside",
            "funny",
            "gifs",
            "IdiotsInCars",
            "instantkarma",
            "Whatcouldgowrong",
        ]
        if c_subreddits not in config
        else config[c_subreddits]
    )

    for sr in subreddits:
        try:
            for submission in reddit.subreddit(sr).hot(limit=max_count_to_get):
                if submission.distinguished and submission.distinguished == 'moderator':
                    lprint(
                        f'skipping moderator\t '
                        f'submission {submission.id} {submission}'
                    )
                    continue

                # if submission.over_18:
                #     lprint(
                #         f'skipping over 18\t submission {submission.id} '
                #         f'{submission.title}'
                #     )
                #     continue

                if submission.score < config[min_score]:
                    lprint(
                        f'skipping min score\t submission {submission.id} '
                        f'{submission.title} with score {submission.score}'
                    )
                    continue

                if submission.id in used_posts_ids:
                    lprint(
                        f'skipping used\t\t submission {submission.id} '
                        f'{submission.title}'
                    )
                    continue

                if int(datetime.today().timestamp() - submission.created_utc) < (
                    60 * config[c_min_time_since_created]
                ):
                    lprint(
                        f'skipping very new\t submission {submission.id} '
                        f'{submission.title}'
                    )
                    continue

                posts.append(submission)
        except PrawcoreException:
            lprint(f'failed to get reddit submissions. will print stacktrace...')
            lprint(f'{traceback.format_exc()}')

    lprint(f'got {len(posts)} hot submissions')

    posts.sort(key=lambda x: x.score, reverse=True)
    posts = posts[: config[max_posts_every_time]]
    lprint(f'using first {config[max_posts_every_time]} hot submissions')

    return posts


def send_to_telegram(post):
    post_id = post.id
    post_title = post.title
    sr_name = post.subreddit.display_name

    print(
        '{}: sending {} {} to telegram channel...'.format(
            utils.beautiful_now(), post_id, post_title
        )
    )
    updater = Updater(config[c_telegram_api_key])

    ydl_opts = {
        'outtmpl': f'downloaded_videos/{youtube_dl.DEFAULT_OUTTMPL}',
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        url = post.url
        print(
            '{}: {} downloading {} with youtube-dl ...'.format(
                utils.beautiful_now(), post_id, url
            )
        )
        try:
            info = ydl.extract_info(url, download=True)
            file_name = ydl.prepare_filename(info)
            print(
                '{}: {} {} youtube-dl result {}'.format(
                    utils.beautiful_now(), post_id, url, file_name
                )
            )
        except YoutubeDLError:
            print(
                '{}: {} {} youtube-dl failed with exception.\n{}'.format(
                    utils.beautiful_now(), post_id, url, traceback.format_exc()
                )
            )
            return False

    is_image = is_file_image(file_name)

    if not is_image:
        scaled_path = '{}-scaled.mp4'.format(file_name)
        scaled, has_audio = scale_video(file_name, scaled_path, 360)

        if not scaled:
            print(
                '{}: failed to scale {} with file {}'.format(
                    utils.beautiful_now(), post_id, file_name
                )
            )
            return False

        print(
            '{}: {} scaled {} to {}'.format(
                utils.beautiful_now(),
                post_id,
                os.path.getsize(file_name),
                os.path.getsize(scaled_path),
            )
        )
        os.remove(file_name)
        file_name = scaled_path

    chat_id = f'@{config[main_channel_id]}'

    caption = (
        f'??? #{sr_name}\n'
        f'???? {post.title}\n\n'
        f'???? <code>{utils.human_format(post.score)}</code>\n'
        f'???? {post.shortlink}\n\n'
        f'{chat_id}'
    )

    uploaded = False
    with open(file_name, 'rb') as fo:
        try:
            print(
                '{}: sending {} {} sized {} to telegram channel @{}...'.format(
                    utils.beautiful_now(),
                    post_id,
                    post_title,
                    os.path.getsize(file_name),
                    config[main_channel_id],
                )
            )

            if is_image:
                result = updater.bot.send_photo(
                    chat_id=chat_id,
                    photo=fo,
                    caption=caption,
                    timeout=60,
                    parse_mode='HTML',
                )
            elif has_audio:
                result = updater.bot.send_video(
                    chat_id=chat_id,
                    video=fo,
                    caption=caption,
                    timeout=60,
                    parse_mode='HTML',
                )
            else:
                result = updater.bot.send_animation(
                    chat_id=chat_id,
                    animation=fo,
                    caption=caption,
                    timeout=60,
                    parse_mode='HTML',
                )

            print(
                '{}: uploaded {} {} to telegram channel @{}.'.format(
                    utils.beautiful_now(), post_id, post_title, config[main_channel_id]
                )
            )
            uploaded = True

            print(
                '{}: forwarding {} to @{}...'.format(
                    utils.beautiful_now(), post_id, config[comments_channel_id]
                )
            )

            _ = updater.bot.forward_message(
                f'@{config[comments_channel_id]}',
                f'@{config[main_channel_id]}',
                result.message_id,
            )

            print(
                '{}: forwarded {} to @{}.'.format(
                    utils.beautiful_now(), post_id, config[comments_channel_id]
                )
            )

            comments_header = 'Good comments from ????????:'

            def process_comment_forest(forest, current_length=0):
                forest_result = ''
                if current_length == 0:
                    forest_result = comments_header

                for comment in forest:
                    if isinstance(comment, MoreComments):
                        continue

                    if comment.depth > 2:
                        continue

                    if not (
                        (comment.depth + 1) * comment.score >= config[min_comment_score]
                    ):
                        continue

                    #  skip comment if it contains xml tags
                    if len(re.findall('<[a-z][\s\S]*>', comment.body)):
                        continue

                    line_start = "|    " * comment.depth
                    author = (
                        ''
                        if not comment.author
                        else f'<a href="https://www.reddit.com/user/{comment.author.name}">'
                        f'{comment.author.name}</a>'
                    )

                    comment_formatted = (
                        f'{line_start}'
                        f'{author}'
                        f'  <code>{utils.human_format(comment.score)}</code>'
                    )

                    line_chars = config[max_line_chars] - len(line_start)

                    comment_body = textwrap.fill(
                        comment.body, line_chars, break_long_words=False
                    )
                    for line in comment_body.splitlines():
                        comment_formatted = comment_formatted + f'\n{line_start}{line}'

                    line_break = f'\n{line_start}\n' * (
                        1 if len(forest_result) or current_length else 0
                    )
                    addition = f'{line_break}{comment_formatted}'

                    length_after_adding_current_comment = (
                        current_length + len(forest_result) + len(addition)
                    )
                    if (
                        length_after_adding_current_comment
                        > config[c_max_comments_message_length]
                    ):
                        break

                    if comment.replies:
                        replies_formatted = process_comment_forest(
                            comment.replies,
                            current_length=length_after_adding_current_comment,
                        )

                        forest_result += addition + replies_formatted
                    else:
                        forest_result += addition

                return forest_result

            comments = process_comment_forest(post.comments)

            if len(comments) > len(comments_header):
                print(
                    '{}: {} sending comments to @{}.'.format(
                        utils.beautiful_now(), post_id, config[comments_channel_id]
                    )
                )

                updater.bot.send_message(
                    chat_id=f'@{config[comments_channel_id]}',
                    text=comments,
                    parse_mode='HTML',
                    disable_web_page_preview=True,
                )

                print(
                    '{}: {} sent comments to @{}.'.format(
                        utils.beautiful_now(), post_id, config[comments_channel_id]
                    )
                )

        except Exception:
            lprint(
                f'failed to get send {post_id} {post_title} to telegram. will print stacktrace...'
            )
            lprint(f'{traceback.format_exc()}')
            pass

    os.remove(file_name)
    if uploaded:
        return post

    return False


def get_post_to_send():
    posts = []
    while not len(posts):
        posts = get_new_posts(config[posts_to_get_every_time])

        if not len(posts):
            lprint('no posts to send!')
            utils.sleep_until(60 * config[no_posts_wait_time])

            reload_config()

    return posts[0]


def send_a_gif():
    used_posts = utils.load_json(used_posts_path, [])

    while True:
        post = get_post_to_send()
        sent = send_to_telegram(post)

        used_posts.append({'id': post.id, 'send_time': int(datetime.now().timestamp())})
        utils.save_json(used_posts_path, used_posts)

        if sent:
            break

        seconds = 60
        print(
            '{}: failed to send post {}, sleeping {} seconds...'.format(
                utils.beautiful_now(), post.id, seconds
            )
        )
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

        sleep_time = 60 * random.randint(config[wait_from], config[wait_to])
        now = datetime.now()
        until = datetime.fromtimestamp(int(now.timestamp()) + sleep_time)
        print(
            '{}: sleeping for {} seconds until {}'.format(
                utils.beautiful_date(now), sleep_time, utils.beautiful_date(until)
            )
        )
        time.sleep(sleep_time)

        reload_config()


if __name__ == '__main__':
    main()
