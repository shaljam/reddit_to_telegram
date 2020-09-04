import re
import subprocess
import traceback
import json
from pathlib import Path

from utils import lprint

IMAGE_EXTS = set(['jpg', 'jpeg', 'png', 'bmp', 'tif'])


def run_command(cmd):
    cp = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lprint(f'ran command {cmd} with resut:\n{cp}')
    return cp.returncode, cp.stdout.decode()


def is_file_image(path):
    path = Path(path)
    suffix = path.suffix[1:].lower()
    return suffix in IMAGE_EXTS


def get_video_info(path):
    cmd = f'ffprobe -v quiet -print_format json -show_streams -show_format "{path}"'
    return_code, output = run_command(cmd)
    if return_code != 0:
        lprint(f"ffprobe command {cmd} failed with return code {return_code}")

    output = json.loads(output)
    video_streams = [x for x in output["streams"] if x["codec_type"] == "video"]
    audio_streams = [x for x in output["streams"] if x["codec_type"] == "audio"]
    stream = video_streams[0]

    return (stream["width"], stream["height"], bool(len(audio_streams) > 0))


def scale_video(input_path, output_path, max_size):
    width, height, has_audio = get_video_info(input_path)

    if width < max_size and height < max_size:
        w = width
        h = -2
    else:
        if width >= height:
            w = max_size
            h = -2
        else:
            w = -2
            h = max_size

    scale = f"scale={w}:{h}"
    pix_fmt = "-pix_fmt yuv420p"

    video_filters = f'-filter:v "{scale}" {pix_fmt} '

    cmd = (
        f"ffmpeg "
        f'-i "{input_path}" '
        f"-vsync cfr -movflags +faststart {video_filters} "
        f'-strict -2 "{output_path}"'
    )

    return_code, _ = run_command(cmd)
    return return_code == 0, has_audio


if __name__ == "__main__":
    path = '/home/ali/projects/reddit_to_telegram/downloaded_videos/axgthfz5c1l51-axgthfz5c1l51.mp4'
    cmd = f'ffprobe -v quiet -print_format json -show_streams -show_format "{path}"'
    run_command(cmd)
