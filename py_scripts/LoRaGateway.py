import os
import time
from myModules.data_format import *
from myModules.colors import *

from SX127x.LoRa import *
from SX127x.board_config import BOARD
import random
import requests
from websocket import create_connection
import websocket
import threading
import json
import queue

# SERVER_URL = 'ws://localhost:3000/'
SERVER_URL = 'wss://datn-loraserver.herokuapp.com/pi'
GATEWAY_ID = MSG.NODE_ID.GATEWAY


def get_thread_count():
    pi_log_d('current active thread %d' % threading.active_count())


def thread_ping(*args):
    """[summary]
        Periodicly ping server
    """
    i = 0
    time.sleep(1)
    while True:
        time.sleep(10)
        try:
            i = i + 1
            # pi_log_v('ping server')
            args[0].send("ping %d" % i)
        except Exception as e:
            pi_log_e('thread_ping')
            pi_log_e(e)
    pi_log_v("thread_ping terminating...")


def thread_reconnect(*args):
    """[summary]
        Try to reconnect to ws if lost connection
    """
    i = 0
    while True:
        time.sleep(1)
        try:
            i += 1
            pi_log_v('reconnecting[%d]' % i)
            args[0].run_forever()
        except Exception as e:
            pi_log_e('reconnect failed[%d]' % i)
            pi_log_e(e)
    pi_log_v("thread_reconnect terminating...")


class mylora(LoRa):
    seqID = 1

    def __init__(self, verbose=False, do_calibration=False, calibration_freq=434):
        pi_log_v('start lora config')
        super(mylora, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_freq(433)
        self.set_pa_config(pa_select=1, max_power=21, output_power=15)

        self.set_preamble(0x20)
        # self.set_bw(BW.BW500)
        self.set_bw(BW.BW62_5)
        self.set_spreading_factor(12)
        self.set_coding_rate(CODING_RATE.CR4_5)

        self.set_low_data_rate_optim(1)
        self.set_pa_ramp(0x08)
        # self.set_sync_word(0x34)

        self.set_payload_length(10)
        self.set_rx_crc(True)
        self.set_lna_gain(GAIN.G1)
        self.set_implicit_header_mode(True)
        self.set_mode(MODE.STDBY)
        self.set_pa_config(pa_select=1)
        self.set_pa_config(pa_select=1, max_power=None, output_power=15)
        self.set_dio_mapping([0] * 6)
        self.set_pa_dac(True)
        self.set_ocp_trim(200)
        self.set_invert_iq(0)
        self.reset_ptr_rx()
        self.set_fifo_rx_base_addr(0x00)
        pi_log_v(self.__str__())

    ''' ANCHOR: Got socket message '''
    def on_message(self, ws, stringifyJson):
        # if msg.find('pong') > -1:
        #     pass
        # else:
        msg = json.loads(stringifyJson.decode('utf-8'))
        pi_log_v('on_sock_msg')
        pi_log_v(msg)
        loraMsg = [None] * 10
        loraMsg = REQUEST_PROTOTYPE
        loraMsg[MSG.INDEX.HEADER_DEST_ID] = int(msg['nodeID'])
        loraMsg[MSG.INDEX.COMMAND_OPCODE] = int(msg['opcode'])
        # loraMsg[MSG.INDEX.HEADER_SEQUENCE_ID] = int(msg['sequenceID'])
        # if msg['status'].upper() == 'ON':
        loraMsg[MSG.INDEX.DATA_RELAY_STATE] = MSG.DATA.RELAY.ON if msg['status'].upper() == 'ON' else MSG.DATA.RELAY.OFF
        loraMsg[MSG.INDEX.HEADER_TIME_TO_LIVE] = 0
        # elif msg['status'].upper() == 'OFF':
        #     loraMsg[MSG.INDEX.DATA_RELAY_STATE] = MSG.DATA.RELAY.OFF
        self.transmit(loraMsg)

    def on_error(self, ws, error):
        pi_log_e('on_sock_error')
        pi_log_e(error)

    def on_close(self, ws):
        pi_log_v("on_sock_close")

    def on_open(self, ws):
        pi_log_v('on_sock_open')
        pi_log_i('connected to server successfully')

    def create_socket(self, pingPeriod=5):
        pi_log_v('create websocket')
        self.ws = websocket.WebSocketApp(SERVER_URL,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        thread_1 = threading.Thread(target=thread_ping, args={self.ws})
        thread_1.start()
        thread_2 = threading.Thread(target=thread_reconnect, args={self.ws})
        thread_2.start()

    def send_socket(self, raw_msg):
        try:
            tx = self.msg_to_list(raw_msg)
            tx = '.'.join(str(e) for e in tx)
            pi_log_v("Pi send server: ")
            pi_log_i(tx)
            isSent = False
            while not isSent:
                self.ws.send(tx)
                isSent = True
        except Exception as e:
            pi_log_e(e)
            pi_log_e('send socket failed')
            time.sleep(1)

    ''' ANCHOR Got LoRa message '''
    def on_rx_done(self):

        rxMsg = [None] * 10
        
        pi_log_v("---> RxDone")
        # pi_log_d("irq_flags: %s" % self.get_irq_flags())
        pi_log_v("RSSI: %d - PKT_RSSI: %d" % (self.get_rssi_value(), self.get_pkt_rssi_value()))
        rxMsg = self.read_payload(nocheck=True) 
        
        if(self.get_irq_flags()['crc_error'] == 1):
            pi_log_e("CRC failed -> msg discarded")
        else:
            pi_log_v("LoRa receive: ")
            pi_log_i(rxMsg)
            self.send_socket(rxMsg)

        self.clear_irq_flags(RxDone=1, PayloadCrcError=1)
        self.reset_rx_ptr()

    def transmit(self, raw_msg):
        self.seqID += 1
        raw_msg[MSG.INDEX.HEADER_SEQUENCE_ID] = self.seqID

        # pi_log_i(self.list_to_dict(self.msg_to_list(raw_msg)))
        pi_log_v('LoRa transmit:')
        pi_log_i(raw_msg)

        self.write_payload(raw_msg)
        self.set_mode(MODE.TX)

        TIMEOUT_DURATION = 1000000000
        timeout = TIMEOUT_DURATION
        pi_log_v('wait for tx_done')
        while (not lora.get_irq_flags()['tx_done']):
            timeout = timeout - 1
            if timeout == 0:
                pi_log_e('tx timeout')
                break
        if(timeout != 0):
            pi_log_i('send ok after ' + str(TIMEOUT_DURATION - timeout))
        self.clear_irq_flags(TxDone=1)
        time.sleep(0.1)
        self.set_mode(MODE.RXCONT)

    def cmd_polling(self):
        def thread_polling(*args):
            txMsg = [None] * 10
            while True:
                time.sleep(1)
                try:
                    txMsg[MSG.INDEX.HEADER_SOURCE_ID] = GATEWAY_ID
                    txMsg[MSG.INDEX.HEADER_MSG_TYPE] = MSG.HEADER.TYPE.REQUEST
                    txMsg[MSG.INDEX.HEADER_MSG_STATUS] = MSG.HEADER.STATUS.NONE
                    txMsg[MSG.INDEX.DATA_ERR_CODE] = MSG.DATA.ERR_CODE.NONE
                    txMsg[MSG.INDEX.DATA_LOCATION] = MSG.DATA.LOCATION.UNKNOWN
                    txMsg[MSG.INDEX.DATA_RELAY_STATE] = MSG.DATA.RELAY.NONE

                    txMsg[MSG.INDEX.HEADER_DEST_ID] = int(
                        input("Enter node ID (18, 19, 20): \n"))

                    opcode = int(input(
                        "Enter opcode (notif: 1 - relay control: 2 - mcu reset: 3 - location update: 4 - update friend ID: 5): \n"))
                    txMsg[MSG.INDEX.COMMAND_OPCODE] = opcode
                    if opcode == MSG.COMMAND.OPCODE.REQUEST_RELAY_CONTROL:
                        txMsg[MSG.INDEX.DATA_RELAY_STATE] = int(
                            input("Enter relay control (0:off - 1:on): \n"))
                    elif opcode == MSG.COMMAND.OPCODE.REQUEST_LOCATION_UPDATE:
                        txMsg[MSG.INDEX.DATA_LOCATION] = int(
                            input("Enter new location: \n"))
                    elif opcode == MSG.COMMAND.OPCODE.REQUEST_FRIEND_NODE_ID_UPDATE:
                        txMsg[MSG.INDEX.DATA_FRIEND_NODE_ID] = int(
                            input("Enter new friend ID: \n"))
                    else:
                        pass

                    ttl = int(input("Enter msg ttl (0-20): \n"))
                    txMsg[MSG.INDEX.HEADER_TIME_TO_LIVE] = ttl

                    lora.transmit(txMsg)
                except Exception as e:
                    pi_log_e('thread_polling')
                    pi_log_e(e)
            pi_log_v("thread_polling terminating...")
        thread_3 = threading.Thread(target=thread_polling)
        thread_3.start()

    def msg_to_list(self, raw_msg):
        payload = [
            raw_msg[MSG.INDEX.HEADER_SOURCE_ID],
            raw_msg[MSG.INDEX.HEADER_DEST_ID],
            raw_msg[MSG.INDEX.HEADER_MSG_TYPE],
            # raw_msg[MSG.INDEX.HEADER_MSG_STATUS],
            raw_msg[MSG.INDEX.HEADER_MSG_STATUS],
            raw_msg[MSG.INDEX.HEADER_SEQUENCE_ID],
            MSG.DATA.LOCATION.lookup[raw_msg[MSG.INDEX.DATA_LOCATION]],
            MSG.DATA.RELAY.lookup[raw_msg[MSG.INDEX.DATA_RELAY_STATE]],
            MSG.DATA.ERR_CODE.lookup[raw_msg[MSG.INDEX.DATA_ERR_CODE]],
            raw_msg[MSG.INDEX.COMMAND_OPCODE],
            raw_msg[MSG.INDEX.RESET_CAUSE],
            # MSG.DATA.RESET_CAUSE.lookup[raw_msg[MSG.INDEX.RESET_CAUSE]],
        ]
        pi_log_v(payload)
        return payload

    def list_to_dict(self, raw_msg):
        try:
            payload = {
                'SOURCE_ID': raw_msg[MSG.INDEX.HEADER_SOURCE_ID],
                'DEST_ID': raw_msg[MSG.INDEX.HEADER_DEST_ID],
                'MSG_TYPE': MSG.HEADER.TYPE.lookup[raw_msg[MSG.INDEX.HEADER_MSG_TYPE]],
                'MSG_STATUS': MSG.HEADER.STATUS.lookup[raw_msg[MSG.INDEX.HEADER_MSG_STATUS]],
                'SEQUENCE_ID': raw_msg[MSG.INDEX.HEADER_SEQUENCE_ID],
                'DATA_LOCATION': MSG.DATA.LOCATION.lookup[raw_msg[MSG.INDEX.DATA_LOCATION]],
                'DATA_RELAY_STATE': MSG.DATA.RELAY.lookup[raw_msg[MSG.INDEX.DATA_RELAY_STATE]],
                'DATA_ERR_CODE': MSG.DATA.ERR_CODE.lookup[raw_msg[MSG.INDEX.DATA_ERR_CODE]],
                'COMMAND_OPCODE': MSG.COMMAND.OPCODE.lookup[raw_msg[MSG.INDEX.COMMAND_OPCODE]],
                'RESET_CAUSE_2': MSG.DATA.RESET_CAUSE.lookup[raw_msg[MSG.INDEX.RESET_CAUSE]],
            }
            pi_log_i(payload)
            return payload
        except Exception as e:
            pi_log_e('convert to dict failed')
            pi_log_e(e)
        # return dict(zip(payload, raw_msg))

    def start(self):
        self.create_socket()
        self.set_mode(MODE.RXCONT)
        """ Start your code here """
        self.cmd_polling()


if __name__ == "__main__":
    pi_log_v("LoRaGateWay Start")
    BOARD.setup()
    BOARD.reset()
    lora = mylora(verbose=False)
    lora.start()
    get_thread_count()
    while True:
        try:
            pass
        except KeyboardInterrupt:
            lora.set_mode(MODE.SLEEP)
            BOARD.teardown()
            pi_log_v("Exit")
            sys.exit()
        except ValueError:
            pi_log_e(
                "This is not a valid number. It isn't a number at all! This is a string, go and try again. Better luck next time!")
        except Exception as e:
            pi_log_e(e)
