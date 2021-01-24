#!/usr/bin/env python3.8

import argparse
import json
import logging
import ssl
from . import HisenseTv


def main():
    parser = argparse.ArgumentParser(description="Hisense TV control.")
    parser.add_argument("hostname", type=str, help="Hostname or IP for the TV.")
    parser.add_argument(
        "--authorize",
        action="store_true",
        help="Authorize this API to access the TV.",
    )
    parser.add_argument(
        "--get",
        action="append",
        default=[],
        choices=["sources", "volume"],
        help="Gets a value from the TV.",
    )
    parser.add_argument(
        "--key",
        action="append",
        default=[],
        choices=[
            "power",
            "up",
            "down",
            "left",
            "right",
            "menu",
            "back",
            "exit",
            "ok",
            "volume_up",
            "volume_down",
            "channel_up",
            "channel_down",
            "fast_forward",
            "rewind",
            "stop",
            "play",
            "pause",
            "mute",
            "home",
            "subtitle",
            "netflix",
            "youtube",
            "amazon",
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "source_1",
            "source_2",
            "source_3",
            "source_4",
            "source_5",
            "source_6",
            "source_7",
        ],
        help="Sends a keypress to the TV.",
    )
    parser.add_argument(
        "--no-ssl",
        action="store_true",
        help="Do not connect with SSL (required for some models).",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Logging verbosity."
    )

    args = parser.parse_args()

    if args.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    root_logger = logging.getLogger()
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="[{asctime}] [{levelname:<8}] {message}", style="{"
    )
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(level)
    logger = logging.getLogger(__name__)

    if args.no_ssl:
        ssl_context = None
    else:
        ssl_context = ssl._create_unverified_context()

    tv = HisenseTv(
        args.hostname, enable_client_logger=args.verbose >= 2, ssl_context=ssl_context
    )
    with tv:
        if args.authorize:
            tv.start_authorization()
            code = input("Please enter the 4-digit code: ")
            tv.send_authorization_code(code)

        for key in args.key:
            func = getattr(tv, f"send_key_{key}")
            logger.info(f"sending keypress: {key}")
            func()

        for getter in args.get:
            func = getattr(tv, f"get_{getter}")
            output = func()
            if isinstance(output, dict) or isinstance(output, list):
                output = json.dumps(output, indent=4)
            logger.info(f"{getter}: {output}")


if __name__ == "__main__":
    main()
