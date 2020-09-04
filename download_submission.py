import utils
import praw
import requests
import traceback
import os
from datetime import datetime
from ffmpeg_util import scale_video
import youtube_dl
from youtube_dl.utils import YoutubeDLError


accepted_content_types = ['image/gif', 'video/mp4']


def download_file(post):
    post_id = post['id']

    candidate_urls = post['candidate_urls']

    while len(candidate_urls):
        selected_url = candidate_urls[0]

        candidate_urls.remove(selected_url)

        url = selected_url['url']

        # download
        response = requests.get(url, stream=True)
        if not (
            response.status_code == 200
            and response.headers['content-type'] in accepted_content_types
        ):
            print('{}: failed to download {}'.format(utils.beautiful_now(), url))
            continue

        file_name = 'downloaded_videos/{}-{}'.format(
            post_id, int(datetime.now().timestamp() * 1e3)
        )
        print(
            '{}: downloading {} to {}...'.format(utils.beautiful_now(), url, file_name)
        )

        with open(file_name, 'wb') as fo:
            for chunk in response.iter_content(128):
                fo.write(chunk)

        scaled_path = '{}-scaled.mp4'.format(file_name)
        scaled = scale_video(file_name, scaled_path, 360)

        if scaled:
            print(
                '{}: scaled {} to {}'.format(
                    utils.beautiful_now(),
                    post_id,
                    os.path.getsize(file_name),
                    os.path.getsize(scaled_path),
                )
            )


def download_sub_with_id(submission_id):
    reddit = praw.Reddit(
        client_id='5HcYHPhZFHR14Q',
        client_secret='1RVyYaa-0it7zu2hCI2JVo80tuw',
        user_agent='telegram-poster',
    )

    submission = reddit.submission(id=submission_id)

    caption = '❄     {}\n🙋     {}\n\n{}'.format(
        submission.title, submission.author.name, submission.shortlink
    )

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
                {
                    'url': submission.media['reddit_video']['scrubber_media_url'],
                    'width': 200,
                    'height': 200,
                }
            )

        except KeyError:
            pass

        try:
            candidate_urls.append(
                {
                    'url': submission.media['oembed']['thumbnail_url'],
                    'width': 200,
                    'height': 200,
                }
            )

        except KeyError:
            pass

    if not len(candidate_urls):
        return

    dim = 'width'
    if candidate_urls[0]['height'] > candidate_urls[0]['width']:
        dim = 'height'

    candidate_urls.sort(key=lambda x: x[dim], reverse=True)

    post = {
        'id': submission.name,
        'process_time': int(datetime.now().timestamp()),
        'caption': caption,
        'candidate_urls': candidate_urls,
    }

    download_file(post)


# Mon Mar 19 2018 15:52:54 Tehran: sending t3_85hkgf to telegram channel...
# Mon Mar 19 2018 15:52:54 Tehran: failed to send post t3_85hkgf, sleeping 60 seconds...
# Mon Mar 19 2018 15:53:54 Tehran: sending t3_85egjo to telegram channel...
# Mon Mar 19 2018 15:53:55 Tehran: failed to send post t3_85egjo, sleeping 60 seconds...
# Mon Mar 19 2018 15:54:55 Tehran: sending t3_85evtf to telegram channel...
# Mon Mar 19 2018 15:54:55 Tehran: failed to send post t3_85evtf, sleeping 60 seconds...


def download_with_ytdl(submission_id):
    reddit = praw.Reddit(
        client_id='5HcYHPhZFHR14Q',
        client_secret='1RVyYaa-0it7zu2hCI2JVo80tuw',
        user_agent='telegram-poster',
    )

    post = reddit.submission(id=submission_id)
    post_id = post.id
    post_title = post.title

    # file_name = None

    # def my_hook(d):
    #     nonlocal file_name
    #     print(f'\nmy_hook {d}')
    #     if d['status'] == 'finished':
    #         print('{}: {} done downloading {} with youtube-dl'.format(utils.beautiful_now(), post_id, url))

    #         if 'filename' in d.keys():
    #             file_name = d['filename']

    ydl_opts = {
        'outtmpl': f'downloaded_videos/{youtube_dl.DEFAULT_OUTTMPL}',
        # 'progress_hooks': [my_hook]
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
                    utils.beautiful_now(), post_id, url, info
                )
            )
        except YoutubeDLError:
            print(
                '{}: {} {} youtube-dl failed with exception.\n{}'.format(
                    utils.beautiful_now(), post_id, url, traceback.format_exc()
                )
            )
            return False

    if not file_name:
        print(
            '{}: {} {} youtube-dl no filename!'.format(
                utils.beautiful_now(), post_id, url
            )
        )
        return False

    # file_name = 'downloaded_videos/axgthfz5c1l51-axgthfz5c1l51.mp4'
    print(f'file_name: {file_name}')

    scaled_path = '{}-scaled.mp4'.format(file_name)
    scaled = scale_video(file_name, scaled_path, 360)

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


if __name__ == "__main__":
    download_with_ytdl('imi8az')
