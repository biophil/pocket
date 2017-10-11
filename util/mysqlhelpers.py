#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 26 20:38:21 2017

@author: pnbrown
"""


import mysql.connector
from mysql.connector import errorcode
from mysql.connector import DataError, DatabaseError, InterfaceError
import json


TABLES = []


TABLES.append(['accounts',
    "CREATE TABLE `accounts` ("
    "  `acct_id` INT NOT NULL AUTO_INCREMENT,"
    "  `name` VARCHAR(16) NOT NULL,"
    "  `balance` INT NOT NULL DEFAULT 0,"
    "  `in_genesis` BOOL NOT NULL DEFAULT FALSE,"
    "  PRIMARY KEY (`acct_id`), UNIQUE KEY `name` (`name`),"
    "  KEY `balance` (`balance`),"
    "  KEY `in_genesis` (`in_genesis`))"])

TABLES.append(['confirmer_accounts',
    "CREATE TABLE `confirmer_accounts` ("
    "  `confirmer_id` INT NOT NULL AUTO_INCREMENT,"
    "  `name` VARCHAR(16) NOT NULL,"
    "  `fees_collected` INT NOT NULL DEFAULT 0,"
    "  PRIMARY KEY (`confirmer_id`), UNIQUE KEY `name` (`name`))"])

TABLES.append(['op_types',
    "CREATE TABLE `op_types` ("
    "  `type_id` INT NOT NULL AUTO_INCREMENT,"
    "  `name` VARCHAR(100) NOT NULL,"
    "  PRIMARY KEY (`type_id`),"
    "  KEY `name` (`name`))"])

TABLES.append(['ops',
    "CREATE TABLE `ops` ("
    "  `op_id` INT NOT NULL AUTO_INCREMENT,"
    "  `trxid` VARCHAR(40) NOT NULL,"
    "  `steem_block` INT NOT NULL,"
    "  `timestamp` DATETIME NOT NULL,"
    "  `account` VARCHAR(16) NOT NULL,"
    "  `type_id` INT NOT NULL,"
    "  PRIMARY KEY (`op_id`),"
    "  KEY `trxid` (`trxid`),"
    "  KEY `steem_block` (`steem_block`),"
    "  KEY `account` (`account`),"
    "  KEY `type_id` (`type_id`),"
    "  FOREIGN KEY (`type_id`) REFERENCES op_types(`type_id`))"])

TABLES.append(['del_send',
    "CREATE TABLE `del_send` ("
    "  `del_send_id` INT NOT NULL AUTO_INCREMENT," # to find ident SELECT ident FROM send WHERE del_send_id=desired_id
    "  `op_id` INT NOT NULL,"
    "  PRIMARY KEY (`del_send_id`),"
    "  FOREIGN KEY (`op_id`) REFERENCES ops(`op_id`))"])

TABLES.append(['send',
    "CREATE TABLE `send` ("
    "  `send_id` INT NOT NULL AUTO_INCREMENT,"
    "  `op_id` INT NOT NULL,"
    "  `ident` VARCHAR(1000) NOT NULL,"
    "  `to_account` VARCHAR(16) NOT NULL,"
    "  `amount` INT NOT NULL,"
    "  `fee` INT NOT NULL DEFAULT 1,"
    "  `memo` TEXT DEFAULT NULL,"
    "  `del_send_id` INT DEFAULT NULL," # null if comment wasn't deleted
    "  PRIMARY KEY (`send_id`),"
    "  KEY `ident` (`ident`),"
    "  KEY `to_account` (`to_account`),"
    "  FOREIGN KEY (`op_id`) REFERENCES ops(`op_id`),"
    "  FOREIGN KEY (`del_send_id`) REFERENCES del_send(`del_send_id`))"])

TABLES.append(['del_gconf',
    "CREATE TABLE `del_gconf` ("
    "  `del_gconf_id` INT NOT NULL AUTO_INCREMENT," # to find ident SELECT ident FROM send WHERE del_send_id=desired_id
    "  `op_id` INT NOT NULL,"
    "  PRIMARY KEY (`del_gconf_id`),"
    "  FOREIGN KEY (`op_id`) REFERENCES ops(`op_id`))"])

TABLES.append(['gconf',
    "CREATE TABLE `gconf` ("
    "  `gconf_id` INT NOT NULL AUTO_INCREMENT,"
    "  `op_id` INT NOT NULL,"
    "  `ident` VARCHAR(1000) NOT NULL,"
    "  `fee` INT NOT NULL DEFAULT 1,"
    "  `del_gconf_id` INT DEFAULT NULL," # null if comment wasn't deleted
    "  PRIMARY KEY (`gconf_id`),"
    "  KEY `ident` (`ident`),"
    "  FOREIGN KEY (`op_id`) REFERENCES ops(`op_id`),"
    "  FOREIGN KEY (`del_gconf_id`) REFERENCES del_gconf(`del_gconf_id`))"])

TABLES.append(['send_confirmation',
    "CREATE TABLE `send_confirmation` ("
    "  `send_conf_id` INT NOT NULL AUTO_INCREMENT,"
    "  `op_id` INT NOT NULL,"
    "  `send_id` INT NOT NULL,"
    "  `ident` VARCHAR(1000) NOT NULL," # of post containing confirmation
    "  `confirmer` VARCHAR(16) NOT NULL,"
    "  PRIMARY KEY (`send_conf_id`),"
    "  FOREIGN KEY (`op_id`) REFERENCES ops(`op_id`),"
    "  FOREIGN KEY (`send_id`) REFERENCES send(`send_id`))"])

TABLES.append(['gconf_confirmation',
    "CREATE TABLE `gconf_confirmation` ("
    "  `gconf_conf_id` INT NOT NULL AUTO_INCREMENT,"
    "  `op_id` INT NOT NULL,"
    "  `gconf_id` INT NOT NULL,"
    "  `ident` VARCHAR(1000) NOT NULL," # of post containing confirmation
    "  `confirmer` VARCHAR(16) NOT NULL,"
    "  PRIMARY KEY (`gconf_conf_id`),"
    "  FOREIGN KEY (`op_id`) REFERENCES ops(`op_id`),"
    "  FOREIGN KEY (`gconf_id`) REFERENCES gconf(`gconf_id`))"])


class MySQLWrapper :
    
    def __init__(self,lazy=True) :
        try :
            with open('mysql_config.json') as cfgfile :
                self.cfg = json.load(cfgfile)
        except FileNotFoundError :
            cfg = {'database':'',
                   'host':'',
                   'user':'',
                   'password':'',
                   'raise_on_warnings':True}
            with open('mysql_config.json','w') as cfgfile :
                json.dump(cfg,cfgfile)
            raise FileNotFoundError('Please populate mysql_config.json file with relevant values')

        self.cnx = self.getMySQLCnx()
        self.createTables()
        self.lazy = lazy
        # to do: make sure that table op_types has all the type names in it
        
    def getMySQLCnx(self) :
        cnx = mysql.connector.connect(**self.cfg)
        return cnx
    
    def getCursor(self) :
        return self.cnx.cursor(prepared=True)
    
    def createTables(self) :
        cursor = self.getCursor()
        for table in TABLES:
            try:
                print("Creating table {}: ".format(table[0]), end='')
                cursor.execute(table[1])
            except mysql.connector.Error as err:
                if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                    print("already exists.")
                else:
                    print(err.msg)
            else:
                print("OK")
        cursor.close()
        
    def trxid_in_db(self,trxid) :
        cur = self.getCursor()
        q = "SELECT 1 FROM ops WHERE trxid=%s"
        cur.execute(q,(trxid,))
        to_ret = not (cur.fetchone() is None)
        cur.close()
        return to_ret
    
    def acct_in_db(self,account) :
        cur = self.getCursor()
        q = "SELECT 1 FROM accounts WHERE name=%s"
        cur.execute(q,(account,))
        to_ret = not (cur.fetchone() is None)
        cur.close()
        return to_ret
        
        
        
    def add_op(self,mist_op,this_block,trxid,timestamp) :
        # cases: 
        # send
        # send_confirm
        # gconf
        # gconf_confirm
        # del_send
        # del_gconf
        pass
    
        
    def credit_genesis(self,account,steem_block,trxid,timestamp) :
        cur = self.getCursor()
        # this is the lazy implementation where we don't check if what's there is good
        if not self.trxid_in_db(trxid) : # doesn't handle 2 ops in one trx!
            q = "INSERT INTO ops (trxid,steem_block,timestamp,account,type_id) "
            q += "VALUES ("+','.join(['%s']*4)+','
            q += "(SELECT type_id FROM op_types WHERE name='claim'))"
            cur.execute(q,(trxid,steem_block,timestamp,account))
            self.cnx.commit()
            if self.acct_in_db(account) :
                # increase account's balance by genesis amount
                pass
        else :
            # if it's in, we need to decide what to do
            pass
        cur.close()
            
    


#TABLES.append(['accounts',
#    "CREATE TABLE `accounts` ("
#    "  `acct_id` INT NOT NULL AUTO_INCREMENT,"
#    "  `name` VARCHAR(16) NOT NULL,"
#    "  `balance` INT NOT NULL DEFAULT 0,"
#    "  `in_genesis` BOOL NOT NULL DEFAULT FALSE,"
#    "  PRIMARY KEY (`acct_id`), UNIQUE KEY `name` (`name`),"
#    "  KEY `balance` (`balance`),"
#    "  KEY `in_genesis` (`in_genesis`))"])
