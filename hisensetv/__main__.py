import argparse
import logging
import json
from . import HisenseTv


def main():
    parser = argparse.ArgumentParser(description="Hisense TV control.")
    parser.add_argument("hostname", type=str, help="Hostname or IP for the TV.")
    parser.add_argument(
        "--authorize", action="store_true", help="Authorize this API to access the TV.",
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
        choices=["back", "down", "exit", "left", "menu", "power", "right", "up"],
        help="Sends a keypress to the TV.",
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

    tv = HisenseTv(args.hostname, enable_client_logger=args.verbose >= 2)
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
