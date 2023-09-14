import asyncio
import re
import logging
from pathlib import Path
import argparse
from typing import Union
import sys
import signal
from typing import Tuple, List

from .utils import Color
from .ffmpeg import Encoder

PATTERN = r"(?:|.*\W+)([A-Z]+-[0-9]+)\W*"
THRESHOLD_FILE_SIZE_BYTES = 3 * (1024 ** 3)
TMP_DIR_NAME = "_tmp"


def extract_code(pattern, s: str) -> Union[None, str]:
    g = pattern.match(s)
    if g is not None:
        return g.group(1)
    return None

async def encode_service(args):
    src = Path(args.input)
    dest = Path(args.out)
    recursive = args.recursive
    limit = args.max

    pairs: List[Tuple] = []

    if not recursive:
        if dest.is_dir():
            raise ValueError(f"ERROR: Output {dest} folder not allowed in non-recursive mode!!")
        pairs.append((src, dest))
        temp_dir_path = dest.parent / TMP_DIR_NAME

    else:
        if not src.is_dir():
            raise ValueError(f"ERROR: Input {src} must be folder in recursive mode!!")
        elif not dest.is_dir():
            raise ValueError(f"ERROR: Output {dest} must be folder in recursive mode!!")

        logging.info(f"Start scanning...")
        pat = re.compile(PATTERN)
        for spath in src.glob("**/*.raw"):
            code = extract_code(pat, spath.name)
            if code is None:
                continue

            dest_path = dest / (code + ".mp4")
            pairs.append((spath, dest_path))
            logging.debug(f"Source: {spath}, Dest: {dest_path}")

        temp_dir_path = dest / TMP_DIR_NAME

    if not temp_dir_path.is_dir():
        temp_dir_path.mkdir()

    encoder = Encoder()
    for (s, d) in pairs:
        if limit <= 0:
            break
        temp_proc_path = temp_dir_path / d.name
        if d.is_file():
            yes = str(input(f"{d} already exist!!\nWould you like to overwrite it [y/N]: "))
            if not yes.strip() in ("y", "Y"):
                continue
        await encoder.encode_h265(s, temp_proc_path)
        temp_proc_path.rename(d)
        limit -= 1

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


def main():
    shared_parser = argparse.ArgumentParser(prog="kat", description="Kat utilites", add_help=False)
    shared_parser.add_argument("-i", "--input", required=True, type=str, help="Media path")
    shared_parser.add_argument("-o", "--out", required=True, type=str, help="Path to write")
    shared_parser.add_argument("-v", "--verbose", action="store_true")

    parser_2 = argparse.ArgumentParser()
    command = parser_2.add_subparsers(help="command", dest="command")

    encode_parser = command.add_parser("encode",
                                          aliases=["en"],
                                          parents=[shared_parser],
                                          help="Encoding media service")
    encode_parser.add_argument("-r", "--recursive", action="store_true", help="Recursive scan the input path")
    encode_parser.add_argument("--max", type=int, help="Maximum number of encoding", default=4)

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

    exist_code = 0
    if cmd in ("rename", "rn"):
        rename_service(args)

    elif cmd in ("encode", "en"):
        try:
            asyncio.run(encode_service(args))
            exist_code = 0
        except KeyboardInterrupt:
            print("Received KeyboardInterrupt")
            exist_code = signal.SIGINT + 128
        except Exception as e:
            print(e)
            exist_code = 1
        finally:
            print("Cleaning up...")
            dest = Path(args.out)
            temp_dir_path = None
            if args.recursive and dest.is_dir():
                temp_dir_path = dest / TMP_DIR_NAME
            elif not args.recursive:
                temp_dir_path = dest.parent / TMP_DIR_NAME

            if temp_dir_path is not None and temp_dir_path.is_dir():
                for f in temp_dir_path.glob("*.mp4"):
                    logging.debug(f"Remove: {f}")
                    f.unlink()

                if not any(temp_dir_path.iterdir()):
                    logging.debug(f"Remove temp folder: {temp_dir_path}")
                    temp_dir_path.rmdir()

            logging.debug("Cleaning up....")

    return exist_code

if __name__ == "__main__":
    sys.exit(main())

