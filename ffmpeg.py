from os import PathLike
from enum import Enum

from typing import Union

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(format="%(asctime)s [%(levelname)7s]  %(message)s"
                    , level=logging.DEBUG
                    , datefmt="%Y-%m-%d %H:%M:%S")

cmd = [
    "ffmpeg",
    "-h"
]

class VideoFormat(Enum):
    H264 = 1
    H265 = 2


class Encoder:
    def __init__(self):
        self.logger = logging.getLogger("Encoder")

    def encode(self
               , src: Union[str, PathLike[str]]
               , dest: Union[str, PathLike[str]]
               , format: VideoFormat):
        pass

    def encode_h265(self
               , src: Union[str, PathLike[str]]
               , dest: Union[str, PathLike[str]]):
        self.encode(src, dest, VideoFormat.H265)

'''
import asyncio.subprocess
import asyncio
import subprocess
import functools

class MyProtocol(asyncio.subprocess.SubprocessStreamProtocol):
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

async def main():

    loop = asyncio.get_event_loop()

    reader = asyncio.StreamReader(loop=loop)
    protocol_factory = functools.partial(
        MyProtocol, reader, limit=2**16, loop=loop
    )

    async def log_stderr():
        async for line in reader:
            logger.debug("%s: %s", cmd[0], line.decode().rstrip())

    transport, protocol = await loop.subprocess_exec(
        protocol_factory,
        *cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    proc = asyncio.subprocess.Process(transport, protocol, loop)
    (out, err), _ = await asyncio.gather(proc.communicate(), log_stderr())


asyncio.run(main())
'''

