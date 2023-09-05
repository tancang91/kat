from os import PathLike
from enum import Enum
import asyncio.subprocess as sp
import asyncio

from typing import Union

import logging


class VideoFormat(Enum):
    H264 = 1
    H265 = 2

class Encoder:
    def __init__(self):
        self.logger = logging.getLogger("Encoder")

    async def encode(self
               , src: Union[str, PathLike]
               , dest: Union[str, PathLike]
               , format: VideoFormat):

        if format == VideoFormat.H265:
            codec = "hevc_nvenc"
        else:
            codec = "h264_nvenc"

        cmd = ["ffmpeg", "-hwaccel", "cuda", "-nostdin",
               "-i", src,
               "-c:v", codec,
               "-b:v", "3M",
               "-maxrate:v", "4M",
               "-bufsize:v", "8M",
               "-preset", "slow",
               "-c:a", "copy", dest]
        await self.execute(cmd)

    async def encode_h265(self
               , src: Union[str, PathLike]
               , dest: Union[str, PathLike]):
        await self.encode(src, dest, VideoFormat.H265)

    async def execute(self, cmd: list):
        async def log_stderr():
            cnt = 10
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                chunk = chunk.decode()
                while True:
                    if len(chunk) > 0:
                        if "\r" in chunk:
                            (before, _, chunk) = chunk.partition("\r")
                            msg = "{0}: {1}%\r".format(cmd[0], before.rstrip())
                            cnt -= 1
                            if cnt <= 0:
                                self.logger.info(msg)
                                cnt = 10
                        else:
                            (before, _, chunk) = chunk.partition("\n")
                            msg = "{0}: {1}".format(cmd[0], before.rstrip())
                            self.logger.debug(msg)
                    else:
                        break

        loop = asyncio.get_event_loop()

        reader = asyncio.StreamReader(loop=loop)
        transport, protocol = await loop.subprocess_exec(
            lambda: FFmpegProtocol(reader, limit=2**16, loop=loop),
            *cmd,
            stdout=sp.PIPE, stderr=sp.PIPE,
        )

        proc = asyncio.subprocess.Process(transport, protocol, loop)
        (_, _), _ = await asyncio.gather(proc.communicate(), log_stderr())


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


