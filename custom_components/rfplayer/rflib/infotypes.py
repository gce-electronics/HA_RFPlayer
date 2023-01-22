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

def check_bitL2R(byte, bit):
    return bool(byte & (0b10000000>>bit))

def check_bitR2L(byte, bit):
    return bool(byte & (0b1<<bit))

def infoType_0_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 0")
    fields_found = {}
    match infos["subtype"]:
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
    fields_found["id"]=infos["id"]

    if fields_found["id"]!="0":
        return fields_found

def infoType_1_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 1")
    fields_found = {}
    match infos["subtype"]:
        case 0 :
            fields_found["subtype"]="OFF"
        case 1 :
            fields_found["subtype"]="ON"
        case 4 :
            fields_found["subtype"]="ALL_OFF"
        case 5 :
            fields_found["subtype"]="ALL_ON"

    fields_found["id"]=infos["id"]

    if fields_found["id"]!="0":
        return fields_found

def infoType_2_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 2")
    fields_found = {}
    binQualifier=int(infos["qualifier"])
    match infos["subtype"]:
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
    fields_found["id"]=infos["id"]

    if fields_found["id"]!="0":
        return fields_found

def infoType_3_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 3")
    fields_found = {}
    fields_found["subType"]=infos["subTypeMeaning"]
    match int(infos["qualifier"]):
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

    fields_found["id"]=infos["id"]

    if fields_found["id"]!="0":
        return fields_found

def infoType_4_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 4")
    fields_found = {}
    
    fields_found["subType"]=infos.get("subTypeMeaning")
    if fields_found["subType"] == None : fields_found["subType"]=infos.get("subType")
    fields_found["id_PHY"]= infos["id_PHYMeaning"]
    fields_found["adr_channel"]=infos["adr_channel"]
    fields_found["qualifier"]=infos["qualifier"]
    fields_found["lowBatt"]=infos["lowBatt"]

    match int(infos["qualifier"])>>4:
        case 1 :
            fields_found["oreg_protocol"]="V1"
        case 2 : 
            fields_found["oreg_protocol"]="V2"
        case 3 : 
            fields_found["oreg_protocol"]="V3"
    elements={'temperature':'°C','hygrometry':'%'}
    for measure in infos["measures"]:
        if measure['type'] in elements:
            fields_found[measure['type']]= measure['value']
            fields_found[measure['type']+'_unit']= elements[measure['type']]

    fields_found["id"]=infos["adr_channel"]
    
    if fields_found["id"]!="0":
        return fields_found
    
def infoType_5_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 5")
    fields_found = {}
    
    fields_found["subType"]=infos.get("subTypeMeaning")
    if fields_found["subType"] == None : fields_found["subType"]=infos.get("subType")
    fields_found["id_PHY"]= infos["id_PHYMeaning"]
    fields_found["adr_channel"]=infos["adr_channel"]
    fields_found["qualifier"]=infos["qualifier"]
    fields_found["lowBatt"]=infos["lowBatt"]

    match int(infos["qualifier"])>>4:
        case 1 :
            fields_found["oreg_protocol"]="V1"
        case 2 : 
            fields_found["oreg_protocol"]="V2"
        case 3 : 
            fields_found["oreg_protocol"]="V3"
    elements={'temperature':'°C','hygrometry':'%','pressure':'hPa'}
    for measure in infos["measures"]:
        if measure['type'] in elements:
            fields_found[measure['type']]= measure['value']
            fields_found[measure['type']+'_unit']= elements[measure['type']]

    fields_found["id"]=infos["adr_channel"]
    
    if fields_found["id"]!="0":
        return fields_found

def infoType_6_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 6")
    fields_found = {}
    
    fields_found["subType"]=infos.get("subTypeMeaning")
    if fields_found["subType"] == None : fields_found["subType"]=infos.get("subType")
    fields_found["id_PHY"]= infos["id_PHYMeaning"]
    fields_found["adr_channel"]=infos["adr_channel"]
    fields_found["qualifier"]=infos["qualifier"]
    fields_found["lowBatt"]=infos["lowBatt"]
    
    match int(infos["qualifier"])>>4:
        case 1 :
            fields_found["oreg_protocol"]="V1"
        case 2 : 
            fields_found["oreg_protocol"]="V2"
        case 3 : 
            fields_found["oreg_protocol"]="V3"
    elements={'speed':'m/s','direction':'°'}
    for measure in infos["measures"]:
        if measure['type'] in elements:
            fields_found[measure['type']]= measure['value']
            fields_found[measure['type']+'_unit']= elements[measure['type']]

    fields_found["id"]=infos["adr_channel"]
    
    if fields_found["id"]!="0":
        return fields_found

def infoType_7_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 7")
    fields_found = {}
    
    fields_found["subType"]=infos.get("subTypeMeaning")
    if fields_found["subType"] == None : fields_found["subType"]=infos.get("subType")
    fields_found["id_PHY"]= infos["id_PHYMeaning"]
    fields_found["adr_channel"]=infos["adr_channel"]
    fields_found["qualifier"]=infos["qualifier"]
    fields_found["lowBatt"]=infos["lowBatt"]
    
    match int(infos["qualifier"])>>4:
        case 1 :
            fields_found["oreg_protocol"]="V1"
        case 2 : 
            fields_found["oreg_protocol"]="V2"
        case 3 : 
            fields_found["oreg_protocol"]="V3"
    elements={'UV':'UV index'}
    for measure in infos["measures"]:
        if measure['type'] in elements:
            fields_found[measure['type']]= measure['value']
            fields_found[measure['type']+'_unit']= elements[measure['type']]

    fields_found["id"]=infos["adr_channel"]
    
    if fields_found["id"]!="0":
        return fields_found

def infoType_8_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 7")
    fields_found = {}
    
    fields_found["subType"]=infos.get("subTypeMeaning")
    if fields_found["subType"] == None : fields_found["subType"]=infos.get("subType")
    fields_found["id_PHY"]= infos["id_PHYMeaning"]
    fields_found["adr_channel"]=infos["adr_channel"]
    fields_found["qualifier"]=infos["qualifier"]
    fields_found["lowBatt"]=infos["lowBatt"]
    
    match int(infos["qualifier"])>>1:
        case 0 :
            fields_found["measurement"]="General"
        case 1 : 
            fields_found["oreg_protocol"]="Detailed"

    elements={'Power':'W','P1':'W','P2':'W','P3':'W'}
    for measure in infos["measures"]:
        if measure['type'] in elements:
            fields_found[measure['type']]= measure['value']
            fields_found[measure['type']+'_unit']= elements[measure['type']]

    fields_found["id"]=infos["adr_channel"]
    
    if fields_found["id"]!="0":
        return fields_found

def infoType_9_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 9")
    fields_found = {}
    
    fields_found["subType"]=infos.get("subTypeMeaning")
    if fields_found["subType"] == None : fields_found["subType"]=infos.get("subType")
    fields_found["id_PHY"]= infos["id_PHYMeaning"]
    fields_found["id_channel"]=infos["id_channel"]
    fields_found["qualifier"]=infos["qualifier"]
    fields_found["lowBatt"]=infos["lowBatt"]
    
    match int(infos["qualifier"])>>4:
        case 1 :
            fields_found["oreg_protocol"]="V1"
        case 2 : 
            fields_found["oreg_protocol"]="V2"
        case 3 : 
            fields_found["oreg_protocol"]="V3"
    elements={'TotalRain':'mm','Rain':'mm'}
    for measure in infos["measures"]:
        if measure['type'] in elements:
            fields_found[measure['type']]= measure['value']
            fields_found[measure['type']+'_unit']= elements[measure['type']]

    fields_found["id"]=infos["id_channel"]
    
    if fields_found["id"]!="0":
        return fields_found

def infoType_10_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 10")
    fields_found = {}
    
    fields_found["subType"]=infos.get("subTypeMeaning")
    if fields_found["subType"] == None : fields_found["subType"]=infos.get("subType")
    fields_found["qualifier"]=infos["qualifier"]
   
    elements={'functionMeaning':'','stateMeaning':'','modeMeaning':'','d0':'','d1':'','d2':'','d3':''}
    for measure,value in infos:
        if measure in elements:
            fields_found[measure] = value
            fields_found[measure+'_unit']= elements[measure]

    fields_found["id"]=infos["id"]
    
    if fields_found["id"]!="0":
        return fields_found

def infoType_11_decode(infos:list) -> list:
    if infotypes_debug: log.debug("Decode InfoType 11")
    fields_found = {}
    
    fields_found["subType"]=infos.get("subTypeMeaning")
    if fields_found["subType"] == None : fields_found["subType"]=infos.get("subType")
    fields_found["qualifier"]=infos["qualifier"]

    elements={'functionMeaning':'','stateMeaning':'','modeMeaning':'','d0':'','d1':'','d2':'','d3':''}
    for measure,value in infos:
        if measure in elements:
            fields_found[measure] = value
            fields_found[measure+'_unit']= elements[measure]

    if 'flags' in infos['qualifierMeaning']:
        for flag in infos['qualifierMeaning']['flags']:
            fields_found[flag]=1

    fields_found["id"]=infos["id"]
    
    if fields_found["id"]!="0":
        return fields_found

