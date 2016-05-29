from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app)

## pip install flask-socketio gevent gevent-websocket

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


class Effect:
    def __init__(self, name, duration):
        self.name = name;
        self.duration = duration


class GameState:
    effects = []
    initiatives = []
    round = 0
    effects_timestamp = 0
    initiatives_timestamp = 0

    def __init__(self):
        self.effects_timestamp = time.time()
        self.initiatives_timestamp = time.time()

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

    ## Vals spsler! Als er meerdere "bless" effecten zijn wordt nu altijd de eerste verwijderd!
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
        if(init.turn):
            ## Net 1 gepopt
            if(index <= len(self.initiatives)):
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
        if len(self.initiatives) > 0:
            current_index = self.get_current()
            if current_index + 1 < len(self.initiatives):
                new_index = current_index + 1
            else:
                new_index = 0
                self.round += 1
                for eff in self.effects:
                    eff.duration -= 1
                trigger_effects_update_message()
            self.set_current(new_index)

    def rollback_initiative(self):
        self.initiatives_timestamp = time.time()
        if len(self.initiatives) > 0:
            current_index = self.get_current()
            if current_index - 1 < 0:
                if self.round > 0:
                    new_index = len(self.initiatives) - 1
                    self.round -= 1
                    for eff in self.effects:
                        eff.duration += 1
                    trigger_effects_update_message()
                    self.set_current(new_index)
            else:
                new_index = current_index - 1
                self.set_current(new_index)

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

@socketio.on('deleteeffect', namespace='/state')
def delete_effect(data):
    effects.remove_effect(data["name"])
    trigger_effects_update_message()

@socketio.on('addeffect', namespace='/state')
def add_effect(data):
    effects.add_effect(data["name"], int(data["duration"]))
    trigger_effects_update_message()

@socketio.on('move', namespace='/state')
def move_initative(data):
    effects.move_initiative(int(data["old_index"]), int(data["new_index"]))
    trigger_initiative_update_message()

@socketio.on('next', namespace='/state')
def next_initiative():
    effects.next_initiative()
    trigger_initiative_update_message()

@socketio.on('rollback_next', namespace='/state')
def former_initiative():
    effects.rollback_initiative()
    trigger_initiative_update_message()

@socketio.on('clear', namespace='/state')
def clear_initiatives():
    effects.clear()
    trigger_initiative_update_message()
    trigger_effects_update_message()

@socketio.on('delete', namespace='/state')
def delete_initiative(data):
    effects.remove_initiative(int(data["index"]))
    trigger_initiative_update_message()

@socketio.on('getstate', namespace='/state')
def get_state(data):
    if not "effects_timestamp" in data or data["effects_timestamp"] != effects.effects_timestamp:
        emit('neweffects', get_effects_state())
    if not "initiatives_timestamp" in data or data["initiatives_timestamp"] != effects.initiatives_timestamp:
        emit('newstate', get_initiative_state())


def trigger_initiative_update_message():
    emit('newstate', get_initiative_state(), broadcast=True, namespace="/state")

def trigger_effects_update_message():
    emit('neweffects', get_effects_state(), broadcast=True, namespace="/state")

@app.route('/')
def versus_the_world():
    return render_template('initiative.html')

@socketio.on('add', namespace='/state')
def add_initiative(data):
    effects.add_initiative(Initiative(data["name"], int(data["bonus"]), int(data["roll"])))
    trigger_initiative_update_message()

def get_initiative_state():
    return {"initiatives": effects.get_initiatives_dict(), "round": effects.round, "initiatives_timestamp":effects.initiatives_timestamp}

def get_effects_state():
    return {"effects":effects.get_effects_dict(), "effects_timestamp":effects.effects_timestamp}

@app.route('/present')
def initiative():
    return render_template('index.html')

if __name__ == '__main__':
    effects = GameState()
    socketio.run(app, host='0.0.0.0',port=85,debug=False)

