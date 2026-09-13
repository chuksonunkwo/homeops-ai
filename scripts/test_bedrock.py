from __future__ import annotations

import json
import sys

from app.bedrock import BedrockCommercialReviewer


def main() -> int:
    reviewer = BedrockCommercialReviewer()
    result = reviewer.test_connection()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
