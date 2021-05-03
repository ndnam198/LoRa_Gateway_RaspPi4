""" Define LoRa msg constants """


def add_lookup(cls):
    """ A decorator that adds a lookup dictionary to the class.
        The lookup dictionary maps the codes back to the names. This is used for pretty-printing. """
    varnames = filter(str.isupper, cls.__dict__.keys())
    lookup = dict(map(lambda varname: (
        cls.__dict__.get(varname, None), varname), varnames))
    setattr(cls, 'lookup', lookup)
    return cls


@add_lookup
class MSG:

    @add_lookup
    class INDEX:
        HEADER_SOURCE_ID = 0
        HEADER_DEST_ID = 1
        HEADER_MSG_TYPE = 2
        HEADER_MSG_STATUS = 3
        HEADER_SEQUENCE_ID = 4
        DATA_LOCATION = 5
        DATA_RELAY_STATE = 6
        DATA_ERR_CODE = 7
        COMMAND_OPCODE = 8
        RESET_CAUSE = 9
        MAX = 10

    @add_lookup
    class NODE_ID:
        GATEWAY = 0xFF
        NODE_1 = 0x12
        NODE_2 = 0x13
        NODE_3 = 0x14
        NODE_4 = 0x15

    @add_lookup
    class HEADER:

        @add_lookup
        class TYPE:
            REQUEST = 0
            RESPONSE = 1
            NOTIF = 2

        @add_lookup
        class STATUS:
            NONE = 0
            OK = 1
            FAILED = 2

        @add_lookup
        class ACK:
            NO_ACK = 0
            NACK = 1
            ACK = 2

    @add_lookup
    class DATA:

        @add_lookup
        class RELAY:
            OFF = 0
            ON = 1
            NONE = 2

        @add_lookup
        class LOCATION:
            UNKNOWN = 0
            GIAI_PHONG_1 = 1
            GIAI_PHONG_2 = 2
            GIAI_PHONG_3 = 3
            GIAI_PHONG_4 = 4
            GIAI_PHONG_5 = 5
            GIAI_PHONG_6 = 6
            GIAI_PHONG_7 = 7
            GIAI_PHONG_8 = 8
            GIAI_PHONG_9 = 9
            GIAI_PHONG_10 = 10

        @add_lookup
        class ERR_CODE:
            NONE = 0
            LIGHT_ON_FAILED = 1
            LIGHT_OFF_FAILED = 2

        @add_lookup
        class RESET_CAUSE:
            UNKNOWN = 0
            LOW_POWER_RESET = 1
            WINDOW_WATCHDOG_RESET = 2
            INDEPENDENT_WATCHDOG_RESET = 3
            SOFTWARE_RESET = 4
            POWER_ON_POWER_DOWN_RESET = 5
            EXTERNAL_RESET_PIN_RESET = 6
            BROWNOUT_RESET = 7

    @add_lookup
    class COMMAND:

        @add_lookup
        class OPCODE:
            OPCODE_NONE = 0
            REQUEST_STATE = 1
            RESPOSNE_STATE = REQUEST_STATE + 100
            REQUEST_RELAY_CONTROL = 2
            RESPOSNE_RELAY_CONTROL = REQUEST_RELAY_CONTROL + 100
            REQUEST_MCU_RESET = 3
            RESPOSNE_MCU_RESET = REQUEST_MCU_RESET + 100
            REQUEST_LOCATION_UPDATE = 4
            RESPOSNE_LOCATION_UPDATE = REQUEST_LOCATION_UPDATE + 100

REQUEST_PROTOTYPE = [
    MSG.NODE_ID.GATEWAY,
    0,
    MSG.HEADER.TYPE.REQUEST,
    MSG.HEADER.STATUS.NONE,
    0,
    0,
    0,
    MSG.DATA.ERR_CODE.NONE,
    MSG.COMMAND.OPCODE.OPCODE_NONE,
    MSG.DATA.RESET_CAUSE.UNKNOWN
]
