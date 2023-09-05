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
        cmd = ["cargo", "-cat"]
        await self.execute(cmd)

    async def encode_h265(self
               , src: Union[str, PathLike]
               , dest: Union[str, PathLike]):
        await self.encode(src, dest, VideoFormat.H265)

    async def execute(self, cmd: list):
        async def log_stderr():
            async for line in reader:
                self.logger.debug("%s: %s", cmd[0], line.decode().rstrip())

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


