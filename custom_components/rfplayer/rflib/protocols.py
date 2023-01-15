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

def RTS_decode(data:list,message:list,node) -> list:
    """
    RTS uses Infotypes 3
    """
    if protocols_debug: log.debug("Decode RTS")
    if protocols_debug: log.debug("data:%s",str(data))
    if protocols_debug: log.debug("message:%s",str(message))
    decoded_items = cast(PacketType, {"node": node})
    #decoded_items["protocol"]=data["protocol"]
    decoded_items.append(header_decode(message['header']))
    decoded_items.append(globals()["_".join(["infotype",data["infoType"],"decode"])](message['infos']))
    #decoding=alldecode(message)
    #for element,value in decoding:
    #    log.debug("%s = %s", str(element),str(value))
        #decoded_items[element]=value
    match decoded_items["subtype"]:
        case "SHUTTER":
            decoded_items["platform"] = "cover"
            value="shu"
        case "PORTAL":
            value="por"
            decoded_items["platform"] = "cover"
        case _:
            value=""
    decoded_items[decoded_items["platform"]] = value
    return decoded_items

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
    for element,value in decoding.items():
        decoded_items[element]=value
    
    return decoded_items
