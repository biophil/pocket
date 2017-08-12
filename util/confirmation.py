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

## note: this module is only for stuff that deals with posting confirmations,
## NOT validating them.

str_labels = ['from_account','to_account','trxid']

def format_amount(int_amount) :
    # somewhere deep in the Git history is code to do this for decimals
    if int_amount < 0 :
        raise TypeError('amount cannot be less than zero.')
    else : 
        return str(int_amount)

def confirm_op(ident,needed_confirmation,s,confirmer_account) :
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
        possible_confirmations = [val.getConfirmPayload(reply.body) for reply in top_level.get_replies()]
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
            body += 'enjoy!'
            try :
                s.commit.post('',body,confirmer_account,reply_identifier=ident)
            except RPCError :
                pass
            print('confirmed: ' + needed_confirmation['trxid'])