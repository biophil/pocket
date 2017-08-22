#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 23 13:52:31 2017

@author: pnbrown
"""


import util.constants as const
import re

from steem.utils import construct_identifier
def constIdent(author,slug) :
    return construct_identifier(author,slug)

sendCommand = const.TOKEN_NAME + 'send:'

def parseSend(send) :
    # send is a string "send:<amount>@<to_account>,<optional-memo>"
    # re.match('send:)
    match = re.match('^'+sendCommand+'\d+@[a-z][a-z0-9\-.]{2,15}(,|$)',send)
    if match is not None:
        amount = ''
        to_account = ''
        memo = ''
        atfound = False
        comfound = False
        for ch in send[len(sendCommand):] :
            if not atfound :
                if ch=='@' :
                    atfound = True
                else :
                    amount += ch
            elif not comfound :
                if ch==',' :
                    comfound = True
                else :
                    to_account += ch
            else :
                memo += ch
        # deal with decimal:
        amount = int(amount)
        if not (amount=='' or to_account=='') :
            return amount,to_account,memo
    else : 
        return
    
def getConfirmPayload(body) :
    # looks at the body of a post to see if it's a properly-formatted confirmation
    # if format is proper, it returns the operation that it's supposedly confirming
    # otherwise, it returns None
    #
    # body should be a string :
    # "Successful Send of <send_amount>\n"
    # "Sending Account: <from_account_name>\n"
    # "Receiving Account : <to_account_name>\n"
    # "New sending account balance: <from_account_balance>\n"
    # "New receiving account balance: <to_account_balance>\n"
    # "Fee: <fee>\n"
    # "Steem trxid: <trxid>\n"
    # "<arbitrary string>"
    #
    # first check if it's a Genesis confirmation:
    genesis_conf_start = 'Success! You claimed a genesis stake of ' + str(const.GENESIS_CREDIT) + '.\n'
    if body.startswith(genesis_conf_start) :
        if body[len(genesis_conf_start):].startswith('trxid:') :
            idx = len(genesis_conf_start)+len('trxid:')
            trxid_len = body[idx:].find('\n')
            if trxid_len > 0 :
                extracted_op = {'trxid':body[idx:(idx+trxid_len)]}
                return extracted_op
    body_work = body
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
    extracted_op = {}
    try : 
        for descr,label in zip(descStrings,payloadLabels) :
            if body_work.startswith(descr) :
                body_work = body_work[len(descr):]
                # now everything until first \n is payload
                payload_length = body_work.find('\n')
                if payload_length > -1 :
                    payload_str = body_work[0:payload_length]
                    extracted_op[label] = parseConfirmPayload(payload_str,label)
                    body_work = body_work[(len(payload_str)+1):] # skip the \n that we know is there
                else :
#                    print('second. body: ' + body_work)
                    return None
            else :
#                print('first. body: ' + body_work)
                return None
    except IndexError as er:
        print(str(er))
        return None
    except TypeError as er :
        print(str(er))
        return None
    return extracted_op
        
def parseConfirmPayload(payload_str,label) :
    str_labels = ['from_account','to_account','trxid']
    if label in str_labels :
        return payload_str
    else : # then proper format is decimal with precision 3 and at least one leading digit
        num_match = re.match('\d+',payload_str)
        if num_match is not None :
            return int(payload_str)
        else :
            raise TypeError('Numeric format incorrect: ' + payload_str)
        return None
    
def parseConfirm(associated_ops,steem_op,parentIdent) :
    # checks the confirmation post in steem_op against the requested confirmation in op_to_confirm
    # body should be a string "Success!\nNew sending account balance: <from_account_balance>\nNew receiving account balance: <to_account_balance>\n"
    # an issue here is that we parse the entire confirmation before we know if it's actually a needed one.
    #
    body = steem_op[1]['body']
    extracted_op = getConfirmPayload(body)
    if extracted_op is not None :
        if extracted_op['trxid'] in associated_ops :
            op_to_confirm = associated_ops[extracted_op['trxid']]
            if op_to_confirm['type'] != 'genesis_confirm' :
                for label in extracted_op.keys() : # check if if fits...
                    if extracted_op[label] != op_to_confirm[label] :
                        return None # discrepancy found, so exit
            mist_op = {'type':'confirmation'}
            mist_op['confirmer'] = steem_op[1]['author']
            mist_op['fee'] = op_to_confirm['fee']
            mist_op['associated_ident'] = parentIdent
            mist_op['associated_trxid'] =  extracted_op['trxid']
            return mist_op
    return None
        
def _parentIsGenesis(op) :
    return (op[1]['parent_author'] == const.GENESIS_ACCOUNT) and (op[1]['parent_permlink'] == const.GENESIS_PERMLINK)

def _isPocketSend(op) :
    return op[1]['body'][0:len(sendCommand)] == sendCommand

def parseOP(op,trxid,DB) :
    # parses a Steem blockchain op and returns the Mist op
    # returns None if improperly-formatted Mist op
    try :
        if op[0] == 'comment' :
            if _parentIsGenesis(op) or _isPocketSend(op) :
                body = op[1]['body']
                if body.startswith(sendCommand) :
                    sendTup = parseSend(body) # guaranteed to be int
                    if sendTup is not None :
                        amount,to_account,memo = sendTup
                        from_account = op[1]['author']
                        mist_op = {'type':'send'}
                        mist_op['to_account'] = to_account
                        mist_op['from_account'] = from_account
                        mist_op['memo'] = memo
                        mist_op['amount'] = amount
                        mist_op['fee'] = const.FEE
                        mist_op['trxid'] = trxid
                        return mist_op
                elif body.startswith('confirm') :
                    mist_op = {'type':'genesis_confirm'}
                    mist_op['account'] = op[1]['author']
                    mist_op['fee'] = const.FEE
                    mist_op['trxid'] = trxid
                    return mist_op
            else : # check if it's a confirmation
                parentIdent = constIdent(op[1]['parent_author'],op[1]['parent_permlink'])
                associated_ops = DB.get_ops_for_ident(parentIdent)
                # associated_ops is a dictionary of trixd:mist_op pairs
                if associated_ops is not None :
                    mist_op = parseConfirm(associated_ops,op,parentIdent)
                    return mist_op
        elif op[0] == 'delete_comment' :
            ident = constIdent(op[1]['author'],op[1]['permlink'])
            ops_to_confirm = DB.get_ops_for_ident(ident) # unconfirmed ops associated with this ident
            if ops_to_confirm is not None :
                ops_to_remove = ops_to_confirm.copy()
                for trxid in ops_to_remove :
                    # return fee to receiving account because now confirmation is impossible
                    op_to_confirm = ops_to_confirm[trxid]
                    fee_credit_account = ''
                    if op_to_confirm['type'] == 'send' :
                        fee_credit_account = op_to_confirm['to_account']
                    else : # assume it's a genesis_confirm
                        fee_credit_account = op_to_confirm['account']
                    print('post deleted; crediting fee to ' + fee_credit_account)
                    DB.increase_account_balance(fee_credit_account,op_to_confirm['fee'])
                    DB.remove_pending_confirmation(ident,op_to_confirm['trxid'])
    except KeyError :
        pass
    except IndexError :
        pass
    

def balance_to_string(balance_int) :
    balance_int_str = str(balance_int)
    if len(balance_int_str) < 4 :
        balance_str = '0.' + '0'*(3-len(balance_int_str)) + balance_int_str
    else :
        balance_str = balance_int_str[0:-3] + '.' + balance_int_str[-3:]
    return balance_str