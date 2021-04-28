#!/usr/bin/env python
# coding: utf-8

# Auteur    : Patrick Pinard
# Date      : 24.10.2020
# Objet     : MonsterBorg 
# Source    : carLib.py
# Version   : 2.0


#   Clavier MAC :      
#  {} = "alt/option" + "(" ou ")"
#  [] = "alt/option" + "5" ou "6"
#   ~  = "alt/option" + n    
#   \  = Alt + Maj + / 

# Importation des librairies nécessaires
import sys
import time
import logging
import ThunderBorg3 as ThunderBorg

# on récupère le fichier de log basic (défini au niveau Borg.py)
logging = logging.getLogger()

DEBUG = False
MIN_SPEED = 30 # niveau minimum pour faire démarrer le moteur
MAX_SPEED = 95 # niveau maximum moteur autorisé


class car:
 
    """
    Classe definissant une voiture de type MonsterBorg et ses méthodes associées.
      move    : déplacement avec vitesse des moteurs gauche et droite
      start   : démarrage de la voiture (running = True)
      stop    : arrêt de la voiture  (running = False)
      battery : retourne le niveau actuel de la batterie LiPo (self.battCurrent)
    """

    def __init__(self, name):
        """
        Constructeur de la voiture MonsterBorg avec carte ThunderBorg pour gestion des quatre moteurs.
        """
        self.name = name
        logging.info('Début de la création de la voiture "%s"', self.name)  
        self.running = False
        self.speedleft = 0
        self.speedright = 0
        self.TB = ThunderBorg.ThunderBorg()
        self.TB.Init()
        if not self.TB.foundChip:
            boards = ThunderBorg.ScanForThunderBorg()
            if len(boards) == 0:
                logging.info("Aucune carte ThunderBorg détectée !")
                sys.exit()
            else:
                logging.info("Carte ThunderBorg à l'adresse %02X :" % (self.TB.i2cAddress))
                for board in boards:
                    logging.info('    %02X (%d)' % (board, board))
                logging.info('Changer adresse I²C dans programme : ')
                logging.info('TB.i2cAddress = 0x%02X' % (boards[0]))
            sys.exit()

        # communications failsafe enclenchée
        for i in range(5):
            self.TB.SetCommsFailsafe(True)
            failsafe = self.TB.GetCommsFailsafe()
            if failsafe:
                break
        if not failsafe:
            logging.info('Board %02X pas en mode failsafe!' % (self.TB.i2cAddress))
            sys.exit()

        # On met les moteurs à l'arrêt tous les moteurs
        self.TB.MotorsOff()

        # Définition des niveaux pour batteries
        # Pour 10 batteries AAA de 1,5V, on fixe les limites 
        # min : 9,5V, Moyen : 11,5V et Max - 13,5V
        self.battMin = 9.5
        self.battMax = 13.5
        self.TB.SetBatteryMonitoringLimits(self.battMin, self.battMax)
        
        # Affichage du niveau min, max et actuel des batteries
        self.battMin, self.battMax = self.TB.GetBatteryMonitoringLimits()
        self.battCurrent = self.TB.GetBatteryReading()
        logging.info('Etat des batteries ')
        logging.info('    Minimum  (rouge)  :  %02.2f V' % (self.battMin))
        logging.info('    Moyen    (jaune)  :  %02.2f V' % ((self.battMin + self.battMax) / 2))
        logging.info('    Maximum  (vert)   :  %02.2f V' % (self.battMax))
        logging.info('-------------------------------------')
        logging.info('    Voltage actuel    :  %02.2f V' % (self.battCurrent))
        logging.info('-------------------------------------')
        logging.info('Fin de la création de la voiture "%s" ', self.name)
        return

    def __repr__(self):
        """
        Méthode permettant d'afficher les paramètres de la voiture
        .....en cours de développement....
        """
        self.battCurrent = "{:5.2f}".format(self.battCurrent)
        return "Voiture : {}\n Running   : {}\n Batteries : {}\n Moteurs   : \n Gauche    : {}\n Droite    : {}\n".format(self.name, self.running, self.battCurrent, self.speedleft, self.speedright)
    
    def __del__(self):
        """
        Méthode permettant d'effacer une voiture MonsterBorg
        """ 
        del self
        logging.info('voiture effacée')
        return
    
    def battery(self):
        """
        Méthode retournant le niveau de la batterie LiPo avec 3 décimales après la virgule
        """ 
        # self.battCurrent = '%.3f'%(float(self.TB.GetBatteryReading()))
        self.battCurrent = round(self.TB.GetBatteryReading(), 3)
        logging.info('niveau batterie : '+ str(self.battCurrent))
        return self.battCurrent
    
    def move(self):
        """
        Méthode permettant de faire avancer la voiture avec une vitesse comprise entre -100 et 100
        speedleft et speedright pour chaque côté afin d'aller en avant et arrière
        """
        if self.running:
            self.TB.SetMotor2(-self.speedleft/100)
            self.TB.SetMotor1(self.speedright/100)
            if DEBUG: 
                logging.info("vitesse gauche : %s     droite : %s", self.speedleft, self.speedright)
        return

    def start(self):
        """
        Méthode permettant de d'autoriser le démarrage de la voiture.
        """ 
        self.running = True
        logging.info('Démarrage autorisé de la voiture %s', self.name)
        return

    def stop(self):
        """
        Méthode permettant de stopper la voiture complétement avec moteurs à 0 et led éteintes.
        """ 
        self.TB.SetMotor1(0)
        self.TB.SetMotor2(0)
        self.TB.SetCommsFailsafe(False)
        self.TB.SetLedShowBattery(False)
        self.running = False
        logging.info('Arrêt complet de la voiture %s', self.name)
        return

  