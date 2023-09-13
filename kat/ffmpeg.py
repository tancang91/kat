import asyncio.subprocess as sp
import asyncio
import json
from os import PathLike
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from typing import Union
import logging
import re
from tqdm import tqdm


class VideoFormat(Enum):
    H264 = 1
    H265 = 2


@dataclass
class MediaInfo:
    path: str
    format_name: str
    size: int
    bitrate: int
    duration: int
    _name: Optional[str] = None

    def __repr__(self) -> str:
        if self.size > 1024 ** 3:
            size_str = str(self.size_gb()) + " gb"
        elif self.size > 1024 ** 2:
            size_str = str(self.size_mb()) + " mb"
        else:
            size_str = str(self.size_kb()) + " kb"

        return "MediaInfo:\n" + \
                f"    Path: {self.path}\n"  + \
                f"    Size: {size_str}\n"  + \
                f"    Bitrate: {self.bitrate // 1000} kb/s\n"  + \
                f"    Duration: {self.duration_str()}"

    def size_kb(self) -> float:
        return round(self.size / 1024, 2)

    def size_mb(self) -> float:
        return round(self.size / (1024 ** 2), 2)

    def size_gb(self) -> float:
        return round(self.size / (1024 ** 3), 2)

    def duration_str(self) -> str:
        hour = self.duration // 3600
        min = (self.duration % 3600 ) // 60
        sec = self.duration % 60

        return "{0:02}:{1:02}:{2:02}".format(hour, min, sec)

    @property
    def name(self) -> str:
        if self._name is None:
            self._name = Path(self.path).name
        return self._name

class Encoder:
    _PROGRESS_RX = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.\d{2}")
    _SPEED_RX = re.compile(r"speed=(.*)x")
    _BITRATE_RX = re.compile(r"bitrate=(.*)kbits/s")

    def __init__(self):
        self.logger = logging.getLogger("Encoder")
        self.pbar = None
        self.media_info = None

    @staticmethod
    def _seconds(hours, minutes, seconds):
        return (int(hours) * 60 + int(minutes)) * 60 + int(seconds)

    async def encode(self
               , src: Union[str, PathLike]
               , dest: Union[str, PathLike]
               , format: VideoFormat):

        if not Path(src).is_file():
            raise FileNotFoundError(f"ERROR: Source {src} not found!!")

        if Path(dest).is_file():
            Path(dest).unlink()

        if format == VideoFormat.H265:
            codec = "hevc_nvenc"
        else:
            codec = "h264_nvenc"

        if self.media_info is None:
            media_info = await self.get_media_info(src)
            if media_info is None:
                raise OSError(f"ERROR: Cannot get media info of {media_info}")

            self.media_info = media_info

        self.logger.debug(f"Converting to format {format}")
        print(self.media_info)

        cmd = ["ffmpeg",
               "-hwaccel", "cuda",
               "-nostdin",
               "-i", src,
               "-c:v", codec,
               "-b:v", "3M",
               "-maxrate:v", "4M",
               "-bufsize:v", "8M",
               "-preset", "slow",
               "-c:a", "copy",
               dest]

        await self.subprocess_exec(cmd)

    async def encode_h265(self
               , src: Union[str, PathLike]
               , dest: Union[str, PathLike]):
        await self.encode(src, dest, VideoFormat.H265)

    async def get_media_info(self, media_path: Union[str, PathLike]):
        cmd = ["ffprobe", "-v", "quiet",
               "-print_format", "json",
               "-show_format", media_path]

        stdout, _, returncode = await self.subprocess_exec(cmd)

        if returncode == 0:
            json_str = json.loads(stdout.decode())
            path = json_str["format"]["filename"]
            duration = round(float(json_str["format"]["duration"]))
            format_name = json_str["format"]["format_name"]
            bitrate = int(json_str["format"]["bit_rate"])
            size = int(json_str["format"]["size"])

            return MediaInfo(path, format_name, size, bitrate, duration)

        return None

    async def subprocess_exec(self, cmd: list):
        async def log_stderr():
            duration = self.media_info.duration if self.media_info else 0

            while True:
                chunk = await reader.read(1024)
                if not chunk:
                    break
                chunk = chunk.decode()
                while True:
                    if len(chunk) > 0:
                        if "\r" in chunk:
                            (before, _, chunk) = chunk.partition("\r")
                            msg = "{0}: {1}%\r".format(cmd[0], before.rstrip())
                            self.progress(duration, before)
                        else:
                            (before, _, chunk) = chunk.partition("\n")
                            msg = "{0}: {1}".format(cmd[0], before.rstrip())
                            self.logger.debug(msg)
                    else:
                        break

            if self.pbar:
                self.pbar.update(duration - self.pbar.n)

        loop = asyncio.get_event_loop()

        reader = asyncio.StreamReader(loop=loop)
        transport, protocol = await loop.subprocess_exec(
            lambda: FFmpegProtocol(reader, limit=2**16, loop=loop),
            *cmd,
            stdout=sp.PIPE, stderr=sp.PIPE,
        )

        proc = asyncio.subprocess.Process(transport, protocol, loop)
        (stdout, stder), _ = await asyncio.gather(proc.communicate(), log_stderr())
        return (stdout, stder, proc.returncode)

    def progress(self, total: int, line: str):
        progress_search = self._PROGRESS_RX.search(line)
        bitrate_search = self._BITRATE_RX.search(line)
        bitrate = bitrate_search[1] if bitrate_search is not None else -1

        if progress_search is not None:
            current = self._seconds(*progress_search.groups())
            stats = "{0} kb/s".format(bitrate)

            if self.pbar is None:
                desc = "Encoding " + (self.media_info.name if self.media_info and self.media_info.name else "N/A")
                unit = " secs"
                self.pbar = tqdm(
                    desc=desc,
                    total=total,
                    dynamic_ncols=True,
                    unit=unit,
                    ncols=0,
                    colour="green",
                )
            self.pbar.set_postfix_str(stats)
            self.pbar.update(current - self.pbar.n)


class FFmpegProtocol(asyncio.subprocess.SubprocessStreamProtocol):
    def __init__(self, reader, limit, loop):
        super().__init__(limit=limit, loop=loop)
        self._reader = reader

    def pipe_data_received(self, fd, data):
        """Called when the child process writes data into its stdout
        or stderr pipe.
        """
        super().pipe_data_received(fd, data)
        if fd == 2:
            self._reader.feed_data(data)

    def pipe_connection_lost(self, fd, exc):
        """Called when one of the pipes communicating with the child
        process is closed.
        """
        super().pipe_connection_lost(fd, exc)
        if fd == 2:
            if exc:
                self._reader.set_exception(exc)
            else:
                self._reader.feed_eof()

