from flask import Blueprint, request
from google.cloud import datastore
import json
import constants

client = datastore.Client()

bp = Blueprint('loads', __name__, url_prefix='/loads')

@bp.route('/', methods=['POST','GET'])
def loads_get_post():
    if request.method == 'POST':
        content = request.get_json()
        new_load = datastore.entity.Entity(key=client.key(constants.loads))
        try:
            new_load.update({'weight': content['weight'], 'content': content['content'], 'delivery_date': content['delivery_date'], 'carrier': content['carrier']})
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(new_load)
        new_load["id"] = str(new_load.key.id)
        new_load["self"] = request.url + str(new_load.key.id)
        return (json.dumps(new_load), 201)
    elif request.method == 'GET':
        query = client.query(kind=constants.loads)
        q_limit = int(request.args.get('limit', '3'))
        q_offset = int(request.args.get('offset', '0'))
        l_iterator = query.fetch(limit= q_limit, offset=q_offset)
        pages = l_iterator.pages
        results = list(next(pages))
        if l_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None
        for e in results:
            e["id"] = e.key.id
            e["self"] = request.url
        output = {"loads": results}
        if next_url:
            output["next"] = next_url
        return json.dumps(output)
    else:
        return 'Method not recogonized'

@bp.route('/<id>', methods=['GET','PUT','DELETE'])
def loads_get_put_delete(id):
    if request.method == 'PUT':
        content = request.get_json()
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        load.update({"name": content["name"], "description": content["description"],
          "price": content["price"]})
        client.put(load)
        return ('',200)
    elif request.method == 'DELETE':
        key = client.key(constants.loads, int(id))
        load = client.get(key = key)
        if (load == None):
            response_body = {}
            response_body["Error"] = "No load with this load_id exists"
            return (json.dumps(response_body), 404)
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
            if not (e["loads"] == None):
                if (e["loads"] == load["id"]):
                    boat_key = client.key(constants.boats, e["id"])
                    boat = client.get(key=boat_key)
                    boat.update({"loads": None})
                    client.put(boat)
        client.delete(key)
        return ('',204)
    elif request.method == 'GET':
        content = request.get_json()
        load_key = client.key(constants.loads, int(id))
        load = client.get(key=load_key)
        if (load == None):
            response_data = {}
            response_data['Error'] = 'No load with this load_id exists'
            return (json.dumps(response_data), 404)
        load["id"] = load.key.id
        load["self"] = request.url
        return (json.dumps(load), 200)
    else:
        return 'Method not recogonized'

# @bp.route('/<lid>/boats/<bid>', methods=['PUT','DELETE'])
# def add_delete_load(lid,bid):
#     if request.method == 'PUT':
#         load_key = client.key(constants.loads, int(lid))
#         load = client.get(key=load_key)
#         boat_key = client.key(constants.boats, int(bid))
#         boat = client.get(key=boat_key)
#         if 'boats' in load.keys():
#             load['boats'].append(boat.id)
#         else:
#             load['boats'] = [boat.id]
#         client.put(load)
#         return('',200)
#     if request.method == 'DELETE':
#         load_key = client.key(constants.loads, int(lid))
#         load = client.get(key=load_key)
#         if 'boats' in load.keys():
#             load['boats'].remove(int(bid))
#             client.put(load)
#         return('',200)

# @bp.route('/<id>/boats', methods=['GET'])
# def get_loads(id):
#     load_key = client.key(constants.loads, int(id))
#     load = client.get(key=load_key)
#     load_list  = []
#     if 'boats' in load.keys():
#         for gid in load['boats']:
#             boat_key = client.key(constants.boats, int(bid))
#             load_list.append(boat_key)
#         return json.dumps(client.get_multi(load_list))
#     else:
#         return json.dumps([])
