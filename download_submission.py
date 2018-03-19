import utils
import praw
import requests
import os
from datetime import datetime
from ffmpeg_util import scale_video


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
        if not (response.status_code == 200 and response.headers['content-type'] in accepted_content_types):
            print('{}: failed to download {}'.format(utils.beautiful_now(), url))
            continue

        file_name = 'downloaded_videos/{}-{}'.format(post_id, int(datetime.now().timestamp() * 1e3))
        print('{}: downloading {} to {}...'.format(utils.beautiful_now(), url, file_name))

        with open(file_name, 'wb') as fo:
            for chunk in response.iter_content(128):
                fo.write(chunk)

        scaled_path = '{}-scaled.mp4'.format(file_name)
        scaled = scale_video(file_name, scaled_path, 360)

        if scaled:
            print('{}: scaled {} to {}'
                  .format(utils.beautiful_now(), post_id, os.path.getsize(file_name), os.path.getsize(scaled_path)))


def download_sub_with_id(submission_id):
    reddit = praw.Reddit(client_id='5HcYHPhZFHR14Q',
                         client_secret='1RVyYaa-0it7zu2hCI2JVo80tuw',
                         user_agent='telegram-poster')

    submission = reddit.submission(id=submission_id)

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
        return

    dim = 'width'
    if candidate_urls[0]['height'] > candidate_urls[0]['width']:
        dim = 'height'

    candidate_urls.sort(key=lambda x: x[dim], reverse=True)

    post = {
        'id': submission.name,
        'process_time': int(datetime.now().timestamp()),
        'caption': caption,
        'candidate_urls': candidate_urls
    }

    download_file(post)

# Mon Mar 19 2018 15:52:54 Tehran: sending t3_85hkgf to telegram channel...
# Mon Mar 19 2018 15:52:54 Tehran: failed to send post t3_85hkgf, sleeping 60 seconds...
# Mon Mar 19 2018 15:53:54 Tehran: sending t3_85egjo to telegram channel...
# Mon Mar 19 2018 15:53:55 Tehran: failed to send post t3_85egjo, sleeping 60 seconds...
# Mon Mar 19 2018 15:54:55 Tehran: sending t3_85evtf to telegram channel...
# Mon Mar 19 2018 15:54:55 Tehran: failed to send post t3_85evtf, sleeping 60 seconds...


# download_sub_with_id('85hkgf')
