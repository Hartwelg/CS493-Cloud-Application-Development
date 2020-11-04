from flask import Blueprint, request
from google.cloud import datastore
import json
import constants

client = datastore.Client()

bp = Blueprint('lodging', __name__, url_prefix='/lodgings')

@bp.route('', methods=['POST','GET'])
def lodgings_get_post():
    if request.method == 'POST':
        content = request.get_json()
        new_lodging = datastore.entity.Entity(key=client.key(constants.lodgings))
        new_lodging.update({'name': content['name'], 'description': content['description'],
          'price': content['price']})
        client.put(new_lodging)
        return str(new_lodging.key.id)
    elif request.method == 'GET':
        query = client.query(kind=constants.lodgings)
        q_limit = int(request.args.get('limit', '2'))
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
        output = {"lodgings": results}
        if next_url:
            output["next"] = next_url
        return json.dumps(output)
    else:
        return 'Method not recogonized'

@bp.route('/<id>', methods=['PUT','DELETE'])
def lodgings_put_delete(id):
    if request.method == 'PUT':
        content = request.get_json()
        lodging_key = client.key(constants.lodgings, int(id))
        lodging = client.get(key=lodging_key)
        lodging.update({"name": content["name"], "description": content["description"],
          "price": content["price"]})
        client.put(lodging)
        return ('',200)
    elif request.method == 'DELETE':
        key = client.key(constants.lodgings, int(id))
        client.delete(key)
        return ('',200)
    else:
        return 'Method not recogonized'

@bp.route('/<lid>/guests/<gid>', methods=['PUT','DELETE'])
def add_delete_reservation(lid,gid):
    if request.method == 'PUT':
        lodging_key = client.key(constants.lodgings, int(lid))
        lodging = client.get(key=lodging_key)
        guest_key = client.key(constants.guests, int(gid))
        guest = client.get(key=guest_key)
        if 'guests' in lodging.keys():
            lodging['guests'].append(guest.id)
        else:
            lodging['guests'] = [guest.id]
        client.put(lodging)
        return('',200)
    if request.method == 'DELETE':
        lodging_key = client.key(constants.lodgings, int(lid))
        lodging = client.get(key=lodging_key)
        if 'guests' in lodging.keys():
            lodging['guests'].remove(int(gid))
            client.put(lodging)
        return('',200)

@bp.route('/<id>/guests', methods=['GET'])
def get_reservations(id):
    lodging_key = client.key(constants.lodgings, int(id))
    lodging = client.get(key=lodging_key)
    guest_list  = []
    if 'guests' in lodging.keys():
        for gid in lodging['guests']:
            guest_key = client.key(constants.guests, int(gid))
            guest_list.append(guest_key)
        return json.dumps(client.get_multi(guest_list))
    else:
        return json.dumps([])
