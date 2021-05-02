""" colorize your tẻminal """
import time
import datetime

class bcolors:
    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKCYAN    = '\033[96m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    
def now():
    return '[' + bcolors.HEADER + str(datetime.datetime.now()) + bcolors.ENDC + '] '
    
def pi_log_i(string):
    print(now(), end = '')
    print(bcolors.OKGREEN, end = '')
    print(string, end = '')
    print(bcolors.ENDC)
    
def pi_log_w(string):
    print(now(), end = '')
    print(bcolors.WARNING, end = '')
    print(string, end = '')
    print(bcolors.ENDC)

def pi_log_e(string):
    print(now(), end = '')
    print(bcolors.FAIL, end = '')
    print(string, end = '')
    print(bcolors.ENDC)

def pi_log_d(string):
    print(now(), end = '')
    print(bcolors.OKBLUE, end = '')
    print(string, end = '')
    print(bcolors.ENDC)

def pi_log_v(string):
    print(now(), end = '')
    print(string)