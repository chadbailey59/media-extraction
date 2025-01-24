#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import sys

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import (
    EndFrame,
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transports.network.websocket_server import (
    WebsocketServerParams,
    WebsocketServerTransport,
)
from pipecat.transports.services.daily import DailyParams, DailyTransport

from runner import configure

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


class AudioProcessor(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            await self.push_frame(
                OutputAudioRawFrame(
                    audio=frame.audio,
                    sample_rate=frame.sample_rate,
                    num_channels=frame.num_channels,
                )
            )
        else:
            await self.push_frame(frame)


async def main():
    async with aiohttp.ClientSession() as session:
        (room_url, token) = await configure(session)

        daily_transport = DailyTransport(
            room_url,
            token,
            "Chatbot",
            DailyParams(
                audio_out_enabled=True,
                audio_in_enabled=True,
                audio_in_sample_rate=16000,
                camera_out_enabled=False,
                transcription_enabled=True,
            ),
        )

        ws_transport = WebsocketServerTransport(
            params=WebsocketServerParams(
                audio_out_sample_rate=16000,
                audio_out_enabled=True,
                add_wav_header=True,
                session_timeout=60 * 3,  # 3 minutes
            )
        )

        audio_processor = AudioProcessor()

        # the websocket transport input is what runs the server
        pipeline = Pipeline(
            [ws_transport.input(), daily_transport.input(), audio_processor, ws_transport.output()]
        )

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

        @daily_transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            print(f"Participant left: {participant}")
            await task.queue_frame(EndFrame())

        runner = PipelineRunner()

        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
