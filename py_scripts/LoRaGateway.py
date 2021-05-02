import os
import time
from myModules.data_format import *
from myModules.colors import *

from SX127x.LoRa import *
#from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD
import random
import requests 
from websocket import create_connection

#parser = LoRaArgumentParser("Lora tester")

class mylora(LoRa):
    
    SERVER_URL = 'ws://192.168.3.107:5000'
    GATEWAY_ID = MSG.NODE_ID.GATEWAY

    seqID = 1
    txMsg = [None] * 10
    rxMsg = [None] * 10
    ws = None
    
    def __init__(self, verbose=False, do_calibration = False, calibration_freq = 434):
        pi_log_d('start lora config')
        super(mylora, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_freq(434)
        self.set_pa_config(pa_select=1, max_power=21, output_power=15)
        self.set_bw(BW.BW125)
        self.set_coding_rate(CODING_RATE.CR4_5)
        self.set_spreading_factor(6)
        self.set_rx_crc(True)
        self.set_lna_gain(GAIN.G1)
        self.set_implicit_header_mode(True)
        self.set_mode(MODE.STDBY)
        self.set_detect_optimize(0b101)
        self.set_detection_threshold(0x0C)
        self.set_pa_config(pa_select=1)
        self.set_preamble(0x0008)
        self.set_payload_length(10)
        self.set_pa_config(pa_select = 1, max_power = None, output_power = 15)
        self.set_dio_mapping([0] * 6)
        self.set_pa_dac(True)
        self.set_ocp_trim(200)
        self.set_invert_iq(0)
        self.reset_ptr_rx()
        self.set_fifo_rx_base_addr(0x00)
        # pi_log_v(self.__str__())

    def create_socket(self):
        self.ws = create_connection(self.SERVER_URL)
        pi_log_d("connect to server ok")
        self.send_to_socket(self.seqID)

    def close_socket(self):
        if(self.ws is not None):
            pi_log_d("close socket")
            self.ws.close()
    
    def send_to_socket(self, data):
        if(self.ws is not None):
            if(type(data) is str):
                tx = data
            elif(type(data) is int):
                tx = str(data)
            elif(type(data) is list):
                tx = '.'.join(str(e) for e in data)
            pi_log_v("Pi send server: ")
            pi_log_i(tx)
            self.ws.send(tx)

    def on_rx_done(self):
        print()
        pi_log_d ("---> RxDone")
        pi_log_d ("irq_flags: %s" % self.get_irq_flags())
        pi_log_d ("RSSI: %d - PKT_RSSI: %d" % (self.get_rssi_value(), self.get_pkt_rssi_value())) 
        self.rxMsg = self.read_payload(nocheck=True)# Receive INF
        if(self.get_irq_flags()['crc_error'] == 1):
            pi_log_e ("CRC failed -> msg discarded")
        else:
            pi_log_v ("LoRa receive: ")
            temp = self.list_to_dict(self.rxMsg)
            for key, value in temp.items():
                pi_log_i("%s : %s" % (key, value))
            self.send_to_socket(self.rxMsg)
        self.clear_irq_flags(RxDone = 1, PayloadCrcError = 1)
        self.reset_rx_ptr()

    def transmit(self, data):
        timeout = 1000
        pi_log_i('LoRa transmit:')
        pi_log_v(data)
        self.write_payload(data)
        self.set_mode(MODE.TX)
        pi_log_d('wait for tx_done')
        while (not lora.get_irq_flags()['tx_done']):
            timeout = timeout - 1
            if timeout == 0:
                pi_log_e('tx timeout')
                break
        if(timeout != 0):
            pi_log_i('send ok after ' + str(1000 - timeout))
        self.clear_irq_flags(TxDone = 1)
        self.set_mode(MODE.RXCONT) 

    def cmd_polling(self):
        self.seqID += 1

        nodeID = int(input("Enter node ID (decimal): "))
        cmd = int(input("Enter relay control (0:off - 1:on): "))
        
        self.txMsg[MSG.INDEX.SOURCE_ID]        = self.GATEWAY_ID
        self.txMsg[MSG.INDEX.DEST_ID]          = nodeID
        self.txMsg[MSG.INDEX.MSG_TYPE]         = MSG.HEADER.TYPE.REQUEST
        self.txMsg[MSG.INDEX.MSG_STATUS]       = MSG.HEADER.STATUS.NONE
        self.txMsg[MSG.INDEX.SEQUENCE_ID]      = self.seqID 
        self.txMsg[MSG.INDEX.DATA_LOCATION]    = MSG.DATA.LOCATION.UNKNOWN
        self.txMsg[MSG.INDEX.DATA_RELAY_STATE] = cmd
        self.txMsg[MSG.INDEX.DATA_ERR_CODE]    = MSG.DATA.ERR_CODE.NONE

        self.txMsg[MSG.INDEX.DATA_TIME_ALIVE]  = 0
        self.txMsg[MSG.INDEX.RESET_CAUSE]        = 0

        lora.transmit(self.txMsg)
        
    def reset_rx_ptr(self):
        pi_log_d('reset rxPtr to base value')
        self.set_mode(MODE.STDBY)
        self.set_mode(MODE.RXCONT)

    def list_to_dict(self, list_data):
        payload = {
            'INDEX_SOURCE_ID'       : list_data[MSG.INDEX.SOURCE_ID],
            'INDEX_DEST_ID'         : list_data[MSG.INDEX.DEST_ID],
            'INDEX_MSG_TYPE'        : MSG.HEADER.TYPE.lookup[list_data[MSG.INDEX.MSG_TYPE]],
            'INDEX_MSG_STATUS'      : MSG.HEADER.STATUS.lookup[list_data[MSG.INDEX.MSG_STATUS]],
            'INDEX_SEQUENCE_ID'     : list_data[MSG.INDEX.SEQUENCE_ID],
            'INDEX_DATA_LOCATION'   : MSG.DATA.LOCATION.lookup[list_data[MSG.INDEX.DATA_LOCATION]],
            'INDEX_DATA_RELAY_STATE': MSG.DATA.RELAY.lookup[list_data[MSG.INDEX.DATA_RELAY_STATE]],
            'INDEX_DATA_ERR_CODE'   : MSG.DATA.ERR_CODE.lookup[list_data[MSG.INDEX.DATA_ERR_CODE]],
            'INDEX_DATA_TIME_ALIVE' : 0,
            'RESET_CAUSE_2'         : MSG.DATA.RESET_CAUSE.lookup[list_data[MSG.INDEX.RESET_CAUSE]],
        } 
        # return dict(zip(payload, list_data))
        return payload
    
    def start(self):   
        self.create_socket()
        self.set_mode(MODE.RXCONT) 

        """ Start your code here """
        self.cmd_polling()
        

if __name__ == "__main__" :
    pi_log_d("LoRaGateWay Start")
    BOARD.setup()
    BOARD.reset()
    lora = mylora(verbose=False)

    txMsg = [None] * 10
    txMsg[MSG.INDEX.SOURCE_ID]        = MSG.NODE_ID.GATEWAY
    txMsg[MSG.INDEX.DEST_ID]          = MSG.NODE_ID.NODE_1
    txMsg[MSG.INDEX.MSG_TYPE]         = MSG.HEADER.TYPE.REQUEST
    txMsg[MSG.INDEX.MSG_STATUS]       = MSG.HEADER.STATUS.NONE
    txMsg[MSG.INDEX.SEQUENCE_ID]      = 0
    txMsg[MSG.INDEX.DATA_LOCATION]    = MSG.DATA.LOCATION.UNKNOWN
    txMsg[MSG.INDEX.DATA_RELAY_STATE] = MSG.DATA.RELAY.OFF
    txMsg[MSG.INDEX.DATA_ERR_CODE]    = MSG.DATA.ERR_CODE.NONE
    txMsg[MSG.INDEX.DATA_TIME_ALIVE]  = 0
    txMsg[MSG.INDEX.RESET_CAUSE]      = 0

    lora.start()
    while True:
        try:
            lora.start()
                    
        except KeyboardInterrupt:
            lora.close_socket()
            lora.set_mode(MODE.SLEEP)
            BOARD.teardown()

            pi_log_v("Exit")
            sys.exit()
        except ValueError:
            pi_log_e("This is not a valid number. It isn't a number at all! This is a string, go and try again. Better luck next time!")
        except Exception as e:
            pass
            # pi_log_e(e)
            