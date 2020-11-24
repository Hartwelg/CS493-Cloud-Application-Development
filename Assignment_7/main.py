from google.cloud import datastore
from flask import Flask, request
import json
import constants
import auth

app = Flask(__name__)
client = datastore.Client()

from google.cloud import datastore
from flask import Flask, request
from requests_oauthlib import OAuth2Session
import json
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests

# This disables the requirement to use HTTPS so that you can test locally.
import os 
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
client = datastore.Client()

# These should be copied from an OAuth2 Credential section at
# https://console.cloud.google.com/apis/credentials
client_id = r'755334506722-56mkl83eenr86529ekkes2c4giqgqvf7.apps.googleusercontent.com'
client_secret = r'5bmlb8UgtrncEsjRGBt_gn44'

# This is the page that you will use to decode and collect the info from
# the Google authentication flow
redirect_uri = 'https://hartwelg-hw7-gae.wl.r.appspot.com/oauth'

# These let us get basic info to identify a user and not much else
# they are part of the Google People API
# scope = ['https://www.googleapis.com/auth/userinfo.email', 
scope = ['https://www.googleapis.com/auth/userinfo.profile']
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

# This link will redirect users to begin the OAuth flow with Google
@app.route('/')
def index():
    authorization_url, state = oauth.authorization_url(
        'https://accounts.google.com/o/oauth2/auth',
        # access_type and prompt are Google specific extra
        # parameters.
        access_type="offline", prompt="select_account")
    return 'Please go <a href=%s>here</a> and authorize access.' % authorization_url

# This is where users will be redirected back to and where you can collect
# the JWT for use in future requests
@app.route('/oauth')
def oauthroute():
    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.url,
        client_secret=client_secret)
    req = requests.Request()

    id_info = id_token.verify_oauth2_token( 
    token['id_token'], req, client_id)

    return "Your JWT is: %s" % token['id_token']

# This page demonstrates verifying a JWT. id_info['email'] contains
# the user's email address and can be used to identify them
# this is the code that could prefix any API call that needs to be
# tied to a specific user by checking that the email in the verified
# JWT matches the email associated to the resource being accessed.
@app.route('/verify-jwt')
def verify():
    req = requests.Request()

    id_info = id_token.verify_oauth2_token( 
    request.args['jwt'], req, client_id)

    return repr(id_info) + "<br><br> the user is: " + id_info['email']

@app.route('/boats', methods=['POST','GET'])
def boats_get_post():
    if request.method == 'POST':
        content = request.get_json()
        new_boat = datastore.entity.Entity(key=client.key(constants.boats))
        
        req = requests.Request()
        token = request.headers.get("Authorization")
        if (token == None):
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        token = token.split(' ')
        token = token[1]
        try:
            id_info = id_token.verify_oauth2_token(token, req, client_id)
        except:
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        if id_info['iss'] != "accounts.google.com":
            raise ValueError('Incorrect Issuer')
        uid = id_info['sub']

        try:
            new_boat.update({"name": content["name"], "type": content["type"], "length": content["length"], "public": content["public"], "owner": uid})
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(new_boat)
        new_boat["id"] = str(new_boat.key.id)
        new_boat["self"] = request.url + '/' + str(new_boat.key.id)
        return (json.dumps(new_boat), 201)
    elif request.method == 'GET':
        req = requests.Request()
        token = request.headers.get("Authorization")
        if (token == None):
            query = client.query(kind=constants.boats)
            results = list(query.fetch())
            for e in results:
                e["id"] = e.key.id
            return (json.dumps(results), 200)
        token = token.split(' ')
        token = token[1]
        try:
            id_info = id_token.verify_oauth2_token(token, req, client_id)
        except:
            query = client.query(kind=constants.boats)
            results = list(query.fetch())
            for e in results:
                e["id"] = e.key.id
            return (json.dumps(results), 200)
        if id_info['iss'] != "accounts.google.com":
            raise ValueError('Incorrect Issuer')
        uid = id_info['sub']

        query = client.query(kind=constants.boats)
        results = list(query.fetch())
        response_body = []
        for e in results:
            e["id"] = e.key.id
            if (e["owner"] == uid):
                response_body.append(e)
        return (json.dumps(response_body), 200)
    else:
        return 'Method not recogonized'

@app.route('/owners', methods=['GET', 'POST'])
def get_post_owners():
    if request.method == 'GET':
        query = client.query(kind=constants.owners)
        results = list(query.fetch())
        for e in results:
            e["id"] = e.key.id
        return (json.dumps(results), 200)
    elif request.method == 'POST':
        content = request.get_json()
        new_owner = datastore.entity.Entity(key=client.key(constants.owners))
        
        req = requests.Request()
        token = request.headers.get("Authorization")
        if (token == None):
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        token = token.split(' ')
        token = token[1]
        try:
            id_info = id_token.verify_oauth2_token(token, req, client_id)
        except:
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        if id_info['iss'] != "accounts.google.com":
            raise ValueError('Incorrect Issuer')
        uid = id_info['sub']

        try:
            new_owner.update({"name": uid, "boats": content["boats"]})
        except KeyError:
            response_body = {}
            response_body['Error'] = "The request object is missing at least one of the required attributes"
            return (json.dumps(response_body), 400)
        client.put(new_owner)
        new_owner["id"] = str(new_owner.key.id)
        new_owner["self"] = request.url + '/' + str(new_owner.key.id)
        return (json.dumps(new_owner), 201)
    else:
        return "Method not recognized"
        
@app.route('/owners/<oid>/boats', methods=['GET'])
def get_owner_boats(oid):
    content = request.get_json()
    owner_key = client.key(constants.owners, int(oid))
    owner = client.get(key=owner_key)

    req = requests.Request()
    token = request.headers.get("Authorization")
    if (token == None):
        response_body = {}
        response_body["Error"] = "The request does not have proper authorization"
        return (json.dumps(response_body), 401)
    token = token.split(' ')
    token = token[1]
    try:
        id_info = id_token.verify_oauth2_token(token, req, client_id)
    except:
        response_body = {}
        response_body["Error"] = "The request does not have proper authorization"
        return (json.dumps(response_body), 401)
    if id_info['iss'] != "accounts.google.com":
        raise ValueError('Incorrect Issuer')
    uid = id_info['sub']

    if (owner == None):
        response_data = {}
        response_data['Error'] = 'No owner with this owner_id exists'
        return (json.dumps(response_data), 404)
    owner["id"] = owner.key.id
    owner["self"] = request.url
    boat_list = []
    query = client.query(kind=constants.boats)
    results = list(query.fetch())
    for e in results:
        e["id"] = e.key.id
        if (e["owner"] == uid):
            if (e["public"] == "True"):
                boat_list.append(e)
    return (json.dumps(boat_list), 200)

@app.route('/boats/<bid>', methods=['GET', 'DELETE'])
def bid_get_delete(bid):
    if request.method == 'GET':
        content = request.get_json()
        boat_key = client.key(constants.boats, int(bid))
        boat = client.get(key=boat_key)
        if (boat == None):
            response_data = {}
            response_data['Error'] = 'No boat with this boat_id exists'
            return (json.dumps(response_data), 404)
        
        req = requests.Request()
        token = request.headers.get("Authorization")
        if (token == None):
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        token = token.split(' ')
        token = token[1]
        try:
            id_info = id_token.verify_oauth2_token(token, req, client_id)
        except:
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        if id_info['iss'] != "accounts.google.com":
            raise ValueError('Incorrect Issuer')
        uid = id_info['sub']

        boat["id"] = boat.key.id
        boat["self"] = request.url
        return (json.dumps(boat), 200)
    elif request.method == 'DELETE':
        req = requests.Request()
        token = request.headers.get("Authorization")
        if (token == None):
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        token = token.split(' ')
        token = token[1]
        try:
            id_info = id_token.verify_oauth2_token(token, req, client_id)
        except:
            response_body = {}
            response_body["Error"] = "The request does not have proper authorization"
            return (json.dumps(response_body), 401)
        if id_info['iss'] != "accounts.google.com":
            raise ValueError('Incorrect Issuer')
        uid = id_info['sub']

        key = client.key(constants.boats, int(bid))
        boat = client.get(key = key)
        if (boat == None):
            response_body = {}
            response_body["Error"] = "No boat with this boat_id exists"
            return (json.dumps(response_body), 403)
        boat["id"] = str(boat.key.id)
        if (boat["owner"] != uid):
            response_body = {}
            response_body["Error"] = "Boat is owned by someone else"
            return (json.dumps(response_body), 403)
        client.delete(key)
        return ('', 204)
    else:
        return "Method not recognized"

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)