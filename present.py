import random
import re
import socket

from flask import Flask, render_template
from flask import make_response
from flask import request
from flask_socketio import SocketIO, emit, join_room, rooms
import logging
import time

app = Flask(__name__)
socketio = SocketIO(app)

## Set up logging, disable access logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
log = logging.getLogger("initiative")
handler = logging.StreamHandler()
log.addHandler(handler)


## A creative function that checks if the client IP is similar to the server IP
## Very hacky, but works for me.
serverip = False
def is_client_trusted():
    trusted = False
    global serverip
    if not serverip:
        ## Helpful internet code quote:
        ## https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
        serverip = [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in
             [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        serverip = serverip.split(".")

    if request.remote_addr is not None:
        client = request.headers.get("X-Forwarded-For") if "X-Forwarded-For" in request.headers else request.remote_addr

        ## If the X=Forwarded header was used, we have a comma seperaterd list of IP adresses
        client = [xfor.strip() for xfor in client.split(',')]
        client = client[0].split(".")

        ## It's not infallible, but good enough for me. If the first two tuples match, I assume you are on the same network
        trusted = client[0] == serverip[0] and client[1] == serverip[1]
    return trusted

## A simple static function that generates a random name to use for your sessions
suggestions = ["abnormal","abracadabra","adventure","alchemy","allegorical","allusion","amulet","apparition","apprentice","atmosphere","attraction","awe","beast","beauty","belief","berserk","bewitch","bizarre","black cat","blindfold","bogeyman","brew","brownies","captivate","cast","castles","cauldron","cave","chalice","changeling","characters","charisma","charming","chimerical","clairvoyant","clarity","classic","cliffs","clock","collapse","comic","compare","conjure","conspirator","creative","creature","crisis","crow","cruelty","crystal ball","curious","curse","dancing","daring","dazzle","deeds","deformity","delirious","demon","detect","detection","detective","disappearance","disaster","dose","dragon","dramatic","dread","dream","dwarf","eek","eerie","elf","empire","enchanting","esp","event","evil","experience","fable","fabricate","fairy","fairy","fairy ring","fairy tale","familiar","fanciful","fantastic","fantasy","fascination","favors","fiction","fiery","figment","folklore","foolishness","forces","forgery","garb","gestures","ghost","giant","gifts","glimmer","gnome","goblin","godmother","gowns","grateful","graveyard","green","grimm","grotesque","hag","hallucinate","harbinger","helpful","herbs","heroic","hollow","horror","howls","humped","idyll","illusions","image","imagery","imaginary","imagination","imp","impressive","improvise","impulse","incantation","incognito","informative","ingenious","inspiration","invisible","jargon","jaunt","jiggle","joking","keepsake","kettle","kidnap","king","kingdom","lands","legend","legerdemain","leprechauns","lore","lucky","lunar","magic","carpet","magical","magician","majesty","malevolence","mask","medieval","medium","miracle","mischief","mischievous","misshapen","monster","moon","muse","musings","mysterious","mystery","mystical","myth","mythical","narration","nature","necromancer","necromancy","nemesis","newt","notion","oberon","odd","ogre","oracle","otherworldly","overpower","overwhelm","owl","pattern","perform","petrify","pixie","pixie dust","plot","poisonous","potent","potion","powder","power","prey","prince","prophet","protection","prowl","quail","quake","quash","quaver","queen","quest","question","quizzical","raconteur","rage","realm","reasoning","reference","reign","repel","reveal","robe","rule","sage","sandman","scare","scold","scroll","seeking","seer","setting","shaman","soothsayer","sorcerer","sorcery","specter","speculation","spell","spider","spirits","stars","story","substitution","supernatural","superstition","talisman","terror","theory","thrilling","torch","tragic","transform","tremors","tricks","troll","unbelievable","unexplained","unicorn","unique","unusual","valiant","valor","vampire","vanguard","vanish","vanquish","variety","venomous","version","vice","vicious","victim","visionary","vital","wail","wand","ward","watchful","weird","werewolf","western","whim","whimsical","whine","whisk","whispers","white","wicked","willies","win","wince","wisdom","wish","witch","worry","worship","wrinkled","wrongdoing","xanadu","yearn","yesteryear","youth","yowl","zap","zealous","zigzag"]
def get_suggestions(existing_sessions):
    new_suggestions = []
    i = 0
    while i < 5:
        new_suggestion = random.choice(suggestions) + str(random.randint(1, 10))
        if new_suggestion not in existing_sessions:
            new_suggestions.append(new_suggestion)
            i += 1
    return new_suggestions


## Used by the cookie code to see which sessions this user visited. It resturns a new cookie including all the session names know to this visitor
def get_and_add_known_session_cookie(session_name=None, sessions_known=None):
    known_list = []
    if(session_name):
        known_list.append(session_name)

    if sessions_known:
       known_list.extend(sessions_known.split(";"))
    ## Let op! Set comprejensino, om alle dubbelingen eruit te werken
    known_list = {session for session in known_list if session in init.get_gamestate_names()}
    return known_list

## A placeholder class keeping track of all of the variables related to a single initative roll
class Initiative:
    def __init__(self, name, bonus, roll):
        self.name = name
        self.bonus = int(bonus)
        self.roll = int(roll)
        self.turn = False
        self.total = self.bonus + self.roll

    def is_earlier_than(self, other):
        if self.total != other.total:
            return self.total > other.total
        else:
            return self.bonus > other.bonus

    def set_turn(self, turn):
        self.turn = turn

    def get_as_dict(self):
        return {"name":self.name,"total":self.total,"turn":self.turn}

## Similar to the initative class, but keeping track of a single effect
class Effect:
    def __init__(self, name, duration):
        self.name = name
        self.duration = duration


## A single game is kept in this class
class GameState:
    def __init__(self, session):
        self.effects_timestamp = time.time()
        self.initiatives_timestamp = time.time()
        self.session = session
        self.effects = []
        self.initiatives = []
        self.session = session
        self.round = 0
        self.create_timestamp = time.time()
        self.effects_timestamp = 0
        self.initiatives_timestamp = 0
        self.last_change_timestamp = self.create_timestamp


    def add_effect(self, name, duration):
        self.effects_timestamp = time.time()
        self.effects.append(Effect(name, duration))

    def add_initiative(self, new_init):
        self.initiatives_timestamp = time.time()
        insert_at = 0
        for init in self.initiatives:
            if new_init.is_earlier_than(init):
                break
            else:
                insert_at += 1
        self.initiatives.insert(insert_at, new_init)

    def next_round(self, rollback=False):
        self.initiatives_timestamp = time.time()
        for eff in self.effects:
            eff.duration = eff.duration + (1 if rollback else -1)

    def clear(self):
        self.initiatives_timestamp = time.time()
        self.effects_timestamp = time.time()
        self.effects[:] = []
        self.initiatives[:] = []
        self.round = 0

    ## Vals speler! Als er meerdere "bless" effecten zijn wordt nu altijd de eerste verwijderd!
    def remove_effect(self, name):
        self.effects_timestamp = time.time()
        i = 0
        while i < len(self.effects):
            if self.effects[i].name == name:
                self.effects.pop(i)
                break
            i += 1

    def remove_initiative(self, index):
        self.initiatives_timestamp = time.time()
        init = self.initiatives.pop(index)
        if init.turn:
            ## Net 1 gepopt
            if index <= len(self.initiatives):
                self.set_current(index)
            else:
                self.set_current(0)

    def move_initiative(self, old_index, new_index):
        self.initiatives_timestamp = time.time()
        init = self.initiatives[old_index]
        self.initiatives.insert(new_index, self.initiatives.pop(old_index))
        if init.turn:
            self.set_current(old_index)

    def next_initiative(self):
        self.initiatives_timestamp = time.time()
        effects_change = False
        if len(self.initiatives) > 0:
            current_index = self.get_current()
            if current_index + 1 < len(self.initiatives):
                new_index = current_index + 1
            else:
                new_index = 0
                self.round += 1
                for eff in self.effects:
                    eff.duration -= 1
                effects_change = True
            self.set_current(new_index)
        if effects_change:
            self.effects_timestamp = time.time()

        return effects_change

    def rollback_initiative(self):
        self.initiatives_timestamp = time.time()
        effects_change = False
        if len(self.initiatives) > 0:
            current_index = self.get_current()
            if current_index - 1 < 0:
                if self.round > 0:
                    new_index = len(self.initiatives) - 1
                    self.round -= 1
                    for eff in self.effects:
                        eff.duration += 1
                    effects_change = True
                    self.set_current(new_index)
            else:
                new_index = current_index - 1
                self.set_current(new_index)

        if effects_change:
            self.effects_timestamp = time.time()

        return effects_change

    def get_effects_dict(self):
        return [{"name": eff.name, "rounds": eff.duration if eff.duration > 0 else 0} for eff in self.effects]

    def get_initiatives_dict(self):
        return [init.get_as_dict() for init in self.initiatives]

    def set_current(self,to_index):
        i = 0
        while i < len(self.initiatives):
            self.initiatives[i].set_turn(i == to_index)
            i += 1

    def get_current(self):
        i = 0
        while i < len(self.initiatives):
            if self.initiatives[i].turn:
                break
            i += 1
        return i

## Overlay class keeping track of the different games
class InitiativeApp:
    def __init__(self):
        self.gamestates = {}
        self.session_validator = re.compile("^([\w\d_-]){3,}$")

    def session_validate(self, session):
        return self.session_validator.match(session)

    def get_gamestate_from_data(self,data):
        if "session" in data:
            session = data["session"].lower()
            if self.session_validate(session):
                return self.get_gamestate(session)
            else:
                return None
        else:
            return None

    def get_gamestate(self,session):
        if session in self.gamestates:
            gamestate = self.gamestates[session]
        else:
           gamestate = self.init_gamestate(session)
        return gamestate

    def delete_gamestate(self,session):
        if session in self.gamestates:
            del self.gamestates[session]

    ## Delete all empty gamestates that were created longer then 15 minutes ago
    def run_wiper(self):
        sessions = []
        currrenttime = time.time()

        ## This need to move. Basically, if the last update was more then 15 minutes ago I wipe this session.
        ## I now only kill sessions with < 2 initiatives.
        timediff = 60 * 15
        for session in self.gamestates:
            if (currrenttime - self.gamestates[session].last_change_timestamp) > timediff:
                if count(session.initiatives) < 2:
                    sessions.append(session)
        for session in sessions:
            self.delete_gamestate(session)


    def init_gamestate(self,session):
        gamestate = GameState(session)
        self.gamestates[session] = gamestate
        return gamestate

    def get_gamestate_names(self):
        return self.gamestates.keys();

@socketio.on('deleteeffect', namespace='/state')
def delete_effect(data):
    gamestate = init.get_gamestate_from_data(data)
    gamestate.remove_effect(data["name"])
    trigger_effects_update_message(gamestate)

@socketio.on('addeffect', namespace='/state')
def add_effect(data):
    gamestate = init.get_gamestate_from_data(data)
    gamestate.add_effect(data["name"], int(data["duration"]))
    trigger_effects_update_message(gamestate)

@socketio.on('move', namespace='/state')
def move_initative(data):
    gamestate = init.get_gamestate_from_data(data)
    gamestate.move_initiative(int(data["old_index"]), int(data["new_index"]))
    trigger_initiative_update_message(gamestate)

@socketio.on('next', namespace='/state')
def next_initiative(data):
    gamestate = init.get_gamestate_from_data(data)
    # Returns True if effects should also trigger
    if gamestate.next_initiative():
        trigger_effects_update_message(gamestate)
    trigger_initiative_update_message(gamestate)

@socketio.on('rollback_next', namespace='/state')
def former_initiative(data):
    gamestate = init.get_gamestate_from_data(data)
    # Returns True if effects should also trigger
    if gamestate.rollback_initiative():
        trigger_effects_update_message(gamestate)
    trigger_initiative_update_message(gamestate)

@socketio.on('clear', namespace='/state')
def clear_initiatives(data):
    gamestate = init.get_gamestate_from_data(data)
    gamestate.clear()
    trigger_initiative_update_message(gamestate)
    trigger_effects_update_message(gamestate)

@socketio.on('delete', namespace='/state')
def delete_initiative(data):
    gamestate = init.get_gamestate_from_data(data)
    gamestate.remove_initiative(int(data["index"]))
    trigger_initiative_update_message(gamestate)

@socketio.on('getstate', namespace='/state')
def get_state(data):
    session = data["session"]
    if session not in rooms():
        join_room(session)
    gamestate = init.get_gamestate_from_data(data)

    if "effects_timestamp" not in data or data["effects_timestamp"] != gamestate.effects_timestamp:
        emit('neweffects', get_effects_state(gamestate))
    if not "initiatives_timestamp" in data or data["initiatives_timestamp"] != gamestate.initiatives_timestamp:
        emit('newstate', get_initiative_state(gamestate))

def trigger_initiative_update_message(gamestate):
    gamestate.last_change_timestamp = time.time()
    emit('newstate', get_initiative_state(gamestate), room=gamestate.session, namespace="/state")

def trigger_effects_update_message(gamestate):
    gamestate.last_change_timestamp = time.time()
    emit('neweffects', get_effects_state(gamestate), room=gamestate.session, namespace="/state")

@app.route('/<session>')
@app.route('/')
def versus_the_world(session = None):
    SESSIONS_KNOWN = "known"
    known_sessions_raw = request.cookies.get(SESSIONS_KNOWN)

    ## A new session instance is a good moment to run a quick wipe
    init.run_wiper()

    if session is not None and init.session_validate(session):
        gamestate = init.get_gamestate(session.lower())
        response = make_response(render_template('initiative.html', session=gamestate.session))
        known_sessions = get_and_add_known_session_cookie(gamestate.session, known_sessions_raw)
    else:
        init.get_gamestate_names()
        if is_client_trusted():
            known_sessions = init.get_gamestate_names()
        else:
            known_sessions = get_and_add_known_session_cookie(sessions_known=known_sessions_raw)
        response = make_response(render_template('welcome.html', suggestions=get_suggestions(init.get_gamestate_names()), known_sessions=known_sessions))

    response.set_cookie(SESSIONS_KNOWN, ";".join(known_sessions), max_age=2147483646)
    return response



@socketio.on('add', namespace='/state')
def add_initiative(data):
    gamestate = init.get_gamestate_from_data(data)
    gamestate.add_initiative(Initiative(data["name"], int(data["bonus"]), int(data["roll"])))
    trigger_initiative_update_message(gamestate)

def get_initiative_state(gamestate):
    return {"session": gamestate.session, "initiatives": gamestate.get_initiatives_dict(), "round": gamestate.round, "initiatives_timestamp":gamestate.initiatives_timestamp}

def get_effects_state(gamestate):
    ## Adding the session in case someone is listening in on multiple rooms from one browser
    return {"session": gamestate.session, "effects": gamestate.get_effects_dict(), "effects_timestamp": gamestate.effects_timestamp}


if __name__ == '__main__':
    init = InitiativeApp()
    socketio.run(app, host='0.0.0.0',port=85,debug=True)

