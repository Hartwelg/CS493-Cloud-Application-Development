from flask import Flask, Blueprint, request, make_response
from google.cloud import datastore
from requests_oauthlib import OAuth2Session
import json
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests
import constants
import re

client = datastore.Client()

bp = Blueprint('boats', __name__, url_prefix='/boats')

@bp.route('/', methods=['POST','GET', 'PUT', 'DELETE'])
def boats_get_post_put_delete():
    #post method
    if request.method == 'POST':
        #get json content from the request to this endpoint
        content = request.get_json()
        #create a new entity and give it an id
        new_boat = datastore.entity.Entity(key=client.key(constants.boats))

        #handle authentication for the request.
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

        # if the content_type of the request is not application/json, send back a 415 response
        if "application/json" not in request.content_type:
                res = make_response()
                res.status_code = 415
                return res
        # match to one or more words and spaces. prevents empty names and names with odd characters
        match = re.match("([\w|\s]+)", content["name"])
        # if name is too long or doesn't fit the match above, return 400 response
        if (len(content["name"]) >= 15 or not match):
            response_body = {}
            response_body["Error"] = "Boat name is too long or contains non-alphanumeric characters"
            return (json.dumps(response_body), 400)
        # if 'length' is in the content and is more than 500, return 400 response
        if "length" in content:
            if content["length"] > 500:
                response_body = {}
                response_body["Error"] = "Boat length cannot exceed 500"
                return (json.dumps(response_body), 400)
        #make a query to datastore for the entity we created earlier
        query = client.query(kind=constants.boats)
        #make a list of the results of our query to datastore
        results = list(query.fetch())
        #look through the results for matching names, return 403 response if there is a match
        for e in results:
            if content["name"] == e["name"]:
                response_body = {}
                response_body["Error"] = "Boat name is not unique"
                return (json.dumps(response_body), 403)
        # try/except for KeyError, in case the request is missing any attributes
        try:
            for x in content:
                #check if request has any extraneous attributes, return 400 response if so
                if not (x == "name" or x == "length" or x == "type" or x == "loads" or x == "owner"):
                    response_body = {}
                    response_body['Error'] = "Extraneous field(s) in request"
                    return (json.dumps(response_body), 400)
            #add data to boat entity we created earlier, including setting the owner with the 'uid' variable taken from 'sub' field in auth token
            new_boat.update({"name": content["name"], "type": content["type"], "length": content["length"], "loads": content["loads"], "owner": uid})
        #if there is a KeyError, return a 400 response in json format
        except KeyError:
            res = make_response()
            res.status_code = 400
            res.mimetype = 'application/json'
            res.headers.set('Content-Type', 'application/json')
            return res
        #put the new entity into datastore
        client.put(new_boat)
        #assign 'id' field to boat entity
        new_boat["id"] = str(new_boat.key.id)
        #assign 'self' field to boat entity
        new_boat["self"] = request.url + str(new_boat.key.id)
        #check for 'application/json' in the accept header of the request. Return boat data as json if so, return 406 response as json if not.
        if 'application/json' in request.accept_mimetypes:
            res = make_response(json.dumps(new_boat))
            res.mimetype = 'application/json'
            res.status_code = 201
            res.headers.set('Content-Type', 'application/json')
            return res
        else:
            boat_key = client.key(constants.boats, int(new_boat["id"]))
            client.delete(boat_key)
            res = make_response()
            res.mimetype = 'application/json'
            res.status_code = 406
            res.headers.set('Content-Type', 'application/json')
            return res
    #GET method
    elif request.method == 'GET':
        req = requests.Request()
        token = request.headers.get("Authorization")
        #if there is no token, return 200 status code and results that don't pertain to the authenticated user
        if (token == None):
            #make a query to datastore for the entity in the request
            query = client.query(kind=constants.boats)
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
                e["self"] = request.url
            #makes output of request. combines pagination with data from 'boats' table in datastore
            output = {"boats": results}
            #if there is a 'next' page, add it to the 'next' field in the output
            if next_url:
                output["next"] = next_url
            return (json.dumps(output), 200)
        #else, get the access token and try verifying
        token = token.split(' ')
        token = token[1]
        try:
            id_info = id_token.verify_oauth2_token(token, req, constants.client_id)
        #if token does not verify, return results that do not pertain to authenticated user
        except:
            query = client.query(kind=constants.boats)
            results = list(query.fetch())
            for e in results:
                e["id"] = e.key.id
            #return 200 status code in json format
            res = make_response()
            res.mimetype = 'applicaton/json'
            res.status_code = 200
            res.headers.set('Content-Type', 'application/json')
            return res
        #if 'iss' field in token is incorrect, do not trust it
        if id_info['iss'] != "accounts.google.com":
            raise ValueError('Incorrect Issuer')
        #user id - the owner's name
        uid = id_info['sub']

        #make a query to datastore for the entity in the request
        query = client.query(kind=constants.boats)
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

        output = []
        boatList = {"boats": output}
        # output += "Boats: "
        #for each entity in results, set 'id' field and 'self' field, then check each one to see if it is owned by the authenticated user
        for e in results:
            e["id"] = e.key.id
            e["self"] = request.url
            #if the boat is owned by the authenticated user, add it to output
            if (e["owner"] == uid):
                boat_key = client.key(constants.boats, int(e.key.id))
                boat = client.get(key = boat_key)
                boat['id'] = boat.key.id
                boat['self'] = request.url + str(boat['id'])
                output.append(boat)
        #makes output of request. combines pagination with data from 'boats' table in datastore
        # output = {"boats": results}
        #if there is a 'next' page, add it to the 'next' field in the output
        if next_url:
            output["next"] = next_url
        #return 200 status code
        return (json.dumps(boatList), 200)
    #PUT and DELETE methods not allowed to this endpoint, so return 405 response.
    elif request.method == 'PUT' or request.method == 'DELETE':
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set('Content-Type', 'applicaton/json')
        return res
    #no other methods allowed to this endpoint
    else:
        return 'Method not recogonized'

@bp.route('/<id>', methods=['GET','PUT','DELETE', 'POST'])
def boats_get_put_delete(id):
    #PUT method. Used to update data on a boat
    if request.method == 'PUT':
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
        #get the json data out of the request
        content = request.get_json()
        #get the key for the boat that needs updating
        boat_key = client.key(constants.boats, int(id))
        #get the boat object from datastore
        boat = client.get(key=boat_key)
        #if there is no boat, return 404
        if (boat == None):
            response_body = {}
            response_body["Error"] = "No boat with this boat_id exists"
            return (json.dumps(response_body), 404)
        #put the new data into it
        boat.update({"name": content["name"], "type": content["type"], "length": content["length"], "owner": content["owner"]})
        #put the boat object back into datastore
        client.put(boat)
        #set 'id' and 'self' attributes of boat
        boat["id"] = boat.key.id
        boat["self"] = request.url
        #return 204 status code
        res = make_response(json.dumps(boat))
        res.mimetype = 'application/json'
        res.status_code = 204
        res.headers.set('Content-Type', 'applicaton/json')
        return res
    #DELETE method
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
        key = client.key(constants.boats, int(id))
        #get the boat object from datastore
        boat = client.get(key = key)
        #if there is no boat, return 404
        if (boat == None):
            response_body = {}
            response_body["Error"] = "No boat with this boat_id exists"
            return (json.dumps(response_body), 404)
        #set the boat id
        boat["id"] = str(boat.key.id)
        #get a list of all loads in in the system
        query = client.query(kind=constants.loads)
        results = list(query.fetch())
        #for each result, get the id and compare its carrier to the boat we are deleting.
        for e in results:
            e["id"] = e.key.id
            #if the carrier id and the boat id are the same, remove the load from the boat
            if (e["carrier"] != None and e["carrier"]["id"] == boat["id"]):
                #get the load object
                load_key = client.key(constants.loads, e["id"])
                load = client.get(key=load_key)
                #set 'carrier' to none
                load.update({"carrier": None})
                #put it back in the database
                client.put(load)
        #finally, remove the baot
        client.delete(key)
        #return 204 status code
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 204
        res.headers.set('Content-Type', 'application/json')
        return res
    #GET method
    elif request.method == 'GET':
        #authenticate the user before we can do anything else
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
        #get the content from the request as json
        content = request.get_json()
        #get the boat object from datastore
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        #if there is no boat, return 404
        if (boat == None):
            response_data = {}
            response_data['Error'] = 'No boat with this boat_id exists'
            return (json.dumps(response_data), 404)
        #set boat's id and self attributes for displaying
        boat["id"] = boat.key.id
        boat["self"] = request.url
        #return the boat data as json
        return (json.dumps(boat), 200)
    #POST method. POST only allowed to /boats/, so not allowed here
    elif request.method == 'POST':
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 405
        res.headers.set('Content-Type', 'applicaton/json')
        return res
    #no other methods allowed
    else:
        return 'Method not recogonized'

#GET all loads for a given boat
@bp.route('/<bid>/loads/', methods=['GET'])
def get_loads_for_boat(bid):
    #get the data from the request to this endpoint
    content = request.get_json()
    #get the key from datastore that corresponds to this boat's id
    boat_key = client.key(constants.boats, int(bid))
    #get the boat out of datastore
    boat = client.get(key=boat_key)
    #if boat is not there, return 404
    if (boat == None):
        response_data = {}
        response_data['Error'] = 'No boat with this boat_id exists'
        return (json.dumps(response_data), 404)
    #set boat's 'id' and 'self' attributes for display
    boat["id"] = boat.key.id
    boat["self"] = request.url
    #initialize the list of loads that are on this boat
    load_list = []
    #if there are any loads on this boat
    if 'loads' in boat.keys():
        #search through the loads that are on this boat
        for lid in boat["loads"]:
            #get the key from datastore that corresponds to this load's id
            load_key = client.key(constants.loads, int(lid["id"]))
            #add that load to load_list
            load_list.append(load_key)
        #return the load_list
        return json.dumps(client.get_multi(load_list))
    #else, return nothing as json data
    res = make_response()
    res.mimetype = 'application/json'
    res.status_code = 200
    res.headers.set('Content-Type', 'application/json')
    return (json.dumps([]), res)

#endpoint for adding or removing a load from a boat
@bp.route('/<bid>/loads/<lid>', methods=['PUT','DELETE'])
def add_delete_load_to_boat(bid, lid):
    #endpoint to add a load to a boat
    if request.method == 'PUT':
        #get the data from the request
        content = request.get_json()
        #get the load and the boat from datastore
        load_key = client.key(constants.loads, int(lid))
        boat_key = client.key(constants.boats, int(bid))
        load = client.get(key=load_key)
        boat = client.get(key=boat_key)
        #if either the boat or the load are not here, return 404
        if (boat == None or load == None):
            response_body = {}
            response_body["Error"] = "The specified boat and/or load does not exist"
            return (json.dumps(response_body), 404)
        #set 'id' and 'self' attributes for both the boat and the load
        boat["id"] = str(boat.key.id)
        boat["self"] = request.url
        load["id"] = str(load.key.id)
        load["self"] = request.url
        #search through the loads that are on this boat
        for lid in boat["loads"]:
            #if the id of the load on the boat matches the one we are searching for, return 403 because it's already there
            if (lid["id"] == load["id"]):
                response_body = {}
                response_body["Error"] = "The load is already on the boat"
                return (json.dumps(response_body), 403)
        #else, set the load's carrier to the boat
        load_carrier = {}
        load_carrier["id"] = str(boat["id"])
        load_carrier["name"] = boat["name"]
        load_carrier["self"] = request.url_root + "boats/" + boat["id"]
        load.update({"carrier": load_carrier})
        #and add the load to the boat's list of loads
        carried_load = {}
        carried_load["id"] = str(load["id"])
        carried_load["self"] = request.url_root + "loads/" + load["id"]
        boat["loads"].append(carried_load)
        #add both the boat and the load back into datastore
        client.put(load)
        client.put(boat)
        #return 204 as json data
        res = make_response()
        res.status_code = 204
        res.mimetype = 'application/json'
        res.headers.set('Content-Type', 'application/json')
        return res
    #endpoint to remove a load from a boat
    elif request.method == 'DELETE':      
        #get both the load and the boat from datastore  
        load_key = client.key(constants.loads, int(lid))
        boat_key = client.key(constants.boats, int(bid))
        load = client.get(key=load_key)
        boat = client.get(key=boat_key)
        #try assigning the 'id' attribute for both the load and the boat
        try:
            boat["id"] = str(boat.key.id)
            load["id"] = str(load.key.id)
        #if there is no load or boat, return 404
        except AttributeError:
            response_body = {}
            response_body["Error"] = "No load with this load_id is on the boat with this boat_id"
            return (json.dumps(response_body), 404)
        #if boat or load aren't there, the load has no carrier, or the load's carrier is not the boat in question, return 404
        if (boat == None or load == None or load["carrier"] == None or load["carrier"]["id"] != boat["id"]):
            response_body = {}
            response_body["Error"] = "No load with this load_id is on the boat with this boat_id"
            return (json.dumps(response_body), 404)
        #if the load's carrier is the boat, set the load's carrier to None
        if (load["carrier"]["id"] == boat["id"]):
            load.update({"carrier": None})
        #remove the load from the boat's loads
        for e in boat["loads"]:
            if (e["id"] == load["id"]):
                boat["loads"].remove(e)
        #put the boat and the load back into datastore
        client.put(boat)
        client.put(load)
        #return 204 as json data
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 204
        res.headers.set('Content-Type', 'application/json')
        return res
    #no other methods recognized here
    else:
        return 'Method not recognized'