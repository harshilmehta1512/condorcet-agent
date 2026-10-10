"""T0/T1 smoke test: one tiny call per judge on TokenRouter. Uses event credits (~9 calls). Run only with the event key."""
import asyncio

from src import config
from src.llm_client import JudgeClient


async def main():
    client = JudgeClient("tokenrouter")
    prompt = 'Reply with JSON only: {"verdict": "SUPPORT"}'
    try:
        for name, model in config.JUDGES.items():
            try:
                text = await client._call(model, prompt)
                print(f"OK    {name:14s} {model:28s} -> {text.strip()[:60]!r}")
            except Exception as e:
                print(f"FAIL  {name:14s} {model:28s} -> {str(e)[:120]}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
