## Pocket 

The POCKET, or Proof Of Concept Electronic Token (the K is silent), is a sub-token designed to operate on the Steem blockchain and interact with its users through a simple set of commands which users can invoke via interfaces such as [Steemit.com](http://Steemit.com) and [Busy.org](https://busy.org).

Please see [the POCKET announcement on Steemit](https://steemit.com/pocket/@biophil/pocket-announcement) and [the POCKET Genesis Post](https://steemit.com/pocket/@biophil/genesis-pocket).

## How to run a confirmer bot

Here are basic instructions for Ubuntu 16.04, they probably work fine on most Linux distribution with latest version of Python 3.5.

Install the python steem library and clone the Pocket repo:

```
git clone https://github.com/Netherdrake/steem-python
cd steem-python
sudo python3 setup.py install
cd
git clone https://github.com/biophil/pocket
cd pocket
git checkout develop
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
"nodes": ["https://steemd.steemitstage.com","https://steemd.steemit.com","steem.house:8090"]
```

If you are running a local steemd node, the last one, `nodes`, should be set to `["localhost:8092"]` (or whichever port you're running it on). 
If you leave `"nodes"` set to its default value of `[""]`, this will use the default nodes from the steem Python library.
Or, alternatively, you could give it a custom list of public nodes you want it to connect to like
`["node1:8092","node2:8092"]...`

Populating the database from scratch on public nodes may take months, since you have to scan the entire blockchain block-by-block. 
To alleviate this, a snapshot is provided of the Pocket database immediately preceding Genesis in the file `db_pregenesis.json`. To use this snapshot, use the third of these startup options the first time you run `blockchain_reader.py` after editing config:

There are 3 startup options, passed as arguments to `blockchain_reader.py`:
- `normal`: Starts parsing the Steem blockchain right where you last left off. If this is the first time you've run your bot, this will start at Steem block 1.
- `replay-from-0`: Begin parsing the Steem blockchain at the beginning of history. **Danger!** This erases your current database! Consider making a backup of your `.db` file.
- `replay-from-genesis`: Begin parsing the Steem blockchain in block number 14971640, when Pocket Genesis begins. Uses the eligibility snapshot contained in `db_pregenesis.json`. **Danger!** This erases your current database! Consider making a backup of your `.db` file.

Open a screen terminal and hit it (my example command uses the `replay_from_genesis` option):

```
screen [press Enter]
python3 blockchain_reader.py replay-from-genesis
```

**Note:** After this first time, to access the `normal` startup mode, you can simply call `blockchain_reader.py`:

```
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
