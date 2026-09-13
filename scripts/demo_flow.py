from tempfile import TemporaryDirectory
from pathlib import Path

from app.engine import HomeOpsEngine
from app.store import Store


def main() -> None:
    with TemporaryDirectory() as tmp:
        engine = HomeOpsEngine(Store(Path(tmp) / "demo.db"))
        job = engine.create_service_request("My AC isn't cooling. Handle it.")
        print("JOB", job["id"])
        comparison = engine.compare_quotes(job["id"])
        print("RECOMMENDATION", comparison["recommended_provider"])
        engine.approve_provider(job["id"], "KlimaPro")
        engine.schedule_service(job["id"])
        engine.record_service_completion(job["id"])
        review = engine.submit_invoice(job["id"], 135, callout=45, service=50, materials=40)
        print("INVOICE_DECISION", review["decision"])
        print("VARIANCE", review["variance"])


if __name__ == "__main__":
    main()
