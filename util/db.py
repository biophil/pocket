#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 21 21:03:55 2017

@author: pnbrown
"""

import pickle
import util.constants as const
import random


from steem.utils import construct_identifier
def constIdent(author,slug) :
    return construct_identifier(author,slug)


class Mist_DB :
    def __init__(self,db_fname='.db') :
        self.db_fname=db_fname
        try :
            self._db = unpickleit(self.db_fname)
        except FileNotFoundError :
            self._reset()
        
    def _reset(self) :
        self._db = {}
        self._db['last_block'] = const.START_BLOCK-1
        self._db['accounts'] = {}#{'philipnbrown':{'balance':1000000}}
        self._db['pending_confirmations'] = {}
        self._db['pending_accounts'] = {}
        self._db['eligible_accounts'] = set()
        self._db['pending_genesis_confirms'] = set()
        self._db['active'] = False
        self._db['genesis_active'] = False
        self._db['genesis_in_block'] = -1
        self._db['genesis_last_block'] = -1
        self.save()
        
    def _load(self) :
        try :
            self._db = unpickleit(self.db_fname)
        except FileNotFoundError :
            self._reset()
        
        
    def save(self) :
        pickleit(self._db,self.db_fname)
        
    def update_last_block(self,new_last_block) :
        self._db['last_block'] = new_last_block
        
    def last_parsed_block(self) :
        return self._db['last_block']
    
    def active(self) :
        return self._db['active']
    
    def genesis_active(self) :
        return self._db['genesis_active']
    
    def past_genesis_interval(self,block) :
        return block > self._db['genesis_last_block']
        
    def activate(self) :
        self._db['active'] = True
        
    def activate_genesis(self,block) :
        self._db['genesis_active'] = True
        self._db['genesis_in_block'] = block
        self._db['genesis_last_block'] = block + const.GENESIS_INTERVAL
        pickleit(self._db['pending_accounts'],'pending_backup.p')
        pickleit(self._db['eligible_accounts'],'eligible_backup.p')
        self._db['pending_accounts'] = {}
        print('GENESIS ACTIVATED!')
        
    def deactivate_genesis(self) :
        self._db['genesis_active'] = False
        self._db['eligible_accounts']=set()
        print('GENESIS DEACTIVATED')
    
    def credit_genesis(self,account) :
        self.increase_account_balance(account,const.GENESIS_CREDIT)
        try :
            self._db['eligible_accounts'].remove(account)
        except KeyError : # this catches the corner case that the genesis account is not technically eligible
            pass
        self._db['pending_genesis_confirms'].add(account)
    
    def get_account_balance(self,account) :
        try :
            return self._db['accounts'][account]['balance']
        except KeyError :
            return 0
        
    def increase_account_balance(self,account,amount) :
        try : 
            self._db['accounts'][account]['balance'] += amount
            print(str(amount) + ' added to account ' + account)
        except KeyError :
            self._db['accounts'][account] = {'balance':amount}
            print(str(amount) + ' added to account ' + account)
        
    def decrease_account_balance(self,account,amount) :
        if self.get_account_balance(account) >= amount :
            self._db['accounts'][account]['balance'] -= amount
            print(str(amount) + ' deducted from account ' + account)
        else :
            print('Insufficient balance in account ' + account)
        
    def add_send(self,mist_op) :  
        send_successful = False
        from_account = mist_op['from_account']
        to_account = mist_op['to_account']
        amount = mist_op['amount']
        if amount > 0 :
            try :
                if self._db['accounts'][from_account]['balance'] >= amount :
                    self._db['accounts'][from_account]['balance'] -= amount
                    send_successful = True
                    print(str(amount) + ' deducted from account ' + from_account)
                else : 
                    print('insufficient balance in account ' + from_account)
            except KeyError :
                print('I have no record of account ' + from_account)
            if send_successful :
                try : 
                    self._db['accounts'][to_account]['balance'] += amount - mist_op['fee']
                    print(str(amount - mist_op['fee']) + ' added to account ' + to_account)
                except KeyError :
                    self._db['accounts'][to_account] = {'balance':amount - mist_op['fee']}
                    print(str(amount - mist_op['fee']) + ' added to account ' + to_account)
        else :
            print('amount of send must be at least 1.')
        return send_successful
        
        
    def add_confirmation(self,mist_op) :
        if mist_op['fee'] > 0 :
            self.increase_account_balance(mist_op['confirmer'],mist_op['fee'])
        self.remove_pending_confirmation(mist_op['associated_ident'],mist_op['associated_trxid'])
        return True
    
    def add_genesis_confirm(self,mist_op) :
        account = mist_op['account']
        if account in self._db['pending_genesis_confirms'] :
            if self.get_account_balance(account) > mist_op['fee'] :
                self.decrease_account_balance(account,mist_op['fee'])
                self._db['pending_genesis_confirms'].remove(account)
                return True
        return False
                
    
    def add_op(self,mist_op) :
        if mist_op['type'] == 'send' :
            return self.add_send(mist_op)
        if mist_op['type'] == 'confirmation' :
            return self.add_confirmation(mist_op)
        if mist_op['type'] == 'genesis_confirm' : # this is a genesis confirmation request
            return self.add_genesis_confirm(mist_op)
        
    def enqueue_for_confirmation(self,mist_op,op) :
        # mist_op is assumed to be valid
        ident = constIdent(op[1]['author'],op[1]['permlink'])
        to_add = mist_op.copy()
        if mist_op['type'] == 'send' :
            to_add['new_from_balance'] = self.get_account_balance(to_add['from_account'])
            to_add['new_to_balance'] = self.get_account_balance(to_add['to_account'])
        try :
            self._db['pending_confirmations'][ident][to_add['trxid']] = to_add
        except KeyError :
            self._db['pending_confirmations'][ident] = {}
            self._db['pending_confirmations'][ident][to_add['trxid']] = to_add
#        print(ident)
        pass
        
    def remove_pending_confirmation(self,ident,trxid) :
        # Remove confirmation associated with trxid
        self._db['pending_confirmations'][ident].pop(trxid)
        # then check if the ident can be removed as well:
        if len(self._db['pending_confirmations'][ident]) == 0 :
            self._db['pending_confirmations'].pop(ident)
    
    def get_ops_for_ident(self,parentIdent) :
        try :
            return self._db['pending_confirmations'][parentIdent]
        except KeyError :
            return None
        
    def get_next_confirmation(self) :
        # return exactly one needed confirmation
        try :
            ident = random.choice(list(self._db['pending_confirmations']))
            trxid = random.choice(list(self._db['pending_confirmations'][ident]))
            return ident, self._db['pending_confirmations'][ident][trxid]
        except IndexError :
            return None
        
    def is_eligible(self,account) :
        return account in self._db['eligible_accounts']
    
    def increment_comment_count(self,account) :
        # assume that account is not already eligible, but nothing will break if it is.
        try : 
            self._db['pending_accounts'][account] += 1
        except KeyError :
            self._db['pending_accounts'][account] = 1
        if self._db['pending_accounts'][account] >= const.GENESIS_POSTS_TH :
            self._db['pending_accounts'].pop(account)
            self._db['eligible_accounts'].add(account)
            
    def get_total_supply(self) :
        return sum([self.get_account_balance(account) for account in self._db['accounts']])
    
    def get_top_accounts(self,K) :
        # return list of accounts with K largest balances
        acctlist = [(account,self.get_account_balance(account)) for account in self._db['accounts']]
        acctlist.sort(key=lambda x: x[1])
        return acctlist[-K:]
    
    def get_bottom_accounts(self,K) :
        # return list of accounts with K largest balances
        acctlist = [(account,self.get_account_balance(account)) for account in self._db['accounts']]
        acctlist.sort(key=lambda x: x[1])
        return acctlist[0:K]
        
        

        
def pickleit(topickle,fname) :
    with open(fname,'wb') as f :
        pickle.dump( topickle, f )
    
def unpickleit(fname) :
    with open(fname,'rb') as f :
        return pickle.load( f )
        