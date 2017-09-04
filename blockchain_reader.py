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

import util.db as db
import util.validators as val
import util.constants as const
import util.confirmation as conf

DB = db.Mist_DB()
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

last_parsed_block = DB.last_parsed_block()

#block_generator = bc.blocks(start=(last_parsed_block-1))

last_irr_block = s.last_irreversible_block_num
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
                    this_block = last_parsed_block + 1
#                    print(this_block)
                    for trx,trxid in zip(block['transactions'],block['transaction_ids']) :
                        for op in trx['operations'] :
                            if DB.active() :
                                mist_op = val.parseOP(op,trxid,DB) # check if it's properly formatted
                                if mist_op is not None :
                                    op_is_valid = DB.add_op(mist_op) # adds if it's valid
                                    print(str(mist_op) + " valid: " + str(op_is_valid))
                                    if op_is_valid :
                                        logging.info(str(mist_op))
                                    if op_is_valid and mist_op['type'] != 'confirmation' :
                                        DB.enqueue_for_confirmation(mist_op,op)
                                    if op_is_valid and mist_op['type'] == 'confirmation' :
                                        # then op is a confirm comment and we should consider voting it
                                        v.mark_for_voting(op)
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
                                                            DB.credit_genesis(payload[1]['account'])
                                v.vote() # votes for others' confirms if voting is active
                            else : # if not active, we're pre-genesis
                                if op[0] == 'comment' : 
                                    if not DB.is_eligible(op[1]['author']) : # eligibility
                                        DB.increment_comment_count(op[1]['author'])
                                    if op[1]['author'] == const.GENESIS_ACCOUNT: # watch for genesis activation
                                        if op[1]['title'] == 'genesis-'+const.TOKEN_NAME :
                                            DB.activate_genesis(this_block)
                                            DB.activate()
                                            DB.credit_genesis(const.GENESIS_ACCOUNT)
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
                            conf.confirm_op(confirm[0],confirm[1],s,confirmer_account,confirm_message)
                            last_confirmation_time = datetime.utcnow()
            elif datetime.utcnow() > next_irr_check_time :
                last_irr_block = s.last_irreversible_block_num
                next_irr_check_time = datetime.utcnow() + timedelta(seconds=block_interval)
            else :
                sleeptime = 1+(next_irr_check_time-datetime.utcnow()).seconds
                time.sleep(sleeptime)
    except KeyboardInterrupt:
        with const.DelayedKeyboardInterrupt() :
            DB.save()
            v.save()
        print("And Done.")
        

