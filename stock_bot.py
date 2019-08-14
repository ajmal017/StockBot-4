
#import libraries
import re
import spacy
import string
import random
import json
import sqlite3
import datetime
from wxpy import *
from spacy.pipeline import EntityRecognizer
from iexfinance.stocks import Stock
from iexfinance.stocks import get_historical_data
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config

bot=Bot(cache_path=True) #wxpy, Wechat log in

iextoken="sk_241ec3b414e043bc842f964d54f0b868"
responses = {'greet': ['Hi!','Nice to meet you!'],     #define response format
             'goodbye':['Bye','See you later'],
             'intro': ['I am stock bot, I can tell you stock information! What do you want to know?'],
             'stock':'Please tell me the company name and the kind of imformation. You can ask: tell me about Apple',
             'latestPrice':'price of {}: {},do you want to know the higest price during the last 52 weeks?',
             'volume':'volume of {}: {}',
             'marketCap':'marketCap of {}: {}',
             'affirm':['What do you mean','What do you want to say'],
             'thank':['You are welcome','My pleasure'],
             'default':'Sorry, I cannot understand'
            }

state=0   #global variables
intent=None
company=None
info=None
pending=0 #if a pending exists

nlp = spacy.load("en_core_web_md")  
trainer = Trainer(config.load("config_spacy.yml"))   # Create a trainer that uses this config
training_data = load_data('train_data.json')  #  Load the training data
interpreter = trainer.train(training_data)  # Create an interpreter by training the model

def interpret(m): #intent recognition
    m1=m.lower()
    if 'price' in m1 or 'Price' in m1:   #check key words
        return 'latestPrice'
    if 'marketcap' in m1 or 'market cap' in m1:
        return 'marketCap'
    if 'volume' in m1 or 'Volume' in m1:
        return 'volume'
    if 'histor' in m1 or 'Histor' in m1:
        return 'history'
    return None
    
def getsymbol(name):   #get stock symbol
    for t in companylist:
        if name in t['Name'] or t['Symbol']==name:
            return t['Symbol']
    return 'No'
 
def auth(uid):   #check user id
    t = (uid,)
    conn = sqlite3.connect('users.db') #connect to database
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE uid=?', t)
    if c.fetchall()==[t] :
        return 1
    return 0

def clear(): #reset global variables
    state=0
    pending=0
    intent=None
    company=None
    info=None

def gethistory(m): #get historical data
    st = re.compile('[Ff]rom (.*) to (.*)')   #find start and end date, using regular expression
    match = re.search(st,m)
    if match is None: 
        return None
    start = datetime.datetime.strptime(match.group(1),'%Y %m %d') 
    end = datetime.datetime.strptime(match.group(2),'%Y %m %d')
    return get_historical_data(company, start, end, token=iextoken)

my_friend = bot.friends().search('FriendName')[0]   #search for a Wechat friend to talk to
@bot.register(my_friend)  
def respond(msg):
    hascp=0 #if a company name exists in user message
    strongint=1
    mg=msg.text
    global state
    global pending #if pending action exists
    global intent
    global info
    global company
    intent=interpret(mg)  #intent recognition
    it=interpreter.parse(mg)["intent"] #intent_recognition(with rasa_nlu)
    if intent==None:    #if no intent found in function 'interpret', use rasa_nlu    
        intent=it['name']
        strongint=0     

    if state==0: #state=0:on start
        if it['confidence']<0.15:  #intent is not clear
            return responses['default']
        if intent=="goodbye":
            clear()
            return random.choice(responses[intent])
        if intent=="greet" or intent=="intro":
            return random.choice(responses[intent])
        state=1 #move to state 1
        return 'Log in first. What is your user id?'

    if state==1:  #state=1:check user id
        if auth(mg):
            state=2 #move to state2
            return 'Log in successfully! What do you want to know'
        return 'Wrong id!'
        
    if state==2:   #state=2:chat
        
        doc=nlp (mg)
        for ent in doc.ents:   #entity extrction(with spacy)
            if ent.label_=='ORG':              
                company = getsymbol(ent.text) #get company name
                hascp=1
        if pending==1:
            pending=0      #clear pending
            if intent=='affirm':  #do pending action
                return 'highest price: {}'.format(info['week52High'])
            return 'What else do you want to know'
        if hascp==1  and strongint==0:  #company name exists in message but a clear intent does not 
            return 'What kind imformation do you want? You can ask like this: tell me the price of Apple'
        if intent=="stock":
            return responses[intent]
        if it['confidence']<0.15:  #intent is not clear
            return responses['default']
        if intent=="goodbye":
            clear()
            return random.choice(responses[intent])

        pending=0   #clear pending
        if  'histor' in mg:
            if gethistory(mg)==None:
                state=3   #move to state3
                return 'Tell me the start date and end date'
            return gethistory(mg)
        if intent=='intro' or intent=='greet' or intent=='thank' or intent=='affirm':
            return random.choice(responses[intent])
        
        if intent=="latestPrice":  #intent is price, ask if the user want highest price during last 52 weeks
            pending=1  #create pending
        info = Stock(company, token=iextoken).get_quote() #get stock imformation
        return responses[intent].format(company,info[intent])
    
    if state==3:  #state=3:historical data
        if gethistory(mg)==None:
            state=2    #move to state2
            return 'Wrong date'
        state=2
        return gethistory(mg)

#companylist=[] #paste the companylist here
bot.join() #block process
