#!/usr/bin/env python3
import aprslib
import json
import re
import time
import sys
import os
import threading
import subprocess
from datetime import datetime, timezone
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

my_position = '''4925.48S/06933.17EI'''
my_comment = '''APRSID BOT'''
bcnInterval = 300

def callback(packet):
    global callsign, ssid, aprs, my_position, my_comment, bcnInterval
    parsed_data = aprslib.parse(packet)
    print(parsed_data)
    if parsed_data:
        RAW = parsed_data['raw']
        FMT = parsed_data['format']
        SRC = parsed_data['from']
        DST = parsed_data['to']
        PATH = parsed_data['path']
        try:
             ADDRSE = parsed_data['addresse']
             MSG = parsed_data['message_text']
             MSGID = parsed_data['msgNo']
        except:
            ADDRSE = ''
            MSG = ''
            MSGID = ''
            #pass

        print("\nReceived Packet:")
        print("Source:", SRC)
        print("Destination:", DST)
        print("Path:", PATH)
        print("Addresse:", ADDRSE)
        print("Message:", MSG)
        print("Message number:", MSGID)
        if RAW and FMT != 'message':
            print("Raw:", RAW)
        print()

    if MSGID and SRC:
        ack = MSGID[0:]
        #print(ack)
        src = f"{SRC}".ljust(9)
        idxack = RAW.rfind("{")
        if idxack != -1:
            print("ACK: " + RAW[idxack+1:])
            ackd = RAW[idxack+1:]
            print("send ack to: " + src)
            aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":ack" + ackd)

    if re.search(r'^PING', MSG, flags=re.IGNORECASE) and SRC:
        src = f"{SRC}".ljust(9)
        print("PONG")
        time.sleep(1)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":PONG")

    if re.search(r'^HELP', MSG, flags=re.IGNORECASE) and SRC:
        src = f"{SRC}".ljust(9)
        print("valid cmd: PING HELP TIME VERSION GETEQ GETWX MSG FIND")
        time.sleep(1)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":=>valid cmd: PING HELP TIME VERSION GETEQ GETWX MSG FIND")
        time.sleep(2)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":=>MSG tocallsign text_messages(leave messages to callsign)")
        time.sleep(2)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":=>FIND just type FIND")

    if re.search(r'^TIME', MSG, flags=re.IGNORECASE) and SRC:
        src = f"{SRC}".ljust(9)
        print("bot time: " + dtime())
        time.sleep(1)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":bot time: " + dtime())

    if re.search(r'^VERSION', MSG, flags=re.IGNORECASE) and SRC:
        src = f"{SRC}".ljust(9)
        print("python version: " + str(sys.version).split()[0])
        time.sleep(1)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":python version: " + str(sys.version).split()[0])

    if re.search(r'^GETWX', MSG, flags=re.IGNORECASE) and SRC:
        src = f"{SRC}".ljust(9)
        with open("/home/hari/FT232H/bme280.txt", "r") as f:
            last_line = f.readlines()[-1]
            fields = last_line.split()
            lines = ' '.join(fields[2:10])
            temperature = float(fields[3][:5])
            humidity = float(fields[5][:5])
            pressure = float(fields[7][:7])
            altitude = float(fields[9][:4])
            s_wx = "Temp = " + str(temperature) + " deg.C, Hum = " + str(humidity) + " %, Pres = " + str(pressure) + " mbar, Alt = " + str(altitude) + " MSL"
        print(s_wx)
        time.sleep(1)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":bot telemetries: " + s_wx)

    if re.search(r'^GETEQ', MSG, flags=re.IGNORECASE) and SRC:
        src = f"{SRC}".ljust(9)
        req = Request(
            url='https://data.bmkg.go.id/DataMKG/TEWS/autogempa.xml',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        xmlfile = urlopen(req).read()
        root = ET.fromstring(xmlfile)

        for child in root.iter():
            if child.text:
                if child.tag == 'Tanggal':
                    TglVal = child.text
                elif child.tag == 'Jam':
                    JamVal = child.text
                elif child.tag == 'Lintang':
                    LinVal = child.text
                elif child.tag == 'Bujur':
                    BujVal = child.text
                elif child.tag == 'Magnitude':
                    MagVal = child.text
                elif child.tag == 'Kedalaman':
                    DepthVal = child.text
                elif child.tag == 'Wilayah':
                    WilVal = child.text
                elif child.tag == 'Potensi':
                    PotVal = child.text
                elif child.tag == 'Dirasakan':
                    DirVal = child.text

        s_eq = "Tgl = " + TglVal + ", Jam = " + JamVal + ", Lin = " + LinVal + ", Buj = "  + BujVal + ", Mag = " + MagVal + ", Depth = " + DepthVal

        print(s_eq + ", Wil = " + WilVal)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":BMKG: " + s_eq)
        time.sleep(3)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":BMKG: " + WilVal)
        urlopen(req).close()

    if re.search(r'^MSG ', MSG, flags=re.IGNORECASE) and SRC:
        src = f"{SRC}".ljust(9)
        result = []
        temp_string = ''
        file="/home/hari/aprsbot/test.json"

        msg_bot = MSG.split(' ')
        for item in msg_bot[1:]:
            if isinstance(item, str):
                temp_string += item + ' '
            else:
                if temp_string != '':
                    result.append(temp_string.strip())
                temp_string = ''

        # Check if there's still a pending string after the loop
        if temp_string != '':
            result.append(temp_string.strip())

        first_word = result[0].split()[0] 
        sender = SRC.strip().upper()
        recipient = str(msg_bot[1]).strip().upper()
        messages = ' '.join(word for word in result[0].split() if word != first_word)

        write_json_data(file, sender.upper(), recipient.upper(), messages)

        print("Sender=" + sender + ", Recipient=" + recipient + ", Message=" + messages)
        time.sleep(1)
        aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":Sender=" + sender + ", Recipient=" + recipient + ", Message=" + messages )

    if re.search(r'^FIND', MSG, flags=re.IGNORECASE) and SRC:
        src = f"{SRC}".ljust(9)
        file = "/home/hari/aprsbot/test.json"
        stored_data = read_json_data(file)
        search_recipient = SRC.strip()
        matching_items = search_by_recipient(stored_data, search_recipient.upper())

        if matching_items:
            print("Matching items:")
            for item in matching_items[-5:]:
                print("Timestamps:", item.get("timestamps")[1:-2], end=", ")
                print("Sender:", item.get("sender"), end=", ")
                print("Recipient:", item.get("recipient"))
                messages_str = ''.join(item.get("messages", []))
                print("Messages:", messages_str,end="")
                print()

                s_find = "Timestamps:" + item.get("timestamps")[1:-2] + ", Sender:" +  str(item.get("sender").strip()).upper() + ", Messages:" + messages_str.strip()

                time.sleep(3)
                aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":your messages: " + s_find )
        else:
            print(f"No items found with the keyword '{search_sender}'.")
            s_find = f"No items found with the keyword '{search_sender}'."
            time.sleep(1)
            aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ": " + s_find )

    if re.search(r'^MOTD', MSG, flags=re.IGNORECASE) and SRC:
        script = '/home/hari/aprsbot/quote.sh'
        try:
            output = subprocess.check_output(script, stderr=subprocess.STDOUT, universal_newlines=True)
            print(output.strip())
            print(len(output.strip()))
            if len(output.strip()) > 150:
                midpoint = len(output.strip()) // 2
                # Split the string into two parts
                var1 = output[:midpoint]
                var2 = output[midpoint:]
                aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":" + var1)
                time.sleep(3)
                aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":" + var2)
            else:
                aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":" + output.strip())
        except subprocess.CalledProcessError as e:
            print("Error running Perl script:")
            print(e.output)
            aprs.sendall(callsign + ">APRS,TCPIP*::" + src + ":sorry, no quotes this time" )

def dtime():
    now = datetime.now()
    s1 = now.strftime("%m/%d/%Y, %H:%M:%S")
    return ("[" + str(s1) + "] ")

def write_json_data(filename, sender, recipient, messages):
    # Load the current ID from the ID file
    try:
        with open("/home/hari/aprsbot/id.txt", "r") as id_file:
            content = id_file.read().strip()
            current_id = int(content) if content.isdigit() else 1
    except FileNotFoundError:
        # If the ID file doesn't exist, start with ID 1
        current_id = 1

    # Create a dictionary with labeled arguments
    data = {
        'id': current_id,
        'timestamps': dtime(),
        'sender': sender,
        'recipient': recipient,
        'messages': messages
    }

    # Read the existing content of the JSON file
    try:
        with open(filename, 'r') as json_file:
            existing_content = json_file.read().strip()

        # Try to parse the existing content as a JSON array
        existing_data = json.loads(existing_content)
        if not isinstance(existing_data, list):
            raise ValueError("Existing content is not a JSON array.")

    except (FileNotFoundError, ValueError):
        # If the file doesn't exist or the content is not a JSON array, start with an empty array
        existing_data = []

    # Add the new object to the array
    existing_data.append(data)

    # Write the modified content (JSON array) to the JSON file
    with open(filename, 'w') as json_file:
        json.dump(existing_data, json_file, indent=2)

    # Update the ID in the ID file
    with open("/home/hari/aprsbot/id.txt", "w") as id_file:
        id_file.write(str(current_id + 1))


def read_json_data(filename):
    try:
        with open(filename, 'r') as json_file:
            data = json.load(json_file)
            return data
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return []

def search_by_recipient(data, recipient):
    matching_items = []

    for item in data:
        if 'recipient' in item and item['recipient'] == recipient:
            matching_items.append(item)

    return matching_items

def writePidFile():
    pid = str(os.getpid())
    f = open('/tmp/aprsbot_pid', 'w')
    f.write(pid)
    f.close()

def aprs_ts():
    # Get the current UTC time
    utc_now = datetime.utcnow()

    # Format the timestamp in APRS format (YYMMDDhhmmss)
    aprs_timestamp = utc_now.strftime("%d%H%M")

    return aprs_timestamp + "z"  # Use only the first 6 characters and append 'Z'

def sendbcn():
    global callsign, ssid, aprs, my_position, my_comment, bcnInterval
    old_t=time.time()
    while True:
        if time.time()-old_t > bcnInterval:
            s_strpos = "@" + aprs_ts() + my_position + my_comment
            print("\nsend position: " + s_strpos + "\n")
            aprs.sendall(callsign + ">APRS,TCPIP*:" + s_strpos)
            old_t=time.time()
        time.sleep(1)

# Set up your APRS credentials
callsign = 'APRSID'
aprspass = '10661'
ssid = 0  # SSID (Secondary Station ID)

# Connect to the APRS-IS network as a listener
aprs = aprslib.IS(callsign, passwd=aprspass, host="t2kk.kutukupret.com", port=14580, skip_login=False)

# Start the connection
aprs.connect()

def main():
    # packet = aprs.consumer(callback, raw=True)
    #aprs.consumer(callback, raw=True)
    # writepid
    writePidFile()
    # thread
    threadbcn = threading.Thread(target=sendbcn)
    threadbcn.daemon = True
    threadbcn.start()
    aprs.consumer(callback, raw=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        #Statements to execute upon that exception
        print("Stopped")

