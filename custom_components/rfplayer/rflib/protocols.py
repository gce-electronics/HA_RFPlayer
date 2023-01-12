import logging
from .infotypes import *
from typing import Any, Callable, Dict, Generator, cast
import json

PacketType = Dict[str, Any]

log = logging.getLogger(__name__)

def alldecode(message:list) -> list:
    log.debug("Decode all")
    fields_found = []
    
    
    if type(message).__name__ in ('dict'):
        elements=message.items()
    else:
        elements=message

    log.debug("Avant for : %s",str(elements))
    for element, value in elements:
        log.debug("Dans for - Type %s",type(value).__name__)
        if type(value).__name__ in ('dict','list'):
            log.debug("Sous-Structure")
            fields_found.append(alldecode(value))
        else:
            log.debug("Element %s = %s", str(element),str(value))
            fields_found.append({element:value})
    
    return fields_found

def RTS_decode(data:list,message:list,node) -> list:
    """
    RTS uses Infotypes 3
    """
    log.debug("Decode RTS")
    decoded_items = cast(PacketType, {"node": node})
    decoded_items["protocol"]=data["protocol"]
    #decoded_items.append(globals()["_".join("infotype",[data["infoType"],"decode"])](message))
    decoding=alldecode(message)
    for element,value in decoding:
        log.debug("%s = %s", str(element),str(value))
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
    log.debug("Decode RTS")
    decoded_items = cast(PacketType, {"node": node})
    decoded_items["protocol"]=data["protocol"]
    #decoded_items.append(globals()["_".join("infotype",[data["infoType"],"decode"])](message))
    decoding=alldecode(message)
    for element,value in decoding:
        log.debug("%s = %s", str(element),str(value))
        #decoded_items[element]=value

    return decoded_items
