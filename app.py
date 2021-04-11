#!/usr/bin/env python
# coding: utf-8
# Auteur    : Patrick Pinard
# Date      : dimanche 11.4.2021
# Objet     : Pilotage de Monsterborg avec interface web basée sur API RESTful Flask et bootstrap
# Version   : 1.0
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
from camera_pi import Camera

global Borg, state, battery, cpu_usage, signal

PASSWORD = 'password'
USERNAME = "admin"

cpu_usage ="unknown"
signal = "GOOD"
state = "unknown"
battery = "unknown"
name = "unknown"
fast_turn = False
full_speed = False

# fichier log
logging.basicConfig(filename='app.log', filemode='w', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
 
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
    
    global Borg, cpu_usage, signal, battery, state, name, fast_turn, full_speed

    if request.method == "GET":
        # Check if user already logged in
        logging.info("received a GET request")
        if not session.get("logged_in"):
            logging.info("login not done, redirect to 'login' page")
            return render_template('login.html', error_message="please login")
        else:
            logging.info("login already done, redirect to 'index' page")
            return "already logged"

    if request.method == "POST":
        # Try to login user
        logging.info("received a POST request")
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
    Borg.running = False
    logging.info("Monsterborg stopped when logout")
    session["logged_in"] = False
    logging.info("user " + name + " logout")
    return render_template("login.html")


@app.route("/startstop",methods = ['POST', 'GET'])                          
def startstop():

    global Borg, cpu_usage, signal, battery, state, name
    
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
    return render_template("index.html",user = name)

@app.route('/move',methods = ['POST'])  
def move():
    
    global Borg, cpu_usage, signal, battery, state, name
    
    parser = reqparse.RequestParser(bundle_errors=True)
    parser.add_argument('direction', type=str, required=True, help='MonsterBorg move direction : left, right, forward, backward')           
    args = parser.parse_args()
    direction = args['direction']
    
    #if steering > 0.0:             
        #    pour aller à droite, on freine les roues droites                                                                                                                                                      
    #    Borg.speedleft  = speed * (1 - steering)
    #    Borg.speedright = speed
    #elif steering < 0.0:
        #    pour aller à gauche, on freine les roues gauches
    #    Borg.speedright = speed * (1 + steering) 
    #    Borg.speedleft  = speed
    #elif steering == 0.0:
    #    Borg.speedright = speed 
    #    Borg.speedleft  = speed   

    if direction == "left":    
        speed = 0.35
        steering = 0.25                                                                                                                                                            
        Borg.speedright  = -speed 
        Borg.speedleft = speed * (1 + steering)
        logging.info("received command : move left / speedright = " + str(Borg.speedright) +  "  speedleft = " + str(Borg.speedleft))
    elif direction == "right":
        speed = 0.35
        steering = 0.25
        Borg.speedright = speed * (1 + steering)
        Borg.speedleft  = -speed 
        logging.info("received command : move right / speedright = " + str(Borg.speedright) +  "  speedleft = " + str(Borg.speedleft))
    elif direction == "forward":
        speed = 0.4
        steering = 0.0
        Borg.speedright = -speed 
        Borg.speedleft  = -speed
        logging.info("received command : move forward / speedright = " + str(Borg.speedright) +  "  speedleft = " + str(Borg.speedleft))
    elif direction == "backward":
        speed = 0.4
        steering = 0.0
        Borg.speedright = speed 
        Borg.speedleft  = speed
        logging.info("received command : move backward / speedright = " + str(Borg.speedright) +  "  speedleft = " + str(Borg.speedleft))
    return render_template("index.html",user = name, battery=battery, state=state, signal=signal, cpu=cpu_usage, left= Borg.speedleft, right=Borg.speedright) 


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
        cpu_usage = psutil.cpu_percent(4)
        signal = "GOOD"
        logging.info("Healtcheck / CPU usage : " + str(cpu_usage) + "   / Battery level (V) : " + str(battery) + "  / State : " + state + "  / Signal : " + signal)  

if __name__ == '__main__':
    
    app.secret_key = os.urandom(12)
    
    #Create the MonsterBorg car
    Borg = carLib.car("MonsterBorg")
    Borg.start()

    # Create new threads
    thread1 = FlaskApp(1, "FlaskApp")
    thread2 = MoveBorg(2, "MoveBorg")
    thread3 = HealthCheck(3, "Healthcheck")
    logging.info("Threads created ....") 
    
    # Start new Threads
    thread1.start()
    thread2.start()
    thread3.start()

    logging.info("Threads started ....")
    thread1.join()
    thread2.join()
    thread3.join()
    logging.info("Threads joined ....")


