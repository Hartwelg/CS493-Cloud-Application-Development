from flask import Flask, Blueprint, request, make_response
from google.cloud import datastore
from requests_oauthlib import OAuth2Session
import json
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests
import constants

client = datastore.Client()

bp = Blueprint('owners', __name__, url_prefix='/owners')

@bp.route('/', methods=['POST', 'GET', 'PUT', 'DELETE'])
def owners_get_post_put_delete():
    if request.method == 'GET':
        #make a query to datastore for the entity in the request
        query = client.query(kind=constants.owners)
        #limit response length to 5
        q_limit = int(request.args.get('limit', '5'))
        #set offset for results for pagination
        q_offset = int(request.args.get('offset', '0'))
        #keeps track of where in the results we are
        g_iterator = query.fetch(limit= q_limit, offset=q_offset)
        #keeps track of how many pages of results there are
        pages = g_iterator.pages
        #results of query
        results = list(next(pages))
        #keeps the 'next' url, which gives the next page of results of the query
        if g_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        #if there are no more pages of results, 'next' is empty
        else:
            next_url = None
        #for each entity in results, set 'id' field and 'self' field
        for e in results:
            e["id"] = e.key.id
            e["self"] = request.url + str(e.key.id)
        #makes output of request. puts 'boats' at the beginning of the page, then outputs the results after that
        output = {"owners": results}
        #if there is a 'next' page, add it to the 'next' field in the output
        if next_url:
            output["next"] = next_url
        #make a response with 200 status code, return to requester
        # res = make_response(json.dumps(results))
        # res.mimetype = 'application/json'
        # res.status_code = 200
        # res.headers.set('Content-Type', 'application/json')
        # return res
        return (json.dumps(output), 200)
    #endpoint to add a new owner
    elif request.method == 'POST':
        #get the data from the request
        content = request.get_json()
        #make a new ID for the owner
        new_owner = datastore.entity.Entity(key=client.key(constants.owners))
        #authenticate the user
        req = requests.Request()
        token = request.headers.get("Authorization")
        if (token == None):
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        token = token.split(' ')
        token = token[1]
        try:
            id_info = id_token.verify_oauth2_token(token, req, constants.client_id)
        except:
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        if id_info['iss'] != "accounts.google.com":
            raise ValueError('Incorrect Issuer')
        uid = id_info['sub']
        #try adding request data to the new owner entity
        try:
            new_owner.update({"user_id": uid, "password": content["pass"], "age": content["age"], "boats": content["boats"]})
        #if there is something wrong with the update, return 400
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        #add the owner to datastore
        client.put(new_owner)
        #set 'id' attribute of owner
        new_owner["id"] = str(new_owner.key.id)
        #set 'self' attribute of new owner
        new_owner["self"] = request.url + '/' + str(new_owner.key.id)
        #return 201 response
        res = make_response(json.dumps(new_owner))
        res.mimetype = 'application/json'
        res.status_code = 201
        res.headers.set('Content-Type', 'application/json')
        return res
    #can't update or delete bulk entities, so return 405
    elif request.method == 'PUT' or request.method == 'DELETE':
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set('Content-Type', 'application/json')
        return res
    #no other methods allowed
    else:
        return 'Method not recognized'

@bp.route('/<oid>', methods=['GET', 'DELETE'])
def owner_get_delete(oid):
    if request.method == 'GET':
        #get the content from the request as json
        content = request.get_json()
        #get the boat object from datastore
        owner_key = client.key(constants.owners, int(oid))
        owner = client.get(key=owner_key)
        #if there is no boat, return 404
        if (owner == None):
            response_data = {}
            response_data['Error'] = 'No owner with this owner_id exists'
            return (json.dumps(response_data), 404)
        #set boat's id and self attributes for displaying
        owner["id"] = owner.key.id
        owner["self"] = request.url
        #return the boat data as json
        return (json.dumps(owner), 200)
    #POST method. POST only allowed to /boats/, so not allowed here
    elif request.method == 'POST':
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set('Content-Type', 'applicaton/json')
        return res
    elif request.method == 'DELETE':
        #validate the user before anything else is allowed
        req = requests.Request()
        #token is in 'authorization' header of request
        token = request.headers.get("Authorization")
        #if there is no token, return 401 response
        if (token == None):
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        #remove 'bearer ' portion of bearer token
        token = token.split(' ')
        token = token[1]
        #verify token
        try:
            id_info = id_token.verify_oauth2_token(token, req, constants.client_id)
        #if token is not valie, return 401 response
        except:
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        #if 'iss' value of token is incorrect, don't trust it
        if id_info['iss'] != "accounts.google.com":
            raise ValueError('Incorrect Issuer')
        #owner is in 'sub' field of token
        uid = id_info['sub']
        #get the key for the boat we are deleting
        key = client.key(constants.owners, int(oid))
        #get the boat object from datastore
        owner = client.get(key = key)
        #if there is no boat, return 404
        if (owner == None):
            response_body = {}
            response_body["Error"] = "No owner with this owner_id exists"
            return (json.dumps(response_body), 404)
        #set the owner id
        owner["id"] = str(owner.key.id)
        #get a list of all loads in in the system
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        #for each result, get the id and compare its carrier to the boat we are deleting.
        for e in results:
            e["id"] = e.key.id
            #if the carrier id and the boat id are the same, remove the load from the boat
            if (e["owner"] != None and e["owner"]["id"] == owner["id"]):
                #get the load object
                boat_key = client.key(constants.boats, e["id"])
                boat = client.get(key=boat_key)
                #set 'carrier' to none
                boat.update({"owner": None})
                #put it back in the database
                client.put(boat)
        #finally, remove the owner
        client.delete(key)
        #return 204 status code
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 204
        res.headers.set('Content-Type', 'application/json')
        return res
    #no other methods allowed here
    else:
        return 'Method not recognized'

#endpoint to get a specific boat for an owner
@bp.route('/<oid>/boats/', methods=['GET'])
def get_owner_boats(oid):
    #get data from request
    content = request.get_json()
    #find the key in datastore that corresponds to the owner's id
    owner_key = client.key(constants.owners, int(oid))
    #get the owner object from datastore
    owner = client.get(key=owner_key)
    #authenticate the user
    req = requests.Request()
    token = request.headers.get("Authorization")
    if (token == None):
        response_body = {}
        response_body["Error"] = "The request does not have proper authorization"
        return (json.dumps(response_body), 401)
    token = token.split(' ')
    token = token[1]
    try:
        id_info = id_token.verify_oauth2_token(token, req, constants.client_id)
    except:
        response_body = {}
        response_body["Error"] = "The request does not have proper authorization"
        return (json.dumps(response_body), 401)
    if id_info['iss'] != "accounts.google.com":
        raise ValueError('Incorrect Issuer')
    uid = id_info['sub']
    #if there is no owner, return 404
    if (owner == None):
        response_data = {}
        response_data['Error'] = 'No owner with this owner_id exists'
        return (json.dumps(response_data), 404)
    #set 'id' attribute of owner for display
    owner["id"] = owner.key.id
    #set 'self' attribute of owner
    owner["self"] = request.url
    #initialize the list of boats owned by the authenticated user
    boat_list = []
    #if the owner has any boats
    if 'boats' in owner.keys():
        #search through them
        for bid in owner["boats"]:
            #get the key that corresponds to the id we are looking at
            boat_key = client.key(constants.boats, int(bid["id"]))
            #get the boat object from datastore
            boat = client.get(key=boat_key)
            #set the 'self' attribute
            boat['self'] = request.url_root + "boats/" + str(boat.key.id)
            #add the boat to boat_list
            boat_list.append(boat)
        #return the boat list and 200 status code
        return (json.dumps(boat_list), 200)
    #else, return 200 with nothing
    res = make_response()
    res.mimetype = 'application/json'
    res.status_code = 200
    res.headers.set('Content-Type', 'application/json')
    return (json.dumps([]), res)

#endpoint for a specific boat owned by an owner
@bp.route('/<oid>/boats/<bid>', methods=['PUT', 'DELETE', 'GET', 'POST'])
def add_delete_boat_for_owner(oid, bid):
    #adding a new boat to the owner
    if request.method == 'PUT':
        #get the data from the request
        content = request.get_json()
        #get the boat and the owner from datastore
        boat_key = client.key(constants.boats, int(bid))
        owner_key = client.key(constants.owners, int(oid))
        boat = client.get(key=boat_key)
        owner = client.get(key=owner_key)
        #if the boat or the owner are not in datastore, return 404 response
        if (boat == None or owner == None):
            response_body = {}
            response_body["Error"] = "The specified boat and/or owner does not exist"
            return (json.dumps(response_body), 404)
        #set 'id' and 'self' for both the boat and the owner
        boat["id"] = str(boat.key.id)
        boat["self"] = request.url
        owner["id"] = str(owner.key.id)
        owner["self"] = request.url
        #look through the boats that are owned by the owner
        for bid in owner["boats"]:
            #if the boat we are looking at is owned by the current owner, return 403 because the boat is already there
            if (bid["owner"] == owner["user_id"]):
                response_body = {}
                response_body["Error"] = "The boat is already assigned to the owner"
                return (json.dumps(response_body), 403)
        #otherwise, initialize the boat's owner
        boat_owner = {}
        #set the boat's owner's id to the owner's id that we are looking at
        boat_owner["id"] = str(owner["id"])
        #set the boat's owenr's user_id to the owner's user_id
        boat_owner["user_id"] = owner["user_id"]
        #set the boat's owner's 'self' attribute to the owner's 'self' attribute
        boat_owner["self"] = request.url_root + "owners/" + owner["id"]
        #set the boat's owner to the owner we are looking at
        boat.update({"owner": boat_owner})
        #initialize the owned_boat variable to hold the boat's data
        owned_boat = {}
        #set the owned_boat's id to the boat's id
        owned_boat["id"] = str(boat["id"])
        #set the owned_boat's owner to the owner
        owned_boat["owner"] = owner["user_id"]
        #set the owned_boat's 'self' attribute to the boat's initial location in datastore
        owned_boat["self"] = request.url_root + "boats/" + boat["id"]
        #add the boat to the owner's list of boats
        owner["boats"].append(owned_boat)
        #add the boat and the owner back into datastore
        client.put(boat)
        client.put(owner)
        #return 204 response if successful
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 204
        res.headers.set('Content-Type', 'application/json')
        return res
    #removing a boat from an owner
    elif request.method == 'DELETE':
        #get the boat and the owner out of datastore
        boat_key = client.key(constants.boats, int(bid))
        owner_key = client.key(constants.owners, int(oid))
        boat = client.get(key=boat_key)
        owner = client.get(key=owner_key)
        #try to set the 'id' attribute for the boat and the owner
        try:
            boat["id"] = str(boat.key.id)
            owner["id"] = str(owner.key.id)
        #if not successful, return 404
        except AttributeError:
            response_body = {}
            response_body["Error"] = "No boat with this boat_id is owned by the owner with this owner_id"
            return (json.dumps(response_body), 404)
        #if boat or owner don't exist, the boat doesn't have an owner, or the boat's owner is not this owner, return 404
        if (owner == None or boat == None or boat["owner"] == None or boat["owner"]["id"] != owner["id"]):
            response_body = {}
            response_body["Error"] = "No boat with this boat_id is owned by the owner with this owner_id"
            return (json.dumps(response_body), 404)
        #if the boat's owner is the owner in question, change the boat to be owned by nobody
        if (boat["owner"]["id"] == owner["id"]):
            boat.update({"owner": None})
        #search through the boats in the onwer's list
        for e in owner["boats"]:
            #if the current boat in the list is the boat we are looking for, remove it from the list
            if (e["id"] == boat["id"]):
                owner["boats"].remove(e)
        #put the boat and the owner back into datastore
        client.put(owner)
        client.put(boat)
        #return 204 status code when successful
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 204
        res.headers.set('Content-Type', 'application/json')
        return res
    #GET and POST not used here, so return 405
    elif request.method == 'GET' or request.method == 'POST':
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set('Content-Type', 'applicaton/json')
        return res
    #no other methods allowed here
    else:
        return "Method not recognized"