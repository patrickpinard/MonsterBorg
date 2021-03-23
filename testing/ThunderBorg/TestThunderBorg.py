#!/usr/bin/env python
# coding: utf-8

import ThunderBorg3 as ThunderBorg
import time
import sys

# Name the global variables
global step
global TB


# Power settings
voltageIn = 1.2 * 10                    # Total battery voltage to the ThunderBorg
voltageOut = 12.0 * 0.95                # Maximum motor voltage, we limit it to 95% to allow the RPi to get uninterrupted power

# Setup the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)


print("--------------------------------")
print("  Welcome to the TELSA Project  ")
print("    Jonathan & Patrick Pinard   ")
print("    version 1.0 / mai 2020      ")
print("--------------------------------")

# Setup the ThunderBorg
TB = ThunderBorg.ThunderBorg()
TB.Init()

if not TB.foundChip:
    boards = ThunderBorg.ScanForThunderBorg()
    if len(boards) == 0:
        print("No ThunderBorg found, check you are attached :")
    else:
        print("No ThunderBorg at address %02X, but we did find boards: ")  % (TB.i2cAddress)
        for board in boards:
            print("    %02X (%d)") % (board, board)
        print("If you need to change the I²C address change the setup line so it is correct, e.g.")
        print("TB.i2cAddress = 0x%02X") % (boards[0])
    sys.exit()

# Ensure the communications failsafe has been enabled!
failsafe = False
for i in range(5):
    TB.SetCommsFailsafe(True)
    failsafe = TB.GetCommsFailsafe()
    if failsafe:
        break
if not failsafe:
    print("Board %02X failed to report in failsafe mode!") % (TB.i2cAddress)
    sys.exit()

# Show battery monitoring settings
battMin, battMax = TB.GetBatteryMonitoringLimits()
battCurrent = TB.GetBatteryReading()
print("-------------------------------")
print(" Battery monitoring settings:  ")
print('    Minimum  (red)     %02.2f V' % (battMin))
print('    Half-way (yellow)  %02.2f V' % ((battMin + battMax) / 2))
print('    Maximum  (green)   %02.2f V' % (battMax))
print('')
print('    Current voltage    %02.2f V' % (battCurrent))
print('')
print("-------------------------------")

# Function to perform a sequence of steps as fast as allowed

# Tell the system how to drive the stepper
sequence = [[1.0, 1.0], [1.0, -1.0], [-1.0, -1.0], [-1.0, 1.0]] # Order for stepping 
stepDelay = 0.002                                               # Delay between steps
degPerStep= 1.8                                                 # Number of degrees moved per step
step = -1

def MoveStep(count):
    global step
    global TB

    # Choose direction based on sign (+/-)
    if count < 0:
        dir = -1
        count *= -1
    else:
        dir = 1

    # Loop through the steps
    while count > 0:
        # Set a starting position if this is the first move
        if step == -1:
            drive = sequence[-1]
            TB.SetMotor1(drive[0])
            TB.SetMotor2(drive[1])
            step = 0
        else:
            step += dir

        # Wrap step when we reach the end of the sequence
        if step < 0:
            step = len(sequence) - 1
        elif step >= len(sequence):
            step = 0

        # For this step set the required drive values
        if step < len(sequence):
            drive = sequence[step]
            TB.SetMotor1(drive[0])
            TB.SetMotor2(drive[1])
        time.sleep(stepDelay)
        count -= 1

# Function to move based on an angular distance
def MoveDeg(angle):
    count = int(angle / float(degPerStep))
    MoveStep(count)

try:
    # Start by turning all drives off
    TB.MotorsOff()
    # Loop forever

    while True:
        print("Move at 50% motor 1 and 2")
        TB.SetMotor1(0.5)
        TB.SetMotor2(0.5)
        time.sleep(2)
        TB.SetMotors(0.75)
        time.sleep(2)
        # Move forward 1/4 turn 16 times with waits between
        for i in range(5):
            print("Move forward 1/4 turn then 1/16 5 times with waits between")
            MoveDeg(90)
            time.sleep(1)
            MoveDeg(10)
            time.sleep(1)
except KeyboardInterrupt:
    # CTRL+C exit, turn off the drives
    TB.MotorsOff()
    print ('Terminated')


# User code here, use TB to control the board