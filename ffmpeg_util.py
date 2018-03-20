import ffmpeg
import subprocess
import re


def scale_video(input_path, output_path, max_size):
    cmd = 'ffprobe -v quiet -show_streams {}'.format(input_path)
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

    if not result.stdout:
        return

    result = result.stdout.decode("utf-8")

    width = None
    height = None

    m = re.search(r'^width=(\d*)$', result, re.MULTILINE)
    if m:
        width = int(m.groups()[0])

    m = re.search(r'^height=(\d*)$', result, re.MULTILINE)
    if m:
        height = int(m.groups()[0])

    if not width or not height:
        return

    if width < max_size and height < max_size:
        w = width
        h = height
    else:
        if width >= height:
            w = max_size
            h = -2
        else:
            w = -2
            h = max_size

    out_config = {
        'c:v': 'libx264',
        'pix_fmt': 'yuv420p',
        'movflags': 'faststart'
    }

    stream = ffmpeg.input(input_path)
    stream = ffmpeg.filter_(stream, 'scale', width=w, height=h)
    stream = ffmpeg.output(stream, output_path, **out_config)
    ffmpeg.run(stream)

    return True
