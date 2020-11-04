from google.cloud import datastore
from flask import Flask, request
import json
import constants

app = Flask(__name__)
client = datastore.Client()

@app.route('/')
def index():
    return "Please navigate to /boats to use this API"

@app.route('/boats', methods=['POST','GET'])
def boats_get_post():
    if request.method == 'POST':
        content = request.get_json()
        new_boat = datastore.entity.Entity(key=client.key(constants.boats))
        try:
            new_boat.update({"name": content["name"], "type": content["type"], "length": content["length"]})
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(new_boat)
        new_boat["id"] = str(new_boat.key.id)
        new_boat["self"] = request.url + '/' + str(new_boat.key.id)
        return (json.dumps(new_boat), 201)
    elif request.method == 'GET':
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
        return json.dumps(results)
    else:
        return 'Method not recogonized'

@app.route('/boats/<id>', methods=['GET', 'PATCH'])
def boat_get_patch(id):
    if request.method == 'GET':
        content = request.get_json()
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        if (boat == None):
            response_data = {}
            response_data['Error'] = 'No boat with this boat_id exists'
            return (json.dumps(response_data), 404)
        boat["id"] = boat.key.id
        boat["self"] = request.url
        return (json.dumps(boat), 200)
    elif request.method == 'PATCH':
        content = request.get_json()
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        if (boat == None):
            response_data = {}
            response_data['Error'] = 'No boat with this boat_id exists'
            return (json.dumps(response_data), 404)
        try:
            boat.update({"name": content["name"], "type": content["type"], "length": content["length"]})
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(boat)
        boat["id"] = str(boat.key.id)
        boat["self"] = request.url
        return (json.dumps(boat), 200)
    else:
        return 'Method not recognized'

@app.route('/slips', methods=['POST','GET'])
def slips_get_post():
    if request.method == 'POST':
        content = request.get_json()
        new_slip = datastore.entity.Entity(key=client.key(constants.slips))
        try:
            new_slip.update({"number": content["number"], "current_boat": None})
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing the required number"
            return (json.dumps(response_body), 400)
        client.put(new_slip)
        new_slip["id"] = str(new_slip.key.id)
        new_slip["self"] = request.url + '/' + str(new_slip.key.id)
        return (json.dumps(new_slip), 201)
    elif request.method == 'GET':
        query = client.query(kind=constants.slips)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
        return json.dumps(results)
    else:
        return 'Method not recogonized'

@app.route('/slips/<id>', methods=['GET', 'PATCH'])
def slip_get_patch(id):
    if request.method == 'GET':
        content = request.get_json()
        slip_key = client.key(constants.slips, int(id))
        slip = client.get(key=slip_key)
        if (slip == None):
            response_data = {}
            response_data['Error'] = "No slip with this slip_id exists"
            return (json.dumps(response_data), 404)
        slip["id"] = slip.key.id
        slip["self"] = request.url
        return (json.dumps(slip), 200)
    elif request.method == 'PATCH':
        content = request.get_json()
        slip_key = client.key(constants.slips, int(id))
        slip = client.get(key=slip_key)
        slip.update({"number": content["number"]})
        client.put(slip)
        slip["id"] = str(slip["current_boat"].key.id)
        slip["self"] = request.url
        return (json.dumps(slip), 200)
    else:
        return 'Method not recognized'

@app.route('/boats/<id>', methods=['PUT','DELETE'])
def boats_put_delete(id):
    if request.method == 'PUT':
        content = request.get_json()
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        boat.update({"name": content["name"], "description": content["description"],
          "price": content["price"]})
        client.put(boat)
        return ('',200)
    elif request.method == 'DELETE':
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key = boat_key)
        if (boat == None):
            response_body = {}
            response_body['Error'] = "No boat with this boat_id exists"
            return (json.dumps(response_body), 404)
        boat["id"] = str(boat.key.id)
        query = client.query(kind=constants.slips)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
            if not (e["current_boat"] == None):
                if (e["current_boat"] == boat["id"]):
                    slip_key = client.key(constants.slips, e["id"])
                    slip = client.get(key=slip_key)
                    slip.update({"current_boat": None})
                    client.put(slip)
        client.delete(boat_key)
        return ('',204)
    else:
        return 'Method not recogonized'

@app.route('/slips/<id>', methods=['PUT','DELETE'])
def slips_put_delete(id):
    if request.method == 'PUT':
        content = request.get_json()
        slip_key = client.key(constants.slips, int(id))
        slip = client.get(key=slip_key)
        slip.update({"number": content["number"]})
        client.put(slip)
        return ('',200)
    elif request.method == 'DELETE':
        key = client.key(constants.slips, int(id))
        slip = client.get(key = key)
        if (slip == None):
            response_body = {}
            response_body["Error"] = "No slip with this slip_id exists"
            return (json.dumps(response_body), 404)
        client.delete(key)
        return ('',204)
    else:
        return 'Method not recogonized'

@app.route('/slips/<slip_id>/<boat_id>', methods=['PUT', 'DELETE'])
def add_boat_to_slip(slip_id, boat_id):
    if request.method == 'PUT':
        content = request.get_json()
        slip_key = client.key(constants.slips, int(slip_id))
        boat_key = client.key(constants.boats, int(boat_id))
        slip = client.get(key=slip_key)
        boat = client.get(key=boat_key)
        if (boat == None or slip == None):
            response_body = {}
            response_body["Error"] = "The specified boat and/or slip does not exist"
            return (json.dumps(response_body), 404)
        if not (slip["current_boat"] == None):
            response_body = {}
            response_body["Error"] = "The slip is not empty"
            return (json.dumps(response_body), 403)
        boat["id"] = str(boat.key.id)
        slip.update({"current_boat": boat["id"]})
        client.put(slip)
        return ('', 204)
    elif request.method == 'DELETE':        
        slip_key = client.key(constants.slips, int(slip_id))
        boat_key = client.key(constants.boats, int(boat_id))
        slip = client.get(key=slip_key)
        boat = client.get(key=boat_key)
        try:
            boat["id"] = str(boat.key.id)
        except AttributeError:
            response_body = {}
            response_body["Error"] = "No boat with this boat_id is at the slip with this slip_id"
            return (json.dumps(response_body), 404)
        if (boat == None or slip == None or slip["current_boat"] != boat["id"]):
            response_body = {}
            response_body["Error"] = "No boat with this boat_id is at the slip with this slip_id"
            return (json.dumps(response_body), 404)
        if not (slip["current_boat"] == None):
            slip.update({"current_boat": None})
        client.put(slip)
        return ('', 204)
    else:
        return 'Method not recognized'

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)