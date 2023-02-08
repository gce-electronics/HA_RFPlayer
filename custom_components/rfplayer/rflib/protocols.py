import logging
from .infotypes import *
from typing import Any, Callable, Dict, Generator, cast
import json

#Debogage des protocoles
protocols_debug=False

PacketType = Dict[str, Any]

log = logging.getLogger(__name__)

def alldecode(message:list) -> list:
    if protocols_debug: log.debug("Decode all")
    fields_found = []
    
    
    if type(message).__name__ in ('dict'):
        elements=message.items()
    else:
        elements=message

    log.debug("Avant for : %s",str(elements))
    for element in elements:
        if protocols_debug: log.debug("Dans for - Type %s",type(element).__name__)
        match type(element).__name__:
            case 'dict'|'tuple':
                if protocols_debug: log.debug("Sous-Structure element")
                fields_found.append(alldecode(element))
            case 'list':
                for subelement, value in element:
                    if protocols_debug: log.debug("Element %s = %s", str(subelement),str(value))
                    fields_found.append({subelement:value})
            case _:
                if len(element)>1:
                    if protocols_debug: log.debug("Element %s = %s", str(element[0]),str(element[1]))
                    fields_found.append({element[0]:element[1]})
                else :
                    log.debug("Element non géré %s",str(element))
                
            
    
    return fields_found

def header_decode(header:dict):
    if protocols_debug: log.debug("Decode Header: Type=%s , datas=%s",type(header).__name__,str(header))
    headers_found = {}
    elements=['frameType','cluster','dataFlag','rfLevel','floorNoise','rfQuality','infoType','frequency']
    """
    frameType			0 : Regular Decoder, 1 : RF Frames
	cluster				Reserved
	dataFlag			0 : 433 Mhz, 1 : 868 Mhz
	rfLevel				Signal Level : Affaiblissement en dB (-40=Haut, -110=Faible)
	floorNoise			Signal Level : Affaiblissement en dB (-40=Haut, -110=Faible)
	rfQuality			Signal Quality note over 10
	protocol			Protocol Number
	protocolMeaning		Protocol Name
	infoType			Data Structure
	frequency			Reception Frequency
    """
    for element in elements:
        headers_found[element]= header.get(element)
    headers_found['protocol']=header.get('protocolMeaning')
    return headers_found

#X10 : Infotypes : 0,1
def X10_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode X10")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items

    #log.warn('Shadow Message, no id found !')

#VISONIC : Infotypes : 2
def VISONIC_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode VISONIC")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"
            #decoding['sensor']=decoding["qualifier"]
            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

#X10 : Infotypes : 0,1
def BLYSS_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode BLYSS")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def CHACON_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode CHACON")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def OREGON_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode OREGON")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def DOMIA_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode DOMIA")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def OWL_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode OWL")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def X2D_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode X2D")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if protocols_debug: log.debug("decoding:%s",str(decoding))
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def RTS_decode(data:list,message:list,node) -> list:
    """
    RTS uses Infotypes 3
    """
    if protocols_debug: log.debug("Decode RTS")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])

    if decoding != None:
        if len(decoding)>0:
            match decoding["subType"]:
                case "Shutter":
                    decoding["platform"] = "cover"
                case "Portal":
                    decoding["platform"] = "cover"

            decoding['cover']=decoding["qualifier"]

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no address found !')

def KD101_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode KD101")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def PARROT_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode PARROT")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def TIC_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode TIC")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def FS20_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode FS20")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def JAMMING_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode JAMMING")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')

def EDISIO_decode(data:list,message:list,node) -> list:
    if protocols_debug: log.debug("Decode EDISIO")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    decoding=header_decode(message['header'])
    if protocols_debug: log.debug("decoding: datas=%s",str(decoding))
    for element,value in decoding.items():
        decoded_items[element]=value
    decoding=globals()["_".join(["infoType",decoded_items["infoType"],"decode"])](message['infos'])
    if decoding != None:
        if len(decoding)>0:
            decoding["platform"] = "sensor"

            for element,value in decoding.items():
                decoded_items[element]=value
            
            return decoded_items
    
    #log.warn('Shadow Message, no id found !')