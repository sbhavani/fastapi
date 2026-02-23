from fastapi import FastAPI
from fastapi.responses import SSEResponse, SSEvent
import asyncio

app = FastAPI()


@app.get("/events", response_class=SSEResponse)
async def main():
    async def event_generator():
        for i in range(3):
            yield f"data: message {i}\n\n"
            await asyncio.sleep(0.1)

    return SSEResponse(event_generator())


@app.get("/events/with-event", response_class=SSEResponse)
async def main_with_event():
    async def event_generator():
        for i in range(3):
            yield SSEvent(data=f"message {i}", event="message")

    return SSEResponse(event_generator(), event="message")


@app.get("/events/with-retry", response_class=SSEResponse)
async def main_with_retry():
    async def event_generator():
        for i in range(3):
            yield SSEvent(data=f"message {i}", retry=5000)

    return SSEResponse(event_generator(), retry=5000)
