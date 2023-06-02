import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.behaviors.focus import FocusBehavior
from kivy.properties import ObjectProperty
from kivy.properties import ListProperty
from kivy.graphics import Rectangle, Color
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.config import Config

import sys
import requests
from requests.exceptions import ConnectionError
import json
import datetime
from urllib.request import urlretrieve
from urllib.error import HTTPError
import os.path
# 1280 x 800 display

Config.set('kivy', 'window_icon', 'assets/Logo.png')
Builder.load_file('scanimatron.kv')
Window.size = (1280, 800)

# Always-focused text input
class SpecialTextInput(TextInput):
    n = False
    def on_focus(self, instance, value):
        if not value:   # de-focused
            if self.n:
                Clock.schedule_once(self.self_focus, 0.1)
            else:
                self.n = True

    def self_focus(self, _):
        self.focus = True

    # event = Clock.schedule_once(my_callback, .5)
    # event()  # nothing will happen since it's already scheduled.
    # event.cancel()  # cancel it
    # event()  # now it's scheduled again.

# Main class
class MyFloatLayout(Widget):

    # Environment variables
    url = "192.168.0.45"  # "127.0.0.1"
    port = "8000"
    directory = "C:/Users/Justi/Scanimatron"  # "C:/Users/Justin Leighton/Desktop/Development/Grocery Database/Scanimatron"
    Window.fullscreen = True  # False

    # Dynamic variables
    upc = ObjectProperty(None)
    clock_variable = None
    UndoFlag = False
    desc = ""
    title = ""
    delta_int = -1
    qty = 0

    def scan(self):

        # Gather Inputs
        upc_input = self.upc.text

        # Convert toggle to int
        if self.delta.state == "normal":
            self.delta_int = 1
        else:
            self.delta_int = -1

        # UPC Detail Functions
        try:
            self.get_upcdetail_local(upc_input)
        except (ConnectionError, IndexError):
            self.get_upcdetail_public(upc_input)
            self.post_upcdetail(upc_input=upc_input,
                                desc_input=self.title,
                                detail_input=self.desc)

        # Insert scan record
        if self.infobutton.state == "normal" and self.qty + self.delta_int > 0:
            self.post_scans(upc_input, self.delta_int)
            self.qty += self.delta_int
            self.UndoFlag = True

        # Update UI
        self.updateUI(upc_input, self.desc, self.title, self.qty)

        # Schedule reset view
        self.timer()

    def updateUI(self, upc_input, title_input, desc_input, qty_input):

        # Fields
        self.upcoutput.text = upc_input
        self.titleoutput.text = title_input
        self.descoutput.text = desc_input
        self.onhandoutput.text = str(qty_input)

        # Buttons
        self.infobutton.state = "normal"

        if self.UndoFlag:
            self.undobutton.icon = "assets/Undo.png"
        else:
            self.undobutton.icon = ""

        # Set image field
        img_input = f"{self.directory}/images/{upc_input}.jpg"
        if os.path.isfile(img_input):
            self.imagefield.source = img_input
        else:
            self.imagefield.source = "assets/blank.png"

        # Set peanut indicator
        if 'peanut' in self.descoutput.text.lower():
            self.peanutindicator.text = "Peanut Warning"
            self.peanutindicator.background_color = [237 / 255, 66 / 255, 69 / 255, 1]
        else:
            self.peanutindicator.text = ""
            self.peanutindicator.background_color = [47 / 255, 49 / 255, 54 / 255, 1]

        # Reset text input
        self.upc.text = ""

    def undo(self):
        self.reset()

    def reset(self):
        self.delta.state = "down"
        self.UndoFlag = False
        self.updateUI("", "", "", "")

    def timer(self):
        if self.clock_variable is None:
            self.clock_variable = Clock.schedule_once(lambda dt: self.reset(), 60)
        else:
            self.clock_variable.cancel()
            self.clock_variable = Clock.schedule_once(lambda dt: self.reset(), 60)

    def exit(self):
        App.get_running_app().stop()

    def get_upcdetail_local(self, upc_input):

        # API call
        r = requests.get(f'http://{self.url}:{self.port}/inventory/api/upcdetail/?UPC={upc_input}')

        # Extract values from json
        self.title = r.json()[0]["description"]
        self.desc = r.json()[0]["details"]
        self.qty = r.json()[0]["onhand"]
        if self.qty == None:
            self.qty = 0
        # self.image = json_response['image']  -------------------------------------------------------------------------

    def get_upcdetail_public(self, upc_input):

        # Parameters
        url = "https://api.upcitemdb.com/prod/trial/lookup?upc=%s" % upc_input
        headers = {'cache-control': "no-cache", }

        # API call
        r = requests.request("GET", url, headers=headers)

        # Extract values from json
        self.title = self.json_value_extract(r, "title").replace("'", "")
        self.desc = self.json_value_extract(r, "description").replace("'", "")
        self.qty = 0
        image = self.json_value_extract(r, "images").replace("'", "")

        # Download image
        try:
            urlretrieve(image, f"{self.directory}/images/{str(upc_input)}.jpg")
        except:
            pass

    def post_scans(self, upc_input, delta_input):
        payload = {'UPC': upc_input, 'date': datetime.datetime.today(), 'delta': delta_input}
        requests.post(f'http://{self.url}:{self.port}/inventory/api/scans/', data=payload)

    def post_upcdetail(self, upc_input, desc_input, detail_input):
        img_input = f"{self.directory}/images/{upc_input}.jpg"
        if os.path.isfile(img_input):
            files = {'image': open(f'{img_input}', 'rb')}
        else:
            files = {}
        payload = {'id': upc_input, 'description': desc_input, 'details': detail_input}
        requests.request("POST", f'http://{self.url}:{self.port}/inventory/api/upcdetail/', data=payload, files=files)

    def json_value_extract(self, response, field, public=True):
        output = "error"
        json = response.json()
        if public:
            try:
                if public:
                    output = json["items"][0][field]
                else:
                    output = json[0][field]
            except:
                pass

        if type(output) is list:
            output = output[0]

        return str(output)


class Scanimatron(App):
    title = "Scanimatron"

    def build(self):
        return MyFloatLayout()


if __name__ == "__main__":
    Scanimatron().run()
