# VideoEncoder - a telegram bot for compressing/encoding videos in h264 format.
# Copyright (c) 2021 WeebTime/VideoEncoder
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import os
import subprocess
import time

from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

import ffmpeg

from .. import audio
from .. import crf as c
from .. import encode_dir
from .. import preset as p
from .. import resolution as r
from .. import tune as t


def get_codec(filepath, channel='v:0'):
    output = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', channel,
                                      '-show_entries', 'stream=codec_name,codec_tag_string', '-of',
                                      'default=nokey=1:noprint_wrappers=1', filepath])
    return output.decode('utf-8').split()


async def encode(filepath):
    path, extension = os.path.splitext(filepath)
    name = path.split('/')
    output_filepath = encode_dir + name[len(name)-1] + '.mp4'
    assert(output_filepath != filepath)

    if os.path.isfile(output_filepath):
        print(f'[Encode] [Warning]: "{output_filepath}": file already exists')
    else:
        print('[Encode]: ' + filepath)

    # Codec and Bits
    codec = '-c:v libx264 -x264-params psnr=0:ssim=0:cabac=1:rc-lookahead=250:bframes=16:b-bias=0:b-adapt=2:b-pyramid=1:ref=16:mixed-refs=1:deblock=-3,-3:ipratio=1.3:pbratio=1.2:keyint=250:open_gop=0:qpmin=18:qpmax=69:qpstep=4:aq-mode=3:aq-strength=0.8:weightb=1:weightp=2:analyse=0x3,0x133:me=umh:subme=11:psy=1:merange=48:mvrange=511:subq=9:8x8dct=1:trellis=2:no-fast-pskip=1:chroma-qp-offset=-2:direct=auto:partitions=all:scenecut=40:cplxblur=20:qblur=0.5:psy-rd=0.9,0.2:no-mbtree=0:constrained-intra=1:qcomp=0.8:direct=auto:no-dct-decimate=1:nr=20:threads=12:crf_max=51 -pix_fmt yuv420p'

    # CRF
    crf = f'-crf {c}'

    # Preset
    if p == 'uf':
        preset = '-preset ultrafast'
    elif p == 'sf':
        preset = '-preset superfast'
    elif p == 'vf':
        preset = '-preset veryfast'
    elif p == 'f':
        preset = '-preset fast'
    elif p == 'm':
        preset = '-preset medium'

    # Optional
    video_opts = f'-tune {t} -map 0:v? -map_chapters 0 -map_metadata 0'

    # Copy Subtitles
    subs_i = get_codec(filepath, channel='s:0')
    if subs_i == []:
        subtitles = ''
    else:
        subtitles = '-c:s copy -map 0:s?'

    # Audio
    a_i = get_codec(filepath, channel='a:0')
    a = audio
    if a_i == []:
        audio_opts = ''
    else:
        audio_opts = '-map 0:a?'
        if a == 'aac':
            audio_opts += ' -c:a libfdk_aac -b:a 32k -vbr 2 -profile:a aac_he_v2 -ac 2 -ar 44100'
        elif a == 'opus':
            audio_opts += ' -c:a libopus -vbr on -b:a 96k'
        elif a == 'copy':
            audio_opts += ' -c:a copy'

    # Resolution
    if r == 'Source':
        resolution = ''
    elif r == '1080':
        resolution = '-vf scale=1920:-2'
    elif r == '720':
        resolution = '-vf scale=1280:-2'
    elif r == '480':
        resolution = '-vf scale=720:-2'
    elif r == '360':
        resolution = '-vf scale=360:-2'
    else:
        resolution = ''

    finish = '-threads 2 -movflags +faststart'

    # Finally
    command = ['ffmpeg', '-y', '-analyzeduration', '500M', '-probesize', '500M', '-i', filepath]
    command.extend((codec.split() + video_opts.split() +
                   crf.split() + resolution.split() + subtitles.split() + audio_opts.split() + finish.split()))
    proc = await asyncio.create_subprocess_exec(*command, output_filepath, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await proc.communicate()
    return output_filepath


def get_thumbnail(in_filename, path, ttl):
    out_filename = os.path.join(path, str(time.time()) + ".jpg")
    open(out_filename, 'a').close()
    try:
        (
            ffmpeg
            .input(in_filename, ss=ttl)
            .output(out_filename, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return out_filename
    except ffmpeg.Error as e:
        return None


def get_duration(filepath):
    metadata = extractMetadata(createParser(filepath))
    if metadata.has("duration"):
        return metadata.get('duration').seconds
    else:
        return 0
