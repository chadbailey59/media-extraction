# Media Extraction Pipeline

This repo demonstrates extracting audio from a Daily room and forwarding it to a websocket client.

To set up the bot:

```
cp env.example .env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then, edit .env and add your Daily API key. This enables the demo to create a room token for you, which isn't strictly necessary for now, but is useful if you want to enable transcription, for example. Go ahead and set DAILY_SAMPLE_ROOM_URL to one of your test rooms.

To run the demo, you'll need two terminal tabs:

```
# for the bot
$ source venv/bin/activate
$ python bot.py
```

```
# host the HTML client page so the websocket can connect
$ source venv/bin/activate
$ python -m http.server
```

Then, open two browser windows: One to your Daily test room, and one to `http://localhost:8000`.

Once you've joined the test room and unmuted your mic, click the "Start Audio" button in the websocket client. If you talk into your mic, you should hear the audio played back from the websocket client tab.