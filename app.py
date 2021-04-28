#!/usr/bin/env python
# coding: utf-8
# Auteur    : Patrick Pinard
# Date      : 28.4.2021
# Objet     : Pilotage de Monsterborg avec interface web basée sur API RESTful Flask et bootstrap
# Version   : 2.0
# 
#  {} = "alt/option" + "(" ou ")"
#  [] = "alt/option" + "5" ou "6"
#   ~  = "alt/option" + n    
#   \  = Alt + Maj + / 


from flask import Flask, render_template, Response, request, redirect, jsonify, url_for, session, abort
from flask_restful import Resource, Api, reqparse
from time import sleep
import os
import random
import psutil
import logging
import threading
import carLib
import json
from camera_pi import Camera
from flask_cors import CORS

global Borg, state, battery, cpu_usage, signal

PASSWORD    = 'password'
USERNAME    = "admin"
DEBUG       = True
name        = ""

# fichier log
logging.basicConfig(filename='app.log', filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(Camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/', methods=["GET", "POST"])
def home():
    
    global Borg

    if request.method == "GET":
        # Check if user already logged in
        
        if not session.get("logged_in"):
            logging.info("login not done, redirect to 'login' page")
            return render_template('login.html', error_message="")
        else:
            logging.info("login already done, redirect to 'index' page")
            return "already logged"

    if request.method == "POST":
        # Try to login user
        
        name = request.form.get("username")
        pwd = request.form.get("password")

        if pwd == PASSWORD and name == USERNAME:
                logging.info("user: " + name + " logged in")
                session['logged_in'] = True
                return render_template('index.html',user=name)
        else:
                logging.warning("login with wrong username and password")
                return render_template('login.html', error_message="wrong username and password. Please try again")
        
        
@app.route("/logout", methods=['POST'])
def logout():
    global name
    # stop the Monsterborg if logout
    # Borg.running = False
    logging.info("Monsterborg stopped when logout")
    session["logged_in"] = False
    logging.info("user " + name + " logout")
    return render_template("login.html")


@app.route("/startstop",methods = ['POST', 'GET'])                          
def startstop():

    global Borg, name
    
    if session.get('logged_in'):
            parser = reqparse.RequestParser(bundle_errors=True)
            parser.add_argument('state', type=str, required=True, help='START/STOP MonsterBorg')           
            args = parser.parse_args()
            command = args['state']
            if command == "START":
                    Borg.running = True
                    state = "RUNNING"
                    logging.info("Starting MonsterBorg ")
            elif command == "STOP":
                    Borg.running = False
                    state = "STOPPED"
                    logging.info("Stopping MonsterBorg ")
    return render_template("index.html")

@app.route("/post", methods=['POST'])
def post():
    
    if request.method == "POST":
         
        content = request.json
        steering = int(json.dumps(content['joy1_x']))
        speed = -int(json.dumps(content['joy1_y']))
        
        if steering > 3:
            Borg.speedleft  = int(speed * (1 - steering/100))
            Borg.speedright = speed
        elif steering < -3:
            Borg.speedright = int(speed * (1 + steering/100))
            Borg.speedleft  = speed
        else:
            Borg.speedright = speed 
            Borg.speedleft  = speed   
        if DEBUG :
            logging.info("steering  : " + str(steering))
            logging.info("speed     : " + str(speed))  
            logging.info("speedleft : " + str(Borg.speedleft))
            logging.info("speedright: " + str(Borg.speedright))         

        return "ok"


class FlaskApp (threading.Thread):
   def __init__(self, threadID, name):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
   def run(self):
      logging.info("FlaskApp Thread started") 
      app.run(host='0.0.0.0', port = 5000, debug=False)


class MoveBorg (threading.Thread):
    global Borg
    def __init__(self, threadID, name):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name

    def run(self):
        logging.info("MoveBorg Thread started") 
        while True : 
            try:
                while Borg.running: 
                    Borg.move()
            except: logging.error("Move error in Thread")

class DNSUpdater (threading.Thread):
    
    def __init__(self, threadID, name):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name

    def run(self):
        logging.info("DNSUpdater Thread started") 
        while True : 
            try:
                while True: 
                    os.system("dns-updater -c /home/pi/.config/exo-dns-updater.toml")
                    logging.info("dns-updater executed every 60 sec.")
                    sleep(60)
            except: logging.error("DNSUpdater error in Thread")

class HealthCheck (threading.Thread):
   def __init__(self, threadID, name):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
   def run(self):

       global Borg, battery, state,cpu_usage, signal

       logging.info("HealthCheck Thread started") 
       while True: 
        sleep(5)
        battery = Borg.battery()
        if Borg.running:
            state = "RUNNING"
        else: 
            state = "STOPPED"

if __name__ == '__main__':
    
    app.secret_key = os.urandom(12)
    
    #Create the MonsterBorg car
    Borg = carLib.car("MonsterBorg")
    Borg.start()

    # Create new threads
    thread1 = FlaskApp(1, "FlaskApp")
    thread2 = MoveBorg(2, "MoveBorg")
    thread3 = HealthCheck(3, "Healthcheck")
    #thread4 = DNSUpdater(4, "DNS-Updater")
    logging.info("Threads created ....") 
    
    # Start new Threads
    thread1.start()
    thread2.start()
    thread3.start()
    #thread4.start()

    logging.info("Threads started ....")
    thread1.join()
    thread2.join()
    thread3.join()
    #thread4.join()
    logging.info("Threads joined ....")


