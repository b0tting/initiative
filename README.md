# Initiative!
We like playing D20 based games - pathfinder, Dungeons and dragons 3rd edition, D&D Next, etcetera. A lot of time goes into combat and administrating combat. Who'se turn is it? But shouldn't Alice have gone first? 

These discussions take the speed out of the game, a problem this page tries to solve by delegating to players. All players can open the initiative app and allow the DM to delegate the calling of rounds and round based effect to the players. 

![Alt text](/static/css/images/screenshot.png?raw=true "App screeshot")

An example of play: 
- DM: "You step on a branch. The loud crack does not seem to surprise the orc, who had already nocked an arrow. He turns around to face you."
- DM: "Everybody, add your initiative. Alice, can you call off the rounds for me? Please add the orc with a +4 initative bonus. Also add a "surprise" effect that lasts three rounds and tell me when it hits zero"
- Alice adds her initiative, one for the orc and also adds an effect called "surprise" that last three rounds. 
- Alice: "Okay, Bob, I see you go first"
- Bob: "I delay until after the orc shoots."
- Bob drags his initiative down. He punches "Next"
- Bob: "You're up now, Alice"

# Loose rules
The app ís run on a small webserver that send updates to all connected browsers. Every player can add new entries, roll turns and add "effects" such as spells or whatever the DM wants. The app does not enforce rules to allow players to bend and fudge the story in whatever way suits them. 

- add your initiative and either roll a die or have the app roll it for you
- remembers the player in the current browser for easier adding in a next combat
- drag character up or down for the "delay" action
- swipe entries left or right to delete them
- click the "round" button on top to only show the initiative that is currently up

# Installation
This web server is dependent on the flask-socketio and gevent libraries. Assuming you have installed pip:
```sh
pip install flask-socketio gevent gevent-websocket
```
Note that the gevent installation will fail on Windows. The error message will direct you to install a VC++ package, which will solve this problem. 

Run the script by starting with python:
```sh
python present.py
````
# Webserver
By default, the webserver starts on port 85. Change this in the last line of present.py. This application is based on websockets, which will give you some trouble if you want to proxy from an apache machine. In that case, assuming you already have an Apache 2.4 and proxy_wstunnel, you can use the following configuration: 
```
<VirtualHost *:80>
  ProxyPreserveHost On
  RewriteEngine on
  ProxyRequests Off
  
  RewriteCond %{QUERY_STRING} transport=polling
  ### Use the IP running the present.py webserver
  RewriteRule /(.*)$ http://127.0.0.1:85/$1 [P]

  ProxyPass /socket.io ws://127.0.0.1:85/socket.io/
  ProxyPass / http://127.0.0.1:85/
  ProxyPassReverse / http://127.0.0.1:85/
</VirtualHost>

```

# Technology
Python flask, running a jquery mobile webpage, communicating over websockets. I also included the original themeroller theme (http://jqueryui.com/themeroller/) so you could roll your own. 
