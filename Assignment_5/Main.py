from google.cloud import datastore
from flask import Flask, request, make_response
import json
import constants
import json2html
import re

app = Flask(__name__)
client = datastore.Client()

@app.route('/')
def index():
    return "Please navigate to /boats to use this API"

@app.route('/boats', methods=['POST','GET', 'PUT', 'DELETE'])
def boats_get_post():
    if request.method == 'POST':
        content = request.get_json()
        new_boat = datastore.entity.Entity(key=client.key(constants.boats))
        if "application/json" not in request.content_type:
                res = make_response()
                res.status_code = 415
                return res
        match = re.match("([\w|\s]+)", content["name"])
        if (len(content["name"]) >= 15 or not match):
            response_body = {}
            response_body["Error"] = "Boat name is too long or contains non-alphanumeric characters"
            return (json.dumps(response_body), 400)
        if "length" in content:
            if content["length"] > 500:
                response_body = {}
                response_body["Error"] = "Boat length cannot exceed 500"
                return (json.dumps(response_body), 400)
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        for e in results:
            if content["name"] == e["name"]:
                response_body = {}
                response_body["Error"] = "Boat name is not unique"
                return (json.dumps(response_body), 403)
        try:
            for x in content:
                if not (x == "name" or x == "length" or x == "type"):
                    response_body = {}
                    response_body['Error'] = "Extraneous field(s) in request"
                    return (json.dumps(response_body), 400)
            new_boat.update({"name": content["name"], "type": content["type"], "length": content["length"]})
        except KeyError:
            response_body = {}
            response_body["Error"] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(new_boat)
        new_boat["id"] = str(new_boat.key.id)
        new_boat["self"] = request.url + '/' + str(new_boat.key.id)
        if 'application/json' in request.accept_mimetypes:
            res = make_response(json.dumps(new_boat))
            res.mimetype = 'application/json'
            res.status_code = 201
            res.headers.set('Content-Type', 'application/json')
            return res
        else:
            res = make_response()
            res.mimetype = 'application/json'
            res.status_code = 406
            res.headers.set('Content-Type', 'application/json')
            return res
    elif request.method == 'GET':
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
        res = make_response(json.dumps(results))
        res.mimetype = 'application/json'
        res.status_code = 200
        return res
    elif request.method == 'PUT' or request.method == 'DELETE':
        res = make_response()
        res.mimetype = 'application/json'
        res.status_code = 405
        return res
    else:
        return 'Method not recogonized'

@app.route('/boats/<id>', methods=['GET','PUT','DELETE', 'PATCH'])
def boats_get_put_delete_patch(id):
    if request.method == 'PUT':
        content = request.get_json()
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        if (boat == None):
            response_body = {}
            response_body["Error"] = "No boat with this boat_id exists"
            return (json.dumps(response_body), 404)
        if "application/json" not in request.content_type:
            res = make_response()
            res.status_code = 415
            return res
        match = re.match("([\w|\s]+)", content["name"])
        if (len(content["name"]) >= 15 or not match):
            response_body = {}
            response_body["Error"] = "Boat name is too long or contains non-alphanumeric characters"
            return (json.dumps(response_body), 400)
        if "length" in content:
            if content["length"] > 500:
                response_body = {}
                response_body["Error"] = "Boat length cannot exceed 500"
                return (json.dumps(response_body), 400)
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        for e in results:
            if content["name"] == e["name"]:
                response_body = {}
                response_body["Error"] = "Boat name is not unique"
                return (json.dumps(response_body), 403)
        try:
            for x in content:
                if not (x == "name" or x == "length" or x == "type"):
                    response_body = {}
                    response_body['Error'] = "Extraneous field(s) in request"
                    return (json.dumps(response_body), 400)
            boat.update({"name": content["name"], "type": content["type"], "length": content["length"]})
        except KeyError:
            response_body = {}
            response_body["Error"] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(boat)
        if 'application/json' in request.accept_mimetypes:
            res = make_response(json.dumps(boat))
            res.mimetype = 'application/json'
            res.status_code = 303
            res.headers.set('Content-Type', 'application/json')
            res.headers.set('Location', request.url)
            return res
        else:
            res = make_response()
            res.status_code = 406
            return res
    elif request.method == 'DELETE':
        key = client.key(constants.boats, int(id))
        boat = client.get(key = key)
        if (boat == None):
            response_body = {}
            response_body["Error"] = "No boat with this boat_id exists"
            return (json.dumps(response_body), 404)
        boat["id"] = str(boat.key.id)
        client.delete(key)
        if 'application/json' in request.accept_mimetypes:
            res = make_response(json.dumps(boat))
            res.mimetype = 'application/json'
            res.status_code = 204
            res.headers.set('Content-Type', 'application/json')
            return res
        elif 'text/html' in request.accept_mimetypes:
            res = make_response(json2html.convert(json = json.dumps(boat)))
            res.mimetype = 'text/html'
            res.status_code = 204
            res.headers.set('Content-Type', 'text/html')
            return res
        else:
            res = make_response()
            res.status_code = 406
            return res
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
        if 'application/json' in request.accept_mimetypes:
            res = make_response(json.dumps(boat))
            res.mimetype = 'application/json'
            res.status_code = 200
            res.headers.set('Content-Type', 'application/json')
            return res
        elif 'text/html' in request.accept_mimetypes:
            res = make_response(json2html.convert(json = json.dumps(boat)))
            res.mimetype = 'text/html'
            res.status_code = 200
            res.headers.set('Content-Type', 'text/html')
            return res
        else:
            res = make_response()
            res.status_code = 406
            return res
    elif request.method == 'PATCH':
        if 'application/json' not in request.content_type:
                res = make_response()
                res.status_code = 415
                return res
        content = request.get_json()
        boat_key = client.key(constants.boats, int(id))
        boat = client.get(key=boat_key)
        if (boat == None):
            response_data = {}
            response_data["Error"] = "No boat with this boat_id exists"
            return (json.dumps(response_data), 404)
        match = re.match("([\w|\s]+)", content["name"])
        if (len(content["name"]) >= 15 or not match):
            response_body = {}
            response_body["Error"] = "Boat name is too long or contains non-alphanumeric characters"
            return (json.dumps(response_body), 400)
        if "length" in content:
            if content["length"] > 500:
                response_body = {}
                response_body["Error"] = "Boat length cannot exceed 500"
                return (json.dumps(response_body), 400)
        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        for e in results:
            if content["name"] == e["name"]:
                response_body = {}
                response_body["Error"] = "Boat name is not unique"
                return (json.dumps(response_body), 403)
        try:
            for x in content:
                if not (x == "name" or x == "length" or x == "type"):
                    response_body = {}
                    response_body['Error'] = "Extraneous field(s) in request"
                    return (json.dumps(response_body), 400)
            boat.update({"name": content["name"], "type": content["type"], "length": content["length"]})
        except KeyError:
            response_body = {}
            response_body["Error"] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(boat)
        boat["id"] = boat.key.id
        boat["self"] = request.url
        if 'application/json' in request.accept_mimetypes:
            res = make_response(json.dumps(boat))
            res.mimetype = 'application/json'
            res.status_code = 200
            res.headers.set('Content-Type', 'application/json')
            return res
        else:
            res = make_response()
            res.status_code = 406
            return res
    else:
        return 'Method not recogonized'

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)