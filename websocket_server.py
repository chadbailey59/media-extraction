import asyncio
import websockets
import os
from datetime import datetime

async def save_audio_data(websocket):
    print("Client connected")
    try:
        # Create output directory if it doesn't exist
        os.makedirs("output", exist_ok=True)
        
        # Create a new file for this connection with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"output/audio_{timestamp}.aac"
        
        with open(output_file, "wb") as f:
            print(f"Saving audio to {output_file}")
            async for message in websocket:
                # Write the AAC audio data to file
                f.write(message)
                print(f"Received {len(message)} bytes of audio data")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Client disconnected")

async def main():
    async with websockets.serve(save_audio_data, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
