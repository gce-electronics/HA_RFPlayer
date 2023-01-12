import logging

log = logging.getLogger(__name__)

id_PHY_OREGON = {
    0x0 : "OREGONV1",
    0x1A2D : "THGR228",
    0xCA2C : "THGR328",
    0x0ACC : "RTGR328",
    0xEA4C : "THWR288",
    0x1A3D : "THGR918",
    0x5A6D : "THGR918N",
    0x1A89 : "WGR800",
    0xCA48 : "THWR800",
    0xFA28 : "THGR810",
    0x2A19 : "PCR800",
    0xDA78 : "UVN800",
}

def infoType_0_decode(message:list) -> list:
    log.debug("Decode InfoType 0")
    fields_found = []
    match message["subtype"]:
        case 0 :
            fields_found["subtype"]="OFF"
        case 1 :
            fields_found["subtype"]="ON"
        case 2 :
            fields_found["subtype"]="BRIGHT"
        case 3 :
            fields_found["subtype"]="DIM"
        case 4 :
            fields_found["subtype"]="ALL_OFF"
        case 5 :
            fields_found["subtype"]="ALL_ON"
    fields_found["id"]=message["id"]
    return fields_found

def infoType_1_decode(message:list) -> list:
    log.debug("Decode InfoType 1")
    fields_found = []
    match message["subtype"]:
        case 0 :
            fields_found["subtype"]="OFF"
        case 1 :
            fields_found["subtype"]="ON"
        case 4 :
            fields_found["subtype"]="ALL_OFF"
        case 5 :
            fields_found["subtype"]="ALL_ON"
    #fields_found["id_lsb"]=message["id_lsb"]
    #fields_found["id_msb"]=message["id_msb"]
    #fields_found["id"]=message["id_lsb"]+(message["id_lsb"] << 8)
    fields_found["id"]=message["id"]
    return fields_found

def infoType_2_decode(message:list) -> list:
    log.debug("Decode InfoType 2")
    fields_found = []
    binQualifier=bin(message["qualifier"])
    match message["subtype"]:
        case 0 :
            fields_found["subtype"]="SENSOR"
            fields_found["Tamper"]=int(binQualifier[-1])
            fields_found["Alarm"]=int(binQualifier[-2])
            fields_found["LowBatt"]=int(binQualifier[-3])
            fields_found["Supervisor"]=int(binQualifier[-4])
        case 1 :
            fields_found["subtype"]="REMOTE"
            fields_found["button1"]=int(binQualifier)==0x08
            fields_found["button2"]=int(binQualifier)==0x10
            fields_found["button3"]=int(binQualifier)==0x20
            fields_found["button4"]=int(binQualifier)==0x40
    fields_found["id"]=message["id"]
    return fields_found

def infoType_3_decode(message:list) -> list:
    log.debug("Decode InfoType 3")
    fields_found = []
    match message["subtype"]:
        case 0 :
            fields_found["subtype"]="SHUTTER"
        case 1 : 
            fields_found["subtype"]="PORTAL"
    match message["qualifier"]:
        case 1 :
            fields_found["qualifier"]="OFF"
        case 4 : 
            fields_found["qualifier"]="MY"
        case 7 : 
            fields_found["qualifier"]="ON"
        case 13 : 
            fields_found["qualifier"]="ASSOC"
        case 5 : 
            fields_found["qualifier"]="LBUTTON"
        case 6 : 
            fields_found["qualifier"]="RBUTTON"

    fields_found["id"]=message["id"]
    return fields_found

def infoType_4_decode(message:list) -> list:
    log.debug("Decode InfoType 3")
    fields_found = []
    match message["subtype"]:
        case 0 :
            fields_found["subtype"]="SENSOR"
    fields_found["id_PHY"]= lambda x:id_PHY_OREGON.get(int(message["id_PHY"]),int(message["id_PHY"]))
    """
    match int(message["id_PHY"]):
        case 0x0 :
            fields_found["id_PHY"]="OREGONV1"
        case 0x1A2D :
            fields_found["id_PHY"]="THGR228"
        case 0xCA2C :
            fields_found["id_PHY"]="THGR328"
        case 0x0ACC :
            fields_found["id_PHY"]="RTGR328"
        case 0xEA4C :
            fields_found["id_PHY"]="THWR288"
        case 0x1A3D :
            fields_found["id_PHY"]="THGR918"
        case 0x5A6D :
            fields_found["id_PHY"]="THGR918N"
        case 0x1A89 :
            fields_found["id_PHY"]="WGR800"
        case 0xCA48 :
            fields_found["id_PHY"]="THWR800"
        case 0xFA28 :
            fields_found["id_PHY"]="THGR810"
        case 0x2A19 :
            fields_found["id_PHY"]="PCR800"
        case 0xDA78 :
            fields_found["id_PHY"]="UVN800"
    """
    fields_found["adr_channel"]=message["adr_channel"]
    match message["qualifier"]:
        case 1 :
            fields_found["qualifier"]="OFF"
        case 4 : 
            fields_found["qualifier"]="MY"
        case 7 : 
            fields_found["qualifier"]="ON"
        case 13 : 
            fields_found["qualifier"]="ASSOC"
        case 5 : 
            fields_found["qualifier"]="LBUTTON"
        case 6 : 
            fields_found["qualifier"]="RBUTTON"

    fields_found["id"]=message["id"]
    return fields_found
    
def infoType_5_decode(message:list) -> list:
    log.debug("Decode InfoType 3")
    fields_found = []
    match message["subtype"]:
        case 0 :
            fields_found["subtype"]="SENSOR"
    fields_found["id_PHY"]= lambda x:id_PHY_OREGON.get(int(message["id_PHY"]),int(message["id_PHY"]))
    match message["qualifier"]:
        case 1 :
            fields_found["qualifier"]="OFF"
        case 4 : 
            fields_found["qualifier"]="MY"
        case 7 : 
            fields_found["qualifier"]="ON"
        case 13 : 
            fields_found["qualifier"]="ASSOC"
        case 5 : 
            fields_found["qualifier"]="LBUTTON"
        case 6 : 
            fields_found["qualifier"]="RBUTTON"

    fields_found["id"]=message["id"]
    return fields_found