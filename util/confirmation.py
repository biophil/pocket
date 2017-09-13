#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 19:33:01 2017

@author: pnbrown
"""
import steem as st
import util.validators as val # NOTE: shouldn't import val. Make a helpers module
import util.constants as const
from steembase.exceptions import PostDoesNotExist, RPCError
from util.db import pickleit
from util.db import unpickleit
from util.validators import constIdent
import datetime
import random

## note: this module is only for stuff that deals with posting confirmations,
## NOT validating them.

str_labels = ['from_account','to_account','trxid']

def format_amount(int_amount) :
    # somewhere deep in the Git history is code to do this for decimals
    if int_amount < 0 :
        raise TypeError('amount cannot be less than zero.')
    else : 
        return str(int_amount)

def confirm_op(ident,needed_confirmation,s,confirmer_account,confirm_message) :
    # ident is for post to reply to
    # needed_confirmation is mist_op that needs to be confirmed
    descStrings = ['Successful Send of ']
    descStrings += ['Sending Account: ']
    descStrings += ['Receiving Account: ']
    descStrings += ['New sending account balance: ']
    descStrings += ['New receiving account balance: ']
    descStrings += ['Fee: ']
    descStrings += ['Steem trxid: ']
    payloadLabels = ['amount']
    payloadLabels += ['from_account']
    payloadLabels += ['to_account']
    payloadLabels += ['new_from_balance']
    payloadLabels += ['new_to_balance']
    payloadLabels += ['fee']
    payloadLabels += ['trxid']
    
    
    # first get a list of valid confirmations already posted to this ident
    try :
        top_level = st.post.Post(ident,s)
    except PostDoesNotExist :
        pass
    else :
        try :
            possible_confirmations = [val.getConfirmPayload(reply.body) for reply in top_level.get_replies()]
        except AttributeError :
            return
        found_match = False
        # for each reply, I need to check if it corresponds to the one we need.
        # if no reply corresponds to the one we need, then post a conf.
        # Or, if every reply does *not* match, then post a conf.
        for poss_conf in possible_confirmations :
            if poss_conf is not None :
                this_not_match = False
                for label in poss_conf : 
                    if needed_confirmation[label] != poss_conf[label] :
                        # being here means that poss_conf is *not* a match
                        this_not_match = True
                        break # don't waste time checking the rest
                if not this_not_match : # got thru one without a discrepancy
                    found_match = True
                    break
        if not found_match : # found match means I found one conf that is completely right
            body = ''
            if needed_confirmation['type'] == 'send' :
                for string,label in zip(descStrings,payloadLabels) :
                    if label in str_labels :
                        conf_data = needed_confirmation[label]
                    else :
                        conf_data = format_amount(needed_confirmation[label])
                    body += string + conf_data + '\n'
            elif needed_confirmation['type'] == 'genesis_confirm' :
                body += 'Success! You claimed a genesis stake of ' + str(const.GENESIS_CREDIT) + '.\n'
                body += 'trxid:' + needed_confirmation['trxid'] + '\n'
            body += confirm_message
            try :
                s.commit.post('',body,confirmer_account,reply_identifier=ident)
            except RPCError as er :
                print(er)
                pass
            else :
                print('confirmed: ' + needed_confirmation['trxid'])
                
class Voter :
    
    vote_wait_interval = datetime.timedelta(seconds=6)
    votes_fname = '.votes'
    
    def __init__(self,voting_account,s,active=False) :
        self.account = voting_account
        self.steem = s
        self.active = active
        self.pending_votes = set()
        self.last_vote_time = datetime.datetime.now()
        try :
            self.votes_cast = unpickleit(self.votes_fname)
        except FileNotFoundError :
            self._reset()
            
    def _reset(self) :
        self.votes_cast = set()
        self.save()
        
    def _load(self) :
        try :
            self.votes_cast = unpickleit(self.votes_fname)
        except :
            print('no file! If desired, run ._reset() ro create one')
            
    def save(self) :
        pickleit(self.votes_cast,self.votes_fname)
        
    def mark_for_voting(self,op) :
        # add vote if active and if it's not for myself
        if self.active :
            if op[1]['author'] != self.account :
                ident = constIdent(op[1]['author'],op[1]['permlink'])
                # make sure ident isn't in cast or pending:
                if ident not in self.votes_cast.union(self.pending_votes) :
                    self.pending_votes.add(ident)

    def vote(self) :
        # if active, vote a single random ident from pending
        if self.active :
            if len(self.pending_votes) > 0 :
                now = datetime.datetime.now()
                if now - self.vote_wait_interval > self.last_vote_time :
                    try :
                        ident_to_vote = random.choice(list(self.pending_votes))
                        self.steem.commit.vote(ident_to_vote,10,self.account)
                    except PostDoesNotExist :
                        self.pending_votes.remove(ident_to_vote)
                    except RPCError as er:
                        # this isn't great; we'll see what sorts of errors come
                        print(er)
                        self.last_vote_time = datetime.datetime.now()
                        pass
                    else :
                        print('voted for confirmation ' + ident_to_vote)
                        self.pending_votes.remove(ident_to_vote)
                        self.votes_cast.add(ident_to_vote)
                        self.last_vote_time = datetime.datetime.now()
                        
                
            