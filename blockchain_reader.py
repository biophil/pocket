#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 21 20:54:53 2017

@author: pnbrown
"""

import steem as st
from datetime import datetime,timedelta
import time
import json
import logging
import sys

import util.db as db
import util.validators as val
import util.constants as const
import util.confirmation as conf
import util.mysqlhelpers as msh

DB = db.Mist_DB()
MySQL = msh.MySQLWrapper()
logging.basicConfig(filename='ops.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logging.getLogger("urllib3.util.retry").setLevel(logging.ERROR)
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

try :
    with open('config.json') as cfgfile :
        cfg = json.load(cfgfile)
except FileNotFoundError :
    cfg = {'confirmer-account':'',
           'confirmer_key':'',
           'nodes':[''],
           'confirm_message':'',
           'confirmation_active':True,
           'vote_on_valid_confs':True}
    with open('config.json','w') as cfgfile :
        json.dump(cfg,cfgfile)
    raise FileNotFoundError('Please populate config.json file with relevant values')

try :
    confirmer_account = cfg['confirmer-account']
    confirmer_key = cfg['confirmer_key']
    nodes = cfg['nodes']
    confirm_message = cfg['confirm_message']
    confirmation_active = bool(cfg['confirmation_active'])
    vote_on_valid_confs = bool(cfg['vote_on_valid_confs'])
except KeyError as er:
    raise KeyError('You may have an outdated version of the config.json file. Back yours up, delete it, and try again!')

if nodes==[''] :
    if confirmer_key == '' :
        s = st.Steem()
    else :
        s = st.Steem(keys = [confirmer_key])
else :
    if confirmer_key == '' :
        s = st.Steem(nodes=nodes)
    else :
        s = st.Steem(nodes=nodes,keys=[confirmer_key])
steem = s.steemd
#steem = stm.steemd
bc = st.blockchain.Blockchain(s)

confirmation_wait_time = 21 # seconds
confirmation_wait_timedelta = timedelta(seconds=confirmation_wait_time)
last_confirmation_time = datetime.utcnow() - confirmation_wait_timedelta
block_interval = 3 # seconds

if len(sys.argv) > 1 :
    startup_behavior = sys.argv[1]
else :
    startup_behavior = 'normal'
    
if startup_behavior == 'replay-from-genesis' : # load pregenesis, overwrite db
    DB.from_json(fname='db_pregenesis.json',overwrite_local=True)
    DB.save()
elif startup_behavior == 'replay-from-0' :
    DB._reset()
elif startup_behavior == 'normal' :
    pass

last_parsed_block = DB.last_parsed_block()

while True : # can't proceed without this, so loop until we get it
    try :
        last_irr_block = s.last_irreversible_block_num
    except TypeError :
        pass
    else :
        break
next_irr_check_time = datetime.utcnow() + timedelta(seconds=block_interval)

activate_voting = vote_on_valid_confs and (confirmer_key!='')
v = conf.Voter(confirmer_account,s,active=activate_voting)

run = True
if run :
    try :
        while True :
            if last_parsed_block < last_irr_block :
#                print(str(last_parsed_block+1))
                with const.DelayedKeyboardInterrupt() : # don't let a SIGINT interrupt in the middle of a block
                    block = s.get_block(last_parsed_block + 1)
#                    print(this_block)
                    try :
                        trxs = zip(block['transactions'],block['transaction_ids'])
                    except TypeError as er :
                        logging.exception("block number: " + str(last_parsed_block + 1))
                        time.sleep(1)
                        continue # don't do anything in this loop; skip back and get a good block
                    this_block = last_parsed_block + 1
                    for trx,trxid in trxs :
                        for op in trx['operations'] :
                            if DB.active() :
                                mist_op = val.parseOP(op,trxid,DB) # check if it's properly formatted
                                if mist_op is not None :
                                    op_is_valid = DB.add_op(mist_op) # adds if it's valid
                                    print(str(mist_op) + " valid: " + str(op_is_valid))
                                    if op_is_valid :
                                        ts = st.utils.parse_time(block['timestamp'])
                                        MySQL.add_op(mist_op,op,this_block,trxid,ts)
                                        logging.info(str(mist_op))
                                    if op_is_valid and mist_op['type'] != 'confirmation' :
                                        DB.enqueue_for_confirmation(mist_op,op)
                                    if op_is_valid and mist_op['type'] == 'confirmation' :
                                        # then op is a confirm comment and we should consider voting it
                                        v.mark_for_voting(op,mist_op['associated_trxid'])
                                if DB.genesis_active() :
                                    if DB.past_genesis_interval(this_block) :
                                        DB.deactivate_genesis()
                                    else :
                                        # watch for reblogs of genesis post
                                        if op[0] == 'custom_json' :
                                            payload = json.loads( op[1]['json'])
                                            if payload[0] == 'reblog' :
                                                if payload[1]['author'] == const.GENESIS_ACCOUNT :
                                                    if payload[1]['permlink'] == 'genesis-'+const.TOKEN_NAME :
                                                        if DB.is_eligible(payload[1]['account']) :
                                                            ts = st.utils.parse_time(block['timestamp'])
                                                            account = payload[1]['account']
                                                            DB.credit_genesis(account)
                                                            MySQL.credit_genesis(account,this_block,trxid,ts)
                                try :
                                    v.delete_extra_confirmations()
                                    v.vote() # votes for others' confirms if voting is active
                                except TypeError as er :
                                    logging.exception("block number: " + str(last_parsed_block + 1))
                                    # this handles the random steem library NoneType problems
                            else : # if not active, we're pre-genesis
                                if op[0] == 'comment' : 
                                    if not DB.is_eligible(op[1]['author']) : # eligibility
                                        DB.increment_comment_count(op[1]['author'])
                                    if op[1]['author'] == const.GENESIS_ACCOUNT: # watch for genesis activation
                                        if op[1]['title'] == 'genesis-'+const.TOKEN_NAME :
                                            ts = st.utils.parse_time(block['timestamp'])
                                            DB.activate_genesis(this_block)
                                            DB.activate()
                                            DB.credit_genesis(const.GENESIS_ACCOUNT)
                                            MySQL.credit_genesis(const.GENESIS_ACCOUNT,this_block,trxid,ts)
                    last_parsed_block += 1 
                    DB.update_last_block(last_parsed_block)
                    if last_parsed_block%const.SAVE_INTERVAL == 0 :
                        DB.save()
                        v.save()
                    if last_parsed_block%100000 == 0 :
                        print(last_parsed_block)
                if confirmation_active and DB.active() :
                    if (datetime.utcnow() - last_confirmation_time) > confirmation_wait_timedelta :
                        confirm = DB.get_next_confirmation()
                        if confirm is not None :
#                            print('want to confirm this: ' + str(confirm[1]))
                            ident = conf.confirm_op(confirm[0],confirm[1],s,confirmer_account,confirm_message)
                            last_confirmation_time = datetime.utcnow()
                            if ident is not None :
                                v.add_posted_conf(confirm[1],ident)
            elif datetime.utcnow() > next_irr_check_time :
                try :
                    last_irr_block = s.last_irreversible_block_num
                except TypeError :
                    print('problem getting block number; will try again')
                next_irr_check_time = datetime.utcnow() + timedelta(seconds=block_interval)
            else :
                sleeptime = 1+(next_irr_check_time-datetime.utcnow()).seconds
                time.sleep(sleeptime)
    except KeyboardInterrupt:
        with const.DelayedKeyboardInterrupt() :
            DB.save()
            v.save()
        print("And Done.")
        

