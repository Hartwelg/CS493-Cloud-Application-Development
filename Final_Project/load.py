from flask import Flask, Blueprint, request, make_response
from google.cloud import datastore
import json
import constants

client = datastore.Client()

bp = Blueprint('loads', __name__, url_prefix='/loads')

@bp.route('/', methods=['POST','GET', 'PUT', 'DELETE'])
def loads_get_post():
    #endpoint to add a load to the system
    if request.method == 'POST':
        #get content from the request
        content = request.get_json()
        #make a new load fpr datastore
        new_load = datastore.entity.Entity(key=client.key(constants.loads))
        #add request data to the new load
        try:
            new_load.update({'weight': content['weight'], 'content': content['content'], 'delivery_date': content['delivery_date'], 'carrier': content['carrier']})
        #if there is a KeyError (missing data in request), return 400
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        #put the new_load into datastore
        client.put(new_load)
        #set the 'id' field of the load
        new_load["id"] = str(new_load.key.id)
        #set the 'self field of the load
        new_load["self"] = request.url + str(new_load.key.id)
        #return the load data to the user with 201 status code
        return (json.dumps(new_load), 201)
    #endpoint to list loads in the system
    elif request.method == 'GET':
        #query the loads table for all loads in the system
        query = client.query(kind=constants.loads)
        #limit results per page to 5
        q_limit = int(request.args.get('limit', '5'))
        #initialize offset
        q_offset = int(request.args.get('offset', '0'))
        #keeps track of where we are in the results
        l_iterator = query.fetch(limit= q_limit, offset=q_offset)
        #keeps track of how many pages of results there are
        pages = l_iterator.pages
        #holds a list of the actual results
        results = list(next(pages))
        #if there is a next page, set the offset to the next result after the end of the current page
        if l_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        #if no more results, 'next' is not set
        else:
            next_url = None
        #for each result, set 'id' and 'self' attributes
        for e in results:
            e["id"] = e.key.id
            e["self"] = request.url
        #put 'loads' at the beginning of the results, then return the results
        output = {"loads": results}
        #if there is a 'next' url, put it at the end of the results
        if next_url:
            output["next"] = next_url
        #return the results
        return (json.dumps(output), 200)
    #PUT and DELETE methods not used here, so return 405
    elif request.method == 'PUT' or request.method == 'DELETE':
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set('Content-Type', 'applicaton/json')
        return res
    #no other methods used here
    else:
        return 'Method not recogonized'

@bp.route('/<id>', methods=['GET','PUT','DELETE', 'POST'])
def loads_get_put_delete(id):
    #endpoint to update a load
    if request.method == 'PUT':
        #get the content of the request
        content = request.get_json()
        #make a new key for datastore
        load_key = client.key(constants.loads, int(id))
        #create a new load
        load = client.get(key=load_key)
        #add the request data to the load
        load.update({"name": content["name"], "description": content["description"], "price": content["price"]})
        #put the load into the database
        client.put(load)
        #successful, return 204
        res = make_response()
        res.mimtype = 'application/json'
        res.status_code = 204
        res.headers.set('Content-Type', 'application/json')
        return res
    #endpoint for deleting a load
    elif request.method == 'DELETE':
        #find the key within the database for the load we want
        key = client.key(constants.loads, int(id))
        #get the load object out of the database
        load = client.get(key = key)
        #if the load is not there, return 404
        if (load == None):
            response_body = {}
            response_body["Error"] = "No load with this load_id exists"
            return (json.dumps(response_body), 404)
        #get the table of boats
        query = client.query(kind=constants.boats)
        #list the table
        results = list(query.fetch())
        #for each result, set the 'id'
        for e in results:
            e["id"] = e.key.id
            #if the 'loads' array is not empty
            if not (e["loads"] == None):
                #if the load we are looking at is the one we are deleting
                if (e["loads"] == load["id"]):
                    #get the boat out of the database
                    boat_key = client.key(constants.boats, e["id"])
                    boat = client.get(key=boat_key)
                    #remove the load from it
                    boat.update({"loads": None})
                    #put it back into datastore
                    client.put(boat)
        #delete the load
        client.delete(key)
        #return 204 as json data
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 204
        res.headers.set('Content-Type', 'applicaton/json')
        return res
    #endpoint to GET a specific load
    elif request.method == 'GET':
        #get content of the request to this endpoint
        content = request.get_json()
        #find the key in datastore that corresponds tothe load's id
        load_key = client.key(constants.loads, int(id))
        #get the load out of datastore
        load = client.get(key=load_key)
        #if the load is not there, return 404
        if (load == None):
            response_data = {}
            response_data['Error'] = 'No load with this load_id exists'
            return (json.dumps(response_data), 404)
        #set 'id' and 'self' attributes of the load for display
        load["id"] = load.key.id
        load["self"] = request.url
        #return the load object with 200 status code
        return (json.dumps(load), 200)
    #can't POST to this endpoint, so return 405
    elif request.method == 'POST':
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set('Content-Type', 'applicaton/json')
        return res
    #no other methods recognized here
    else:
        return 'Method not recogonized'