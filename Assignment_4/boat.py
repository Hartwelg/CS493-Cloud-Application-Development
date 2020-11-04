from flask import Blueprint, request
from google.cloud import datastore
import json
import constants

client = datastore.Client()

bp = Blueprint('boats', __name__, url_prefix='/boats')

@bp.route('/', methods=['POST','GET'])
def boats_get_post():
    if request.method == 'POST':
        content = request.get_json()
        new_boat = datastore.entity.Entity(key=client.key(constants.boats))
        try:
            new_boat.update({"name": content["name"], "type": content["type"], "length": content["length"], "loads": content["loads"]})
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(new_boat)
        new_boat["id"] = str(new_boat.key.id)
        new_boat["self"] = request.url + str(new_boat.key.id)
        return (json.dumps(new_boat), 201)
    elif request.method == 'GET':
        query = client.query(kind=constants.boats)
        q_limit = int(request.args.get('limit', '3'))
        q_offset = int(request.args.get('offset', '0'))
        g_iterator = query.fetch(limit= q_limit, offset=q_offset)
        pages = g_iterator.pages
        results = list(next(pages))
        if g_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None
        for e in results:
            e["id"] = e.key.id
            e["self"] = request.url
        output = {"boats": results}
        if next_url:
            output["next"] = next_url
        return json.dumps(output)

@bp.route('/<id>', methods=['GET','PUT','DELETE'])
def boats_get_put_delete(id):
    if request.method == 'PUT':
        content = request.get_json()
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        boat.update({"name": content["name"], "type": content["type"], "length": content["length"], "loads": content["loads"]})
        client.put(boat)
        return ('',200)
    elif request.method == 'DELETE':
        key = client.key(constants.boats, int(id))
        boat = client.get(key = key)
        if (boat == None):
            response_body = {}
            response_body["Error"] = "No boat with this boat_id exists"
            return (json.dumps(response_body), 404)
        boat["id"] = str(boat.key.id)
        query = client.query(kind=constants.loads)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
            if (e["carrier"] != None and e["carrier"]["id"] == boat["id"]):
                load_key = client.key(constants.loads, e["id"])
                load = client.get(key=load_key)
                load.update({"carrier": None})
                client.put(load)
        client.delete(key)
        return ('',204)
    elif request.method == 'GET':
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
    else:
        return 'Method not recogonized'

@bp.route('/<bid>/loads/', methods=['GET'])
def get_loads_for_boat(bid):
    content = request.get_json()
    boat_key = client.key(constants.boats, int(bid))
    boat = client.get(key=boat_key)
    if (boat == None):
        response_data = {}
        response_data['Error'] = 'No boat with this boat_id exists'
        return (json.dumps(response_data), 404)
    boat["id"] = boat.key.id
    boat["self"] = request.url
    load_list = []
    if 'loads' in boat.keys():
        for lid in boat["loads"]:
            load_key = client.key(constants.loads, int(lid["id"]))
            load_list.append(load_key)
        return json.dumps(client.get_multi(load_list))
    return (json.dumps([]), 200)

@bp.route('/<bid>/loads/<lid>', methods=['PUT','DELETE'])
def add_delete_load_to_boat(bid, lid):
    if request.method == 'PUT':
        content = request.get_json()
        load_key = client.key(constants.loads, int(lid))
        boat_key = client.key(constants.boats, int(bid))
        load = client.get(key=load_key)
        boat = client.get(key=boat_key)
        if (boat == None or load == None):
            response_body = {}
            response_body["Error"] = "The specified boat and/or load does not exist"
            return (json.dumps(response_body), 404)
        boat["id"] = str(boat.key.id)
        boat["self"] = request.url
        load["id"] = str(load.key.id)
        load["self"] = request.url
        for lid in boat["loads"]:
            if (lid["id"] == load["id"]):
                response_body = {}
                response_body["Error"] = "The load is already on the boat"
                return (json.dumps(response_body), 403)
        load_carrier = {}
        load_carrier["id"] = str(boat["id"])
        load_carrier["name"] = boat["name"]
        load_carrier["self"] = request.url_root + "boats/" + boat["id"]
        load.update({"carrier": load_carrier})
        # load.update({"carrier": boat})
        carried_load = {}
        carried_load["id"] = str(load["id"])
        carried_load["self"] = request.url_root + "loads/" + load["id"]
        boat["loads"].append(carried_load)
        # boat["loads"].append(load["id"])
        client.put(load)
        client.put(boat)
        return ('', 204)
    elif request.method == 'DELETE':        
        load_key = client.key(constants.loads, int(lid))
        boat_key = client.key(constants.boats, int(bid))
        load = client.get(key=load_key)
        boat = client.get(key=boat_key)
        try:
            boat["id"] = str(boat.key.id)
            load["id"] = str(load.key.id)
        except AttributeError:
            response_body = {}
            response_body["Error"] = "No load with this load_id is on the boat with this boat_id"
            return (json.dumps(response_body), 404)
        if (boat == None or load == None or load["carrier"] == None or load["carrier"]["id"] != boat["id"]):
            response_body = {}
            response_body["Error"] = "No load with this load_id is on the boat with this boat_id"
            return (json.dumps(response_body), 404)
        if (load["carrier"]["id"] == boat["id"]):
            load.update({"carrier": None})
        for e in boat["loads"]:
            if (e["id"] == load["id"]):
                boat["loads"].remove(e)
        client.put(boat)
        client.put(load)
        return ('', 204)
    else:
        return 'Method not recognized'