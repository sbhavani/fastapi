"""Example of using Server-Sent Events (SSE) with FastAPI."""

import asyncio
from fastapi import FastAPI
from fastapi.responses import SSEResponse, SSEEvent, sse_event

app = FastAPI()


@app.get("/events")
async def main():
    """Simple SSE endpoint that sends events."""

    async def event_generator():
        for i in range(5):
            # Using sse_event helper
            yield sse_event(data=f"Event {i}")
            await asyncio.sleep(1)

    return SSEResponse(event_generator())


@app.get("/events-json")
async def events_json():
    """SSE endpoint with JSON data."""

    async def event_generator():
        for i in range(5):
            # Auto JSON encoding for dict data
            yield sse_event(data={"message": f"Event {i}", "id": i})
            await asyncio.sleep(1)

    return SSEResponse(event_generator())


@app.get("/events-types")
async def events_with_types():
    """SSE endpoint with event types."""

    async def event_generator():
        yield sse_event(data="Process started", event="info")
        await asyncio.sleep(1)
        yield sse_event(data="Step 1 complete", event="progress")
        await asyncio.sleep(1)
        yield sse_event(data="All done!", event="complete")

    return SSEResponse(event_generator())


@app.get("/events-retry")
async def events_with_retry():
    """SSE endpoint with retry configuration."""

    async def event_generator():
        # Set retry to 5 seconds
        yield sse_event(data="Connected", retry=5000)
        for i in range(10):
            yield sse_event(data=f"Update {i}")
            await asyncio.sleep(1)

    return SSEResponse(event_generator())


@app.get("/events-ids")
async def events_with_ids():
    """SSE endpoint with event IDs for reconnection."""

    async def event_generator():
        for i in range(100):
            # Include ID for client reconnection
            yield sse_event(data=f"Event {i}", id=i)
            await asyncio.sleep(1)

    return SSEResponse(event_generator())


@app.get("/events-dataclass")
async def events_with_dataclass():
    """SSE endpoint using SSEEvent dataclass."""

    async def event_generator():
        # Using SSEEvent dataclass
        event1 = SSEEvent(data="Hello", event="greeting")
        event2 = SSEEvent(data={"status": "ok"}, event="status")
        yield str(event1)
        yield str(event2)

    return SSEResponse(event_generator())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
