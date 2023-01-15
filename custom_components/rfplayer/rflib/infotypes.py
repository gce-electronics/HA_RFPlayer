import logging

#Debogage des infotypes
infotypes_debug=False

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

def infoType_0_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 0")
    fields_found = {}
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

def infoType_1_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 1")
    fields_found = {}
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

def infoType_2_decode(infos:list) -> list:
    if infotypes_debug: og.debug("Decode InfoType 2")
    fields_found = {}
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

def infoType_3_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 3")
    fields_found = {}
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

def infoType_4_decode(infos:list) -> list:
    #OK - 15/01/2023
    if infotypes_debug: log.debug("Decode InfoType 4 : %s",str(infos))
    fields_found = {}
    match infos.get("subType"):
        case 0 :
            fields_found["subType"]="SENSOR"
    fields_found["id_PHY"]= infos["id_PHYMeaning"]
    
    fields_found["adr_channel"]=infos["adr_channel"]
    fields_found["qualifier"]=infos["qualifier"]
    match int(infos["qualifier"])>>4:
        case 1 :
            fields_found["oreg_protocol"]="V1"
        case 2 : 
            fields_found["oreg_protocol"]="V2"
        case 3 : 
            fields_found["oreg_protocol"]="V3"
    elements=['temperature','hygrometry']
    for measure in infos["measures"]:
        if measure['type'] in elements:
            fields_found[measure['type']]= measure['value']
        


    fields_found["id"]=infos["adr_channel"]
    fields_found["platform"] = "sensor"

    if fields_found["adr_channel"]!="0":
        return fields_found
    
def infoType_5_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 3")
    fields_found = {}
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