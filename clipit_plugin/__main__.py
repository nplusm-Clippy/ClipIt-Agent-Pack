import argparse
import json
import sys

from .client import ClipItError, OPERATIONS
from .runtime import Runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description="Harness-independent ClipIt platform client. Credentials use the existing CLIPPER environment variables.")
    parser.add_argument("operation", choices=["status", "doctor", *sorted(OPERATIONS)])
    parser.add_argument("--id")
    parser.add_argument("--query", default="{}", help="JSON query object")
    parser.add_argument("--body", default="{}", help="JSON request object, or @- to read stdin; mutations need a stable idempotencyKey")
    args = parser.parse_args(argv)
    runtime = Runtime()
    try:
        if args.operation == "status":
            result = runtime.status()
        elif args.operation == "doctor":
            result = runtime.doctor()
        else:
            body = json.loads(sys.stdin.read(65537) if args.body == "@-" else args.body)
            result = runtime.call(args.operation, {"id": args.id, "query": json.loads(args.query), "body": body})
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ClipItError as exc:
        print(json.dumps(exc.public(), ensure_ascii=False))
        return 13 if exc.code == "OUTCOME_UNKNOWN" else 1
    except (ValueError, TypeError):
        print(json.dumps({"ok": False, "error": {"code": "INVALID_INPUT", "message": "Supply valid JSON objects."}}))
        return 2
    finally:
        runtime.close()


if __name__ == "__main__":
    sys.exit(main())
