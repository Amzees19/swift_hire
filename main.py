"""
Entry point to run the background worker.
"""
import asyncio

from worker.main import main as worker_main


if __name__ == "__main__":
    asyncio.run(worker_main())

