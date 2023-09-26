import asyncio
import signal
import argparse
import logging
from pathlib import Path

from .kat import (
    TMP_DIR_NAME,
    rename_service,
    mv_service,
    encode_service,
)


def _parse_option() -> 'argparse.Namespace':
    shared_parser = argparse.ArgumentParser(prog="kat"
                                            , description="Kat utilites"
                                            , add_help=False)
    shared_parser.add_argument("-i", "--input"
                               , required=True
                               , type=str
                               , help="Media path")
    shared_parser.add_argument("-o", "--out"
                               , required=True
                               , type=str
                               , help="Path to write")
    shared_parser.add_argument("-v", "--verbose"
                               , action="store_true")

    parser_2 = argparse.ArgumentParser()
    command = parser_2.add_subparsers(help="command", dest="command")

    encode_parser = command.add_parser("encode",
                                          aliases=["en"],
                                          parents=[shared_parser],
                                          help="Encoding media service")
    encode_parser.add_argument("-r", "--recursive"
                               , action="store_true"
                               , help="Recursive scan the input path")
    encode_parser.add_argument("--max"
                               , type=int
                               , default=4
                               , help="Maximum number of encoding")

    rename_parser = command.add_parser("rename",
                                          aliases=["rn"],
                                          parents=[shared_parser],
                                          help="Rename media to standard KAT code")
    rename_parser.add_argument("--prefix", type=str, help="Prefix for file", default="")
    rename_parser.add_argument("--suffix", type=str, help="Suffix for file", default="")

    _ = command.add_parser("move",
                                  aliases=["mv"],
                                  parents=[shared_parser],
                                  help="Move to media folder")
    return parser_2.parse_args()


def main():
    logging.basicConfig(format="%(asctime)s [%(levelname)7s]  %(message)s"
                        , datefmt="%Y-%m-%d %H:%M:%S")

    args = _parse_option()
    verbose = args.verbose
    cmd = args.command

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    exist_code = 0
    if cmd in ("rename", "rn"):
        rename_service(args)

    elif cmd in ("move", "mv"):
        mv_service(args)

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

