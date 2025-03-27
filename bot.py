#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import io
import os

import aiohttp
import websockets
from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import (
    EndFrame,
    Frame,
    InputAudioRawFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments
from pydub import AudioSegment

load_dotenv(override=True)


class AudioProcessor(FrameProcessor):
    def __init__(self, websocket_url):
        super().__init__()
        self.audio_buffer = []
        self.sample_rate = None
        self.num_channels = None
        self.websocket = None
        self.websocket_url = websocket_url

    async def connect_websocket(self):
        self.websocket = await websockets.connect(self.websocket_url)

    async def __aenter__(self):
        await super().__aenter__()
        # Connect to WebSocket server when processor starts
        await self.connect_websocket()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.websocket:
            await self.websocket.close()
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            # Store frame audio and metadata
            self.audio_buffer.append(frame.audio)
            self.sample_rate = frame.sample_rate
            self.num_channels = frame.num_channels

            # Once we have 100 frames, combine and output
            # TODO: Separate audio using VAD frames instead
            if len(self.audio_buffer) >= 100:
                combined_audio = b"".join(self.audio_buffer)
                # Convert raw audio to AudioSegment
                audio_segment = AudioSegment(
                    data=combined_audio,
                    sample_width=2,  # 16-bit audio
                    frame_rate=self.sample_rate,
                    channels=self.num_channels,
                )

                # Export as AAC
                output_buffer = io.BytesIO()
                audio_segment.export(
                    output_buffer, format="adts"
                )  # adts is the container format for AAC
                aac_audio = output_buffer.getvalue()
                logger.info("Collected AAC audio to output")
                # Send AAC audio through WebSocket if connected
                if not self.websocket:
                    try:
                        await self.connect_websocket()
                    except (
                        websockets.exceptions.WebSocketException,
                        ConnectionRefusedError,
                    ) as e:
                        logger.error(f"Failed to connect to WebSocket server: {e}")
                if self.websocket:
                    logger.info(
                        f"Trying to send AAC audio to websocket: {self.websocket}"
                    )
                    try:
                        await self.websocket.send(aac_audio)
                    except websockets.exceptions.WebSocketException as e:
                        logger.error(f"WebSocket error: {e}")
                        # Attempt to reconnect
                        try:
                            await self.connect_websocket()
                        except (
                            websockets.exceptions.WebSocketException,
                            ConnectionRefusedError,
                        ) as e:
                            logger.error(
                                f"Failed to reconnect to WebSocket server: {e}"
                            )

                # Clear buffer after sending
                self.audio_buffer = []
        else:
            await self.push_frame(frame)


async def main(args):
    logger.info(f"Starting bot session with args: {args}")
    async with aiohttp.ClientSession() as session:
        # (room_url, token) = await configure(session)

        daily_transport = DailyTransport(
            args.body["daily_room_url"],
            # TODO: Token should be optional
            None,
            "Chatbot",
            DailyParams(
                audio_out_enabled=True,
                audio_in_enabled=True,
                audio_in_sample_rate=16000,
                camera_out_enabled=False,
            ),
        )

        audio_processor = AudioProcessor(args.body["websocket_url"])

        # the websocket transport input is what runs the server
        pipeline = Pipeline(
            [
                daily_transport.input(),
                audio_processor,
            ]
        )

        task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

        @daily_transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            print(f"Participant left: {participant}")
            await task.queue_frame(EndFrame())

        runner = PipelineRunner()

        await runner.run(task)


async def bot(args: DailySessionArguments):
    """Main bot entry point compatible with the FastAPI route handler.

    Args:
        config: The configuration object from the request body
        room_url: The Daily room URL
        token: The Daily room token
        session_id: The session ID for logging
        session_logger: The session-specific logger
    """
    logger.info(f"Bot process initialized. args: {args}")

    try:
        await main(args)
        logger.info("Bot process completed")
    except Exception as e:
        logger.exception(f"Error in bot process: {str(e)}")
        raise


###########################
# for local test run only #
###########################
LOCAL_RUN = os.getenv("LOCAL_RUN")
if LOCAL_RUN:
    import asyncio


async def local_main():
    # (room_url, token) = await configure(session)
    room_url = os.getenv("DAILY_ROOM_URL")
    logger.warning("_")
    logger.warning("_")
    logger.warning(f"Talk to your voice agent here: {room_url}")
    logger.warning("_")
    logger.warning("_")
    args = DailySessionArguments(
        # ensure we're using the room name from the request body
        room_url=None,
        token=None,
        session_id=None,
        body={"websocket_url": os.getenv("WEBSOCKET_URL"), "daily_room_url": room_url},
    )
    # webbrowser.open(room_url)
    await main(args)


if LOCAL_RUN and __name__ == "__main__":
    asyncio.run(local_main())
