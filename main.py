import os
import sys
import requests
import json
import hashlib
import configparser
from inventree.api import InvenTreeAPI
from inventree.part import Part
from inventree.stock import StockItem, StockLocation
from PIL import Image, ImageDraw, ImageFont

tagdict = {} # machash: (mac, hwtype)
hwtypedict = {} # hwtype: (width, height)
stocklocation = {} # pk: (barcode_hash, name, description)


config = configparser.ConfigParser()
config.read("config.ini")

def getConfig(key, section='DEFAULT'):
    # Check if the environment variable is set
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value
    # If not set, return the value from the config file
    return config.get(section, key)

api = InvenTreeAPI(getConfig("INVENTREEURL"), token=getConfig("INVENTREETOKEN"))

def getTagdata():
    # Get the tagdb.json from the AP and extract the macs and hwTypes, then calculate the machash
    tagdb = requests.get("http://" + getConfig("ACCESSPOINTIP") + "/current/tagDB.json")
    hwtypeset = set()
    for tag in tagdb.json():
        match tag:
            case [{"mac": str() as mac, "hwType": int() as hwtype}]:
                if hwtype >= 224:
                    continue
                machash = hashlib.md5(mac[4:].encode('utf-8')).hexdigest()
                tagdict[machash] = (mac[4:], hwtype)
                hwtypeset.add(hwtype)
    # with the set of hwtypes we get the hardware json files from the AP for the resolution data
    for hwtype in hwtypeset:
        hwfilename = str("%0.2X" % hwtype) + ".json"
        typejson = requests.get("http://" + getConfig("ACCESSPOINTIP") + "/tagtypes/" + hwfilename)
        match typejson.json():
            case {"width": int() as width, "height": int() as height}:
                hwtypedict[hwtype] = (width, height)

def getStock(location): # returns the stock of a defined location in the scheme name: quantity
    stockdict = {}
    for stock in StockItem.list(api, location=location):
        name = Part(api, stock["part"])["name"]
        stockdict[name] = int(stock["quantity"])
    # print(stockdict)
    return stockdict
    
def getLocations():
    locations = StockLocation.list(api)
    for location in locations:
        if location["barcode_hash"] == "" or location["barcode_hash"] not in tagdict:
            continue
        stocklocation[location["pk"]] = (location["barcode_hash"], location["name"], location["description"])

def fakeprint():
    # let's get all the data per screen together first
    for location in stocklocation:
        print("Content of Screen \"" + tagdict[stocklocation[location][0]][0] + "\":")
        print("----------------------")
        print(stocklocation[location][2])
        stock = getStock(location)
        for part in stock:
            print(str(stock[part]) + " | " + str(part))
        print(stocklocation[location][1])
        print("----------------------")

def textShortener(draw, displaywidth, text, font):
    textbounds = draw.textbbox((0, 0), text, font=font)
    textlength = len(text)
    trailingdot = ""
    while textbounds[2] >= displaywidth - 35:
        textlength -= 1
        textbounds = draw.textbbox((0, 0), text[:textlength], font=font)
        trailingdot = "."
    return text[:textlength] + trailingdot

def displayUpload():
    for locpk in stocklocation:
        mac = tagdict[stocklocation[locpk][0]][0]
        hwtype = tagdict[stocklocation[locpk][0]][1]
        tagwidth = hwtypedict[hwtype][1]    #technically height, but the image gets rotated
        tagheight = hwtypedict[hwtype][0]   #technically width, but the image gets rotated
        taglocation = stocklocation[locpk][1]
        tagtitle = stocklocation[locpk][2]
        imagepath = "./current/" + mac + ".jpg"
        payload = {"dither": 0, "mac": mac}
        url = "http://" + getConfig("ACCESSPOINTIP") + "/imgupload"
        maxlines = (tagheight - (30 + 16)) // 16
        print("Generating image for tag " + mac + " at position " + taglocation)
        image = Image.new('P', (tagwidth, tagheight))
        palette = [
            255, 255, 255,
            0, 0, 0,
            255, 0, 0
        ]
        image.putpalette(palette)
        draw = ImageDraw.Draw(image)
        # Define the fonts and sizes, shall be changed based on text length later
        font_title = ImageFont.truetype(getConfig("TITLEFONT"), size=int(getConfig("TITLEFONTSIZE")))  
        font_location = ImageFont.truetype(getConfig("LOCATIONFONT"), size=int(getConfig("LOCATIONFONTSIZE")))  
        font_inventory = ImageFont.truetype(getConfig("INVENTORYFONT"), size=int(getConfig("INVENTORYFONTSIZE")))

        text_bbox_title = draw.textbbox((0, 0), tagtitle, font=font_title)
        text_bbox_location = draw.textbbox((0, 0), taglocation, font=font_location)
        text_position_title = ((image.width - (text_bbox_title[2] - text_bbox_title[0])) // 2, int(getConfig("TITLEPOSITION")))
        text_position_location = ((image.width - (text_bbox_location[2] - text_bbox_location[0])) // 2, image.height - 18 + int(getConfig("LOCATIONPOSITION")))
        # Base draw functions
        draw.rectangle([(0, 0), (image.width - 1, 30)], fill=2, outline=1, width=1)
        draw.rectangle([(0, image.height - 16), (image.width - 1, image.height - 1)], fill=2, width=1)
        draw.text(text_position_title, tagtitle, fill=0, font=font_title)  
        draw.text(text_position_location, taglocation, fill=0, font=font_location)  
        draw.line(((28, 30),(28, image.height - 16)), fill=1, width=1)
        # Inventory draw function with height and length cutoff
        heightpos = 32
        stock = getStock(locpk)
        stocklength = len(stock)
        for part in stock:
            if heightpos >= image.height - 47 and stocklength >= 2:
                draw.text((30, heightpos), "and more...", fill=2, font=font_inventory)
                break
            else:
                draw.text((1, heightpos), str(stock[part]), fill=2, font=font_inventory)
                draw.text((30, heightpos), textShortener(draw, tagwidth, str(part), font_inventory), fill=1, font=font_inventory)
                heightpos = heightpos + 16
                stocklength -= 1
        
        rotated_image = image.rotate(270, expand=True)
        rgb_image = rotated_image.convert('RGB')
        print("Exporting image to " + imagepath)
        rgb_image.save(imagepath, 'JPEG', quality="maximum")
        if getConfig("SKIPUPLOAD") == "False" or getConfig("SKIPUPLOAD") == "false":
            print("Uploading to " + url)
            files = {"file": open(imagepath, "rb")}
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print("Image uploaded successfully to " + mac)
            else:
                print("Failed to upload the image.")

getTagdata()
getLocations()
displayUpload()