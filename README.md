# Initiative!
We like playing D20 based roleplaying games - Pathfinder, Dungeons and Dragons 3rd edition, D&D Next, etcetera. A lot of time goes into combat administration. We continually spend time figuring out the order of initiatie. Whose turn is it? Bob again? But shouldn't Alice have gone first? 

These discussions take the speed out of the game, a problem this page tries to solve by delegating to players. All of the players can call up the same state on their tablet or smartphone. All players can edit the game state allowing the DM to delegate the calling of rounds and round based effect to them. 

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
The app is run on a small webserver that send updates to all connected browsers. Every player can add new entries, roll turns and add "effects" such as spells or whatever the DM wants. The app does not enforce rules to allow players to bend and fudge the story in whatever way suits them. Yes, this allows for cheating, but if your friends want to cheat their DM in a sunday night kitchen table game you have bigger problems (and a need for better friends).

Features: 
- add your initiative and either roll a die or have the app roll it for you
- remembers the player in the current browser for easier adding in a next combat
- drag character up or down for the "delay" action
- swipe entries left or right to delete them
- click the "round" button on top to only show the initiative that is currently up
- Shortcuts for common actions (N for next initiative, for example)
- Friendly beeps if the initiative changes while another browser tab is active (also known as "the facebook beep" for multiple reasons..)
- Seperate session rooms

One thing to note is that session states live in the memory of the app and are not persistent. If the app restarts, the initative sessions are lost. 

# Installation
This web server is dependent on the flask-socketio and gevent libraries. Assuming you have installed pip:
```sh
pip install -r requirements.txt 
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
  ServerName init.yourserver.com
  DocumentRoot /usr/local/initiative/static

  <FilesMatch "\.(jpg|jpeg|png|gif|js|css)$">
    Header set Cache-Control "max-age=290304000, public"
  </FilesMatch>

  Alias "/static" "/usr/local/initiative/static"
  <Directory "/usr/local/initiative/static">
    Require all granted
  </Directory>

    RewriteCond %{QUERY_STRING} transport=polling
    RewriteRule /(.*)$ http://127.0.0.1:85/$1 [P]

    ProxyPass /socket.io ws://127.0.0.1:85/socket.io/

    ProxyPassMatch ^/static !
    ProxyPass / http://127.0.0.1:85/
    ProxyPassReverse / http://127.0.0.1:85/

</VirtualHost>


```
Note that this configuration serves the static files from a seperate location instead of using the Python webserver. You cannot run this application as an WSGI application, or at least I could not, because the gevent handler cannot be found or cannot be started. 


# Technology
Python flask, running a jquery mobile webpage, communicating over websockets using timestamped messsages. I included the original themeroller theme (http://jqueryui.com/themeroller/) so you can roll your own. 

