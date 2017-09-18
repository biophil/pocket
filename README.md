## Pocket 

The POCKET, or Proof Of Concept Electronic Token (the K is silent), is a sub-token designed to operate on the Steem blockchain and interact with its users through a simple set of commands which users can invoke via interfaces such as [Steemit.com](http://Steemit.com) and [Busy.org](https://busy.org).

Please see [the POCKET announcement on Steemit](https://steemit.com/pocket/@biophil/pocket-announcement) and [the POCKET Genesis Post](https://steemit.com/pocket/@biophil/genesis-pocket).

## How to run a confirmer bot

Here are basic instructions for Ubuntu 16.04, they probably work fine on most Linux distribution with latest version of Python 3.5.

Install the python steem library and clone the Pocket repo:

```
pip3 install steem
git clone https://github.com/biophil/pocket
cd pocket
```


Run the `blockchain_reader.py` script:
```
python3 blockchain_reader.py
```

The first time, it will exit with the error message `FileNotFoundError: Please populate config.json file with relevant values`.
So open `config.json` with your favorite text editor and fill in the following fields; I've included here @pocket-a's values:

```
"confirm_message": "Thanks for using POCKET! I am running [this confirmer code.](https://github.com/biophil/pocket)"
"confirmer_account": "pocket-a"
"confirmer_key": <your account's private Posting key>
"confirmation_active": true
"vote_on_valid_confs": true
"nodes": [""]
```

If you are running a local steemd node, the last one, `nodes`, should be set to `["localhost:8092"]` (or whichever port you're running it on). 
If you leave `"nodes"` set to its default value of `[""]`, this will use the default nodes from the steem Python library.
Or, alternatively, you could give it a custom list of public nodes you want it to connect to like
`["node1:8092","node2:8092"]...`

**Note: if you are not using a local steemd node, you may want to contact a current bot owner for a recent snapshot of the Pocket database.**
Populating the database from scratch on public nodes may take months, since you have to scan the entire blockchain block-by-block. 

Open a screen terminal and hit it:

```
screen [press Enter]
python3 blockchain_reader.py
```

## How to see how the sync is going
Once you're running the `blockchain_reader.py` script, the code will scan through the entire Steem blockchain computing everybody's eligibility and looking for Pocket commands. To check its progress, run these python commands in another terminal window:

```
python3
>>> import util.db as db
>>> DB = db.Mist_DB()
>>> DB.last_parsed_block()
200
```
This means it's gotten through Steem block 200; when Pocket was new, there were over 15,000,000 blocks.
To check again in the same Python session, run the `_load()` method:

```
>>> DB._load()
>>> DB.last_parsed_block()
200
```

Finally, once it gets to Genesis, you'll start seeing messages in your terminal about transactions coming through and if all is well, it'll start confirming for you.
