from google.cloud import datastore
from flask import Flask, request, render_template, redirect, url_for
import requests
import json
from google.oauth2 import id_token
from google.auth import crypt
from google.auth import jwt
from google.auth.transport import requests
from requests_oauthlib import OAuth2Session
import constants
import load
import boat
import owner

app = Flask(__name__)
app.register_blueprint(load.bp)
app.register_blueprint(boat.bp)
app.register_blueprint(owner.bp)
client = datastore.Client()

import os 
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# This is the page that you will use to decode and collect the info from
# the Google authentication flow
redirect_uri = 'https://hartwelg-final-gae.wl.r.appspot.com/oauth'
# redirect_uri = 'http://localhost:8080/oauth'

# These let us get basic info to identify a user and not much else
# they are part of the Google People API
# scope = ['https://www.googleapis.com/auth/userinfo.email', 
scope = ['https://www.googleapis.com/auth/userinfo.profile']
oauth = OAuth2Session(constants.client_id, redirect_uri=redirect_uri, scope=scope)

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
    req = requests.Request()

    #get the auth token from Google
    token = oauth.fetch_token(
        'https://accounts.google.com/o/oauth2/token',
        authorization_response=request.url,
        client_secret=constants.client_secret)
    #verify the token
    id_info = id_token.verify_oauth2_token( 
    token['id_token'], req, constants.client_id)
    #if token issuer is not accounts.google.com, don't trust it
    if id_info['iss'] != "accounts.google.com":
        raise ValueError('Incorrect Issuer')
    #set uid to the 'sub' attribute of the token
    uid = id_info['sub']
    #get the list of owners from datastore
    query = client.query(kind=constants.owners)
    results = list(query.fetch())
    #search through results
    for e in results:
        #set the 'id' attribute for each result
        e['id'] = e.key.id
        #if the user_id matches uid, the user exists in datastore already, so return their user_id and their JWT
        if (e['user_id'] ==  uid):
            return "Your user id: \n" + e['user_id'] + ", your JWT is: \n" + token['id_token']
    #else, make a new owner in datastore
    new_owner = datastore.entity.Entity(key=client.key(constants.owners))
    #try to set the user_id attribute and add a boat list to the new owner
    try:
        new_owner.update({"user_id": uid, "boats": []})
    #if it can't be done, return 400
    except KeyError:
        response_body = {}
        response_body['Error'] = "The request object is missing at least one of the required attributes"
        return (json.dumps(response_body), 400)
    #add the new owner to datastore
    client.put(new_owner)
    #set 'id' and 'self' attributes for the new_owner
    new_owner["id"] = str(new_owner.key.id)
    new_owner["self"] = request.url + '/' + str(new_owner.key.id)
    #return the user_id and JWT to the new user
    return "Your user id: \n" + e['user_id'] + ", your JWT is: \n" + token['id_token']

# This page demonstrates verifying a JWT. id_info['email'] contains
# the user's email address and can be used to identify them
# this is the code that could prefix any API call that needs to be
# tied to a specific user by checking that the email in the verified
# JWT matches the email associated to the resource being accessed.
@app.route('/verify-jwt')
def verify():
    req = requests.Request()

    id_info = id_token.verify_oauth2_token( 
    request.args['jwt'], req, constants.client_id)

    return repr(id_info) + "<br><br> the user is: " + id_info['email']

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)