import asyncio
import re
import logging
from pathlib import Path
import argparse
from typing import Union
import sys

from .utils import Color
from .ffmpeg import Encoder

PATTERN = r"(?:|.*\W+)([A-Z]+-[0-9]+)\W*"
THRESHOLD_FILE_SIZE_BYTES = 3 * (1024 ** 3)


def extract_code(pattern, s: str) -> Union[None, str]:
    g = pattern.match(s)
    if g is not None:
        return g.group(1)
    return None

async def encode_service(args):
    input = args.input
    out = args.out
    encoder = Encoder()
    await encoder.encode_h265(input, out)

def rename_service(args: argparse.Namespace):
    base_folder = args.input
    target_folder = args.out
    prefix = args.prefix
    suffix = args.suffix

    base_path = Path(base_folder)
    target_path = Path(target_folder)

    if not base_path.is_dir():
        raise OSError(f"ERROR: {base_folder} is not exist!")

    if not target_path.is_dir():
        raise OSError(f"ERROR: {target_folder} is not exist!")

    logging.debug(f"InputFolder: {base_path.absolute()}")
    logging.debug(f"OutFolder: {target_path.absolute()}")

    pattern = re.compile(PATTERN)

    for path in base_path.glob("**/*.mp4"):
        base_name = path.name
        ext = path.suffix

        if path.lstat().st_size < THRESHOLD_FILE_SIZE_BYTES:
            logging.warning(">>> {0} size less than threshold...{1}".format(str(path) ,Color.yellow("SKIPPING")))
            continue

        code = extract_code(pattern, base_name)

        if code is not None:
            dirname = target_path / code
            out = dirname / (prefix + code + ext + suffix)

            if not dirname.is_dir():
                dirname.mkdir()

            path.rename(out)
            logging.info(">>> [{2:<10}] '{0}' rename to {1}".format(str(path), out, Color.green("OK")))
        else:
            logging.warning(">>> '[{1:<10}] {0}' not matched".format(str(path), Color.yellow("SKIPPING")))

    logging.info("All done. Thanks for using my service")


if __name__ == "__main__":
    shared_parser = argparse.ArgumentParser(prog="kat", description="Kat utilites", add_help=False)
    shared_parser.add_argument("-i", "--input", required=True, type=str, help="Media path")
    shared_parser.add_argument("-o", "--out", required=True, type=str, help="Path to write")
    shared_parser.add_argument("-v", "--verbose", action="store_true", help="Path to write")

    parser_2 = argparse.ArgumentParser()
    command = parser_2.add_subparsers(help="command", dest="command")

    encode_parser = command.add_parser("encode",
                                          aliases=["en"],
                                          parents=[shared_parser],
                                          help="Encoding media service")

    rename_parser = command.add_parser("rename",
                                          aliases=["rn"],
                                          parents=[shared_parser],
                                          help="Rename media to standard KAT code")

    rename_parser.add_argument("--prefix", type=str, help="Prefix for file", default="")
    rename_parser.add_argument("--suffix", type=str, help="Suffix for file", default="")

    args = parser_2.parse_args()
    cmd = args.command
    verbose = args.verbose

    logging.basicConfig(format="%(asctime)s [%(levelname)7s]  %(message)s"
                        , datefmt="%Y-%m-%d %H:%M:%S")

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    if cmd in ("rename", "rn"):
        rename_service(args)
    elif cmd  in ("encode", "en"):
        try:
            asyncio.run(encode_service(args))
        except Exception as e:
            print(e)
            sys.exit(1)

