import time
import json
import threading
import os
import shutil
import http.client as http

from flask import Flask, jsonify

#The variables to save and lock the data

json_file = "./data.json"
json_lock = "/tmp/json_lock"
template = "./templates/pag.html"

#constants for connecting to the server
ADDR = "192.168.20.218"
PORT = 80
TIMEOUT = 10

app = Flask(__name__)

@app.route("/data")
def data():
    """data
    returns the data for the charts
    """
    while os.path.isfile(json_lock):
        time.sleep(1/10)
    with open(json_file, 'r') as file:
        data = json.loads(file.read())
    return jsonify(data)

@app.route("/")
def main():
    """main
    returns the webpage
    """
    global template
    with open(template, 'r') as file:
        data = file.read()
    return data

class DataGetter(threading.Thread):
    """DataGetter
    thread to save the data into a json file to read it afterwards
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop = threading.Event()

    @classmethod
    def __request(cls, method="GET",
                 urlattr="", body="",
                 headers={}):
        """_request

        bootsraper for the request method of the HTTPConnection from the
        standard library http.client
        """

        # Create the connection
        conn = http.HTTPConnection(
            ADDR,
            port=PORT,
            timeout=TIMEOUT)

        # Make the request
        try:
            conn.request(method, ADDR,
                         body=body, headers=headers)

        except socket.timeout as exc:
            # If the connection times out raise timeout TimeoutError
            raise TimeoutError(
                "The server {ip}:{port} is not responding".format(
                    ip=ADDR, 
                    port=PORT)) from exc
        except ConnectionRefusedError:
            # if the connection is refused try again
            conn.close()
            conn = http.HTTPConnection(ADDR, port=PORT, timeout=TIMEOUT)
            try:
                conn.request(method, ADDR,
                             body=body, headers=headers)
            except ConnectionRefusedError as cre:
                # If it falils again raise a socket.error
                raise NotAHTTPServerError(
                    "A host was found but is not responding to the \
                     HTTP requests") from cre

        response = conn.getresponse()
        if response.status == 404:
            raise NotFoundError(
                "The url with the requested attributes could not be found")

        conn.close()  # Close the connection
        return response  # return response

    def run(self):
        while not self.stop.is_set():

            #read and load the data from the server
            data = json.loads(self.__request().read())
            data["hour"] = time.time()

            #create the lockfile to lock the file while 
            #modifing it
            open(json_lock, 'a').close()
            #backup the file just in case
            shutil.copyfile(json_file, json_file+"-backup")

            #load the data
            with open(json_file) as file:
                db = json.loads(file.read())

            #add the new data
            db.append(data)

            #save the updated file
            with open(json_file, "w") as file:
                file.write(json.dumps(db))

            #remove the lock
            os.remove(json_lock)

            #wait 1 second
            time.sleep(1)


class NotFoundError(Exception):
    pass

class TimeoutError(Exception):
    pass

class NotAHTTPServerError(Exception):
    pass



#If the data file doen't exist create it
if not os.path.isfile(json_file):
    with open(json_file, 'a') as f:
        f.write("[]")

#create and run the data getter thread
getter = DataGetter(name="Getter")
getter.daemon=True
getter.start()

