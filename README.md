# Media Extraction Pipeline

This repo demonstrates extracting audio from a Daily room and forwarding it to a websocket client.

To set up the bot:

```bash
cp env.example .env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You'll also need `ffmpeg` installed, and possibly some other dependencies for Windows systems.

Then, edit .env and add your Daily API key. This enables the demo to create a room token for you, which isn't strictly necessary for now, but is useful if you want to enable transcription, for example. Go ahead and set DAILY_ROOM_URL to one of your test rooms.

To run the demo locally, you'll need two terminal tabs:

```bash
# for the bot
$ source venv/bin/activate
$ python bot.py
```

```bash
# for the websocket
$ source venv/bin/activate
$ python websocket_server.py
```

Then, open a browser to your test room and start talking. You'll see an AAC file created in the `output` directory with the recording.

## Deploying to Pipecat Cloud

First, you'll need to expose your test websocket server to the internet. Using a reserved hostname on ngrok makes that a bit easier:

```bash
ngrok http --hostname yourdomain.ngrok.app 8765 # if you have a reserved hostname
ngrok http 8765 # to get a randomly assigned hostname
```

Then deploy your bot to Pipecat Cloud:

```bash
docker build --platform linux/arm64 -t media-extraction:latest .
docker tag media-extraction:latest your_dockerhub_username/media-extraction:0.1
docker push your_dockerhub_username/media-extraction:0.1
pcc auth login
pcc deploy media-extraction your_dockerhub_username/media-extraction:0.1
```


Then, start your bot with the Daily room and websocket URL in the POST request body:

```bash
curl --request POST \
  --url https://api.pipecat.daily.co/v1/public/media-extraction/start \
  --header 'Authorization: Bearer YOUR_PCC_API_TOKEN_HERE' \
  --header 'Content-Type: application/json' \
  --data '{
  "createDailyRoom": false,
  "body": {
    "daily_room_url": "https://yourdomain.daily.co/yourroom",
	"websocket_url": "wss://yourdomain.ngrok.app"
  }
}'
