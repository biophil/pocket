# POCKET Protocol Specification

Please see [the POCKET announcement on Steemit](https://steemit.com/pocket/@biophil/pocket-announcement) and [the POCKET Genesis Post](https://steemit.com/pocket/@biophil/genesis-pocket).

## Introduction

The POCKET, or Proof Of Concept Electronic Token (the K is silent), is a sub-token designed to operate on the Steem blockchain and interact with its users through a simple set of commands which users can invoke via interfaces such as [Steemit.com](http://Steemit.com) and [Busy.org](https://busy.org).

Users can transfer POCKET tokens from their account to any other Steem account by including a specially-formatted command in a Steem post (a `comment` operation). In order to provide incentives for third parties to maintain copies of the POCKET database, a small fee is taken from each transaction and is paid to the first Steem account which posts a confirmation of the validity of the transaction to the Steem blockchain. This confirmation is posted as a reply to the post which originated the transfer, thus providing users feedback about their actions and making the system useful without an explicit need for 3rd-party block explorers or local client software.

The protocol is designed to be as simple as possible while ensuring robust protections against double-spending. 

## Purpose of the Protocol

Any blockchain-based cryptocurrency must possess two conceptual elements: a consensus mechanism which generates a blockchain, and a deterministic protocol which translates a history of blockchain operations into record of "who owns what." In many ways, the first is the more difficult problem; however, we consider it to be sufficiently solved by the Steem blockchain. That is, we will consider the Steem blockchain to be an immutable history of messages.

Given the assumption of an immutable Steem blockchain, the POCKET protocol is a specification of the second part of the cryptocurrency problem: it is a deterministic protocol which translates the history of messages in the Steem blockchain into the state of the POCKET system. Users of POCKET can pass messages to the POCKET protocol by including them in properly-formatted Steem transactions.

Note that the POCKET protocol is not owned by anyone. It is not controlled by anyone. Participants in the POCKET system have implicitly agreed that the tokens defined by the protocol have meaning and possibly value; the tokens are not issued by any person or entity.

## Database

The core of the POCKET database is a specification of which accounts control which tokens.

A small amount of auxiliary data is stored by the POCKET database as well, and this will be made clear in subsequent sections.

### Account

A POCKET `account` has two properties:

- `name`: String corresponding to the Steem account name which is associated with this Pocket account. A POCKET account name is considered valid if it adheres to the standard Steem account name specifications (i.e., in terms of allowed formats and characters).
- `balance`: Non-negative integer storing the number of transferable POCKET tokens belonging to the account.

Throughout this document, the `balance` property of an account named `account` will be referenced as `account.balance`.

### Pending Confirmations

#### Send Confirmations

When a valid POCKET `send` operation is executed, information about the operation is temporarily stored as a `pending_confirmation`. This information is then posted by a third-party *back* to the Steem blockchain as a means to confirm to the sender that the operation was successful, and provide some useful information. A `pending_confirmation` has the following properties:

- `identifier`: "@author/permlink" string associated with the Steem post which included the original `send` command.
- `amount`: integer amount of the original `send`.
- `from_account`: sending account.
5. `to_account`: receiving account.
6. `new_from_balance`: Balance of sending account *immediately after* the `send` operation.
7. `new_to_balance`: Balance of receiving account *immediately after* the `send` operation.
8. `fee`: Fee reserved for the first account to post the confirmation information as a reply to the steem post identified by `identifier`.
9. `trxid`: The Steem transaction ID associated with the exact `comment` operation which contained this `send` command.

#### Claim Confirmations

After a Steem account claims their POCKET stake during the genesis interval, they can request a confirmation that their stake was claimed. This is done by replying to the Genesis Post with a single word "confirm", as described later in this document. When this is done, the POCKET database must again record that a confirmation has been requested until the intended confirmation is posted. A genesis confirmation requires much less information to be stored than a send confirmation:

- `identifier`: "@author/permlink" string associated with the Steem post which included the original `confirm` command.
- `account`: account that requested genesis confirmation
- `fee`: Fee reserved for the first account to post the confirmation information as a reply to the steem post identified by `identifier`.
- `trxid`: The Steem transaction ID associated with the exact `comment` operation which contained this `confirm` command.


### DB Activity State and Eligible accounts

At Steem block 1, POCKET is initialized to be inactive. When inactive, there exist no POCKET tokens, and thus no transfers are possible. Nonetheless, the Steem blockchain is still scanned by the POCKET protocol. During the inactivity period, all Steem accounts are monitored to determine their eligibility to receive POCKET tokens in the initial distribution. An account is considered `eligible` if, before POCKET activates, it has posted at least 5 `comment` operations to the Steem blockchain. There is no bonus for more, and no partial credits for less. Every time a `comment` operation by `<author>` is posted to the blockchain, `<author>'s` running total is incremented; when the total hits 5, `<author>` is eligible. The total is *not* decremented if `<author>` deletes a comment. Note that a `comment` operation that edits a previously-published post *is considered a valid `comment` for purposes of eligibility.* Votes, reblogs, follows, and any other type of transaction is irrelevant to determining eligibility.

#### Activating POCKET

POCKET becomes active when a special `comment` operation is included in the Steem blockchain with these properties:

- `author = biophil`
- `title = genesis-pocket`

Once published, this post is known as the "Genesis Post." Users of POCKET will interact with it to claim their tokens.

Note that the title of this post can be changed later, but its permlink will always remain `genesis-pocket`.

#### Miscellaneous

After an eligible account has claimed its POCKET stake, they may request exactly one confirmation of this stake. Thus, a list must be maintained of accounts that have not yet requested this confirmation.

## POCKET Operations

An "operation" is defined as an interaction with the POCKET system that is accomplished by posting a comment (in most cases) to the Steem blockchain. These operations are designed in such a way that POCKET tokens can be transferred between accounts using nothing more than a typical Steem front-end such as [steemit.com](https://steemit.com).


A "command" is (in most cases) defined as a string included in the `body` of a Steem comment. A "command" is parsed to form an "operation", a message which is passed to the POCKET database for validation.


There are two special operations that are only associated with the first 14 days of POCKET, also known as the "genesis interval":

- `genesis`: This is a specialized operation that is executed only once by a single pre-specified account, and it "turns on" the POCKET system.
- `claim`: This is how eligible POCKET accounts agree to participate in the POCKET protocol and receive their genesis stake of tokens.

Other than the two genesis-related operations, there are three core operations possible in the POCKET system:

- `send`: This operation allows the owner of POCKET tokens to send them to another Pocket account.
- `confirm`: This operation allows the owner of POCKET tokens to request a confirmation that they claimed their genesis stake. Each POCKET account is allowed exactly one `confirm` operation.
- `confirmation`: This operation allows a database-maintainer to collect a fee for reporting the success of a POCKET `send` or `confirm` operation.

### `genesis` operation

The `genesis` operation is executed exactly once ever. It is the signal to the POCKET database that POCKET has begun.

**Command Syntax:** The `genesis` operation is executed when the genesis account (`biophil`) publishes a top-level post with the title `genesis-pocket`.

- `author = biophil`
- `title = genesis-pocket`

**Validity:** If the database is inactive, then the `genesis` operation is valid. Otherwise, it is not.

**Result:** Upon execution of a valid `genesis`, the database state is switched to "active." The set of eligible accounts is frozen, and the record of accounts with 4 or less total Steem `comment` operations can be deleted as they are now positively confirmed to be ineligible.

The genesis account is granted a genesis credit (even if not technically eligible):

`biophil.balance += 1000001`

Finally, suppose `genesis` was executed in Steem block number `genesis_block_num`. Then a new field is added to the POCKET database called `genesis_last_block` and initialized to the value `genesis_block_num + 403200`. 403200 is the approximate number of Steem blocks that are processed in 14 days.

### `claim` operation

The `claim` operation is special; it is the only POCKET operation that is executed by doing something *other* than commenting. 

**Command Syntax:** To execute `claim`, an account `account` must reblog the POCKET genesis post. That is, submit a Steem `custom_json` transaction with `json` payload as follows:

```
["reblog",{"author":"biophil","permlink":"genesis-pocket"}]
```

**Validity:** The `claim` operation is valid if:

1. The Genesis Post has been posted already; i.e., the database state is "active."
2. The `reblog` command is included in a Steem block with number less than or equal to `genesis_last_block`.
3. `account` posted 5 or more `comment` operations *before* the Genesis Post was first published (that is, `account` is "eligible" for genesis stake).
4. `account` has not executed the `claim` operation before.

**Result:** If valid, `claim` results in a credit of the Genesis Stake to `account`. That is, the following database update:

```
account.balance += 1000001
```

`account` is now eligible to receive a single genesis confirmation.



### `send` operation

A `send` operation executed by account `from_account` has two arguments:

- `amount`: The number of tokens to be transferred.
- `to_account`: The account the tokens are to be transferred to.

**Command Syntax** A `send` operation is submitted to the POCKET system by including a specially-formatted Steem `comment` operation into the Steem blockchain. Any `comment` is eligible to contain a `send` operation if its `body` begins with

`pocketsend:amount@to_account`

For example, if I want to send 1000 POCKET to account `biophil`, I post a comment (either top-level or reply to some other post) to Steem with `body`="pocketsend:1000@biophil" (where the quotation marks " indicate that this is a string, but are not to be included in the body itself).

Additionally, if a comma (",") is included immediately following `to_account`, everything following the comma is considered a "memo" and is not parsed by the POCKET validator. For example, the above command is equivalent to

`pocketsend:1000@biophil,this part is a memo.`

If a memo is desired, the comma *must* be included and there cannot be a space between `to_account` and the comma.

The proper format of a `send` command can be verified by matching the post `body` against the following regular expression:

`^pocketsend:\d+@[a-z][a-z0-9\-.]{2,15}(,|$)`

That is, "pocketsend:" followed by a non-empty integer, followed by "@", followed by valid account name, followed either by nothing or a "," and an arbitrary string.

In parsing the command, everything between the ":" and the "@" is recorded as `amount`, and everything between "@" and "," or "EOL" is recorded as `to_account`. Note that if `to_account` is followed by a *single* linefeed `\n` character, and nothing more, the send is considered valid. This is to maintain consistency with the Python regex implementation which parses the above regex in this way.

**Validity:** A `send` operation is considered valid (with respect to the current database state) if and only if `amount>0` and `from_account.balance >= amount`. Note that POCKET *does not check* whether `to_account` is actually a registered Steem account; this allows for the "creation" of POCKET accounts whose tokens are not currently spendable, but would be made so if someone registers the associated name as a Steem account.

**Result:** If a `send` operation is valid, it results in the following database update:

1. `from_account.balance -= amount`
2. `to_account.balance += amount - 1`
3. A new pending confirmation is added to the database, including the following information:

 - `ident`: The Steem post identifier (that is, `@accountname/permlink`) corresponding to the Steem post containing the original POCKET `send` message
 - `trxid`: The Steem transaction ID corresponding to the transaction in which the associated Steem post was included.
 - `from_account`
 - `to_account`
 - `amount`
 - `new_from_balance`: the new total balance of the receiving account, computed *after* the transaction (i.e., reflecting the `send`)
 - `new_to_balance`: the new total balance of the sending account, again computed *after* the transaction
 - `fee`: the fee reserved for the confirming account

### `confirm` operation

A `confirm` operation executed by account `account` has no arguments.

**Command Syntax**

A `confirm` operation is submitted to the POCKET system by including a specially-formatted Steem `comment` operation into the Steem blockchain. The `comment` operation must have `parent_permlink` equal to the genesis permlink (`genesis-pocket`), `parent_author` equal to the genesis account (`biophil`), and the `body` must be exactly equal to 

`confirm`.

**Validity**

To be valid, the following two conditions must be met:

1. `account` must have claimed their POCKET genesis stake.
2. `account` must not have executed a `confirm` operation yet.

That is, you can only confirm *after* you claim genesis, and you cannot confirm more than once.

**Result** If valid, `confirm` results in the following database update:

1. `account.balance -= 1`
2. A new pending confirmation is added to the database, including the following information:

 - `ident`: The Steem post identifier (that is, `@accountname/permlink`) corresponding to the Steem post containing the original POCKET `confirm` message
 - `trxid`: The Steem transaction ID corresponding to the transaction in which the associated Steem post was included.
 - `account`
 - `fee`: the fee reserved for the confirming account



### `confirmation` operation for `send`

In the following, we will assume the database contains a `pending_confirmation` object called `pc`. A `confirmation` operation associated with `pc` executed by account `confirmer` has these arguments:


- `identifier`
- `amount`
- `from_account`
- `to_account`
- `new_from_balance`
- `new_to_balance`
- `fee`
- `trxid`

**Command Syntax** 

A proper `confirmation` command is posted to the Steem blockchain as a reply to the post identified by `pc.identifier`. That is, the `confirmation` command is included in the `body` of a comment with `parent_author = pc.from_account` and `parent_permlink` obtained from `pc.identifier`. The `body` of the comment, properly formatted, is given by (every line, *including the last,* ends with a linefeed `\n` character):

```
Successful Send of pc.amount
Sending Account: pc.from_account
Receiving Account: pc.to_account
New sending account balance: pc.new_from_balance
New receiving account balance: pc.new_to_balance
Fee: pc.fee
Steem trxid: pc.trxid
```

The command is considered properly formatted if the `body` of its associated `comment` matches the following regular expression:

```
^Successful Send of \d+\nSending Account: [a-z][a-z0-9\-.]{2,15}\nReceiving Account: [a-z][a-z0-9\-.]{2,15}\nNew sending account balance: \d+\nNew receiving account balance: \d+\nFee: \d+\nSteem trxid: [a-f0-9]{40}\n
```

Note that any arbitrary string is allowed after the final LF `\n` character, which allows confirmers to include other valuable information if desired.

**Validity:** A `confirmation` operation `op` is considered valid if there is a `pending_confirmation` object `pc` in the database to which `op` exactly corresponds. That is, `op` must meet the following criteria:

1. The Steem transaction `op.trxid` must include the `comment` operation resulting in the associated `send` command.
2. The command resulting in `op` must be in the body of a reply to `pc.identifier`.
3. `op.amount = pc.amount`
4. `op.from_account = pc.from_account`
5. `op.to_account = pc.to_account`
6. `op.new_from_balance = pc.new_from_balance`
7. `op.new_to_balance = pc.new_to_balance`
8. `op.fee = pc.fee`
9. `op.trxid = pc.trxid`

**Result:** If a `confirmation` operation is valid, it results in the following database update:

1. `confirmer.balance += op.fee`
2. Pending confirmation `pc` is removed from the database.


### `confirmation` operation for `confirm`

The setup for posting a confirmation to a `confirm` operation is much simpler. In the following, we will assume the database contains a `pending_confirmation` object called `pc`. A `confirmation` operation associated with `pc` executed by account `confirmer` has these properties:

- `identifier`
- `account`
- `fee`
- `trxid`

**Command Syntax** 

A proper `confirmation` command is posted to the Steem blockchain as a reply to the post identified by `pc.identifier`. That is, the `confirmation` command is included in the `body` of a comment with `parent_author = pc.account` and `parent_permlink` obtained from `pc.identifier`. The `body` of the comment, properly formatted, begins with (note that every line, including the last, ends with a linefeed `\n` character):

```
Success! You claimed a genesis stake of 1000001.
trxid:pc.trxid
```

Note that any arbitrary string is allowed after the final LF `\n` character, which allows confirmers to include other valuable information if desired.

**Validity:** A `confirmation` operation `op` is considered valid if there is a `pending_confirmation` object `pc` in the database to which `op` exactly corresponds. That is, `op` must meet the following criteria:

1. The Steem transaction `op.trxid` must include the `comment` operation resulting in the inclusion of this `confirm` operation associated with `pc.identifier` in the Steem blockchain.
2. The command resulting in `op` must be in the body of a reply to `pc.identifier`.
3. `op.account = pc.account`
4. `op.trxid = pc.trxid`

**Result:** If a `confirmation` operation is valid, it results in the following database update:

1. `confirmer.balance += op.fee`
2. Pending confirmation `pc` is removed from the database.




### `delete_confirmation` operation

It may happen that a POCKET user wishes to send tokens, but does not wish to pay the associated fee for the confirmation. If this is the case, the sender may execute the `send` command in a post, and then immediately execute the Steem `delete_comment` operation on the associated post. The original post's data will be included in the blockchain, so the `send` operation will be considered valid, but because the post will have been deleted there will be no way to post a reply to confirm the `send`. In this case, POCKET credits the associated fee to the *receiving* account.

**Command Syntax:** Every Steem `delete_comment`, denoted `del_comm`, operation must be checked for validity as a POCKET `delete_confirmation` operation, denoted `del_conf`. This operation has a single property, `identifier`, which is equal to the identifier associated with `del_comm`.

**Validity:**
Operation `del_conf` is considered valid if there exists one or more `pending_confirmation` objects in the POCKET database with `identifier = del_conf.identifier`.

**Result:** If a `del_conf` operation is valid, let `pending_confs` denote the set of `pending_confirmation` objects in the POCKET database such that for all `pc` in `pending_confs`, `pc.identifier == del_conf.identifier`. Note that an identifier can be associated with more than one `send` operation because the POCKET protocol does not distinguish between newly-posted comments and edited comments.

The result of `del_conf` is

```
for pc in pending_confs :
	pc.to_account.balance += pc.fee
	delete pc from database
end_for
```

#### Note for `confirm` operations:

All of the above applies as well for POCKET accounts who delete their `confirm` posts. If a post containing a `confirm` request is deleted before its associated confirmation can be posted, then the associated pending confirmation is also deleted. In this case, the fee is returned to the *original* account.


## The POCKET Protocol in pseudocode

```
### Database initialization
DB.active = False
DB.eligible_accounts = empty 	# this will be populated with author account names


### Constants
C.GENESIS_ACCOUNT = biophil
C.GENESIS_TITLE = genesis-pocket
C.GENESIS_PERMLINK = genesis-pocket
C.GENESIS_CREDIT = 1000001
C.GENESIS_INTERVAL = 403200
C.FEE = 1

for STEEM operation op in block :
	if DB.active == False :
		if op is comment com :
			if com.author == C.GENESIS_ACCOUNT :
				if com.title == C.GENESIS_TITLE :
					DB.active = True
					DB.gensis_last_block = 403200
					DB.GENESIS_ACCOUNT.balance += C.GENESIS_CREDIT
			if com.author not in DB.eligible_accounts :
				if com.author has posted fewer than 4 comments, add 1 to its comment count
				else if com.author has posted exactly 4 comments, add com.author to DB.eligible_accounts
	else if DB.active == True :
		if op is comment com :
			# watch for genesis confirmation requests and send transactions
			if (com.parent_author == C.GENESIS_ACCOUNT) & (com.parent_permlink == C.GENESIS_PERMLINK) : # i.e., comment is a reply to the genesis post
				if com.body == ‘confirm’ :
					if DB.(com.author).needs_genesis_confirmation == True :
						DB.pending_confirmations.add(confirmation info)
					DB.(com.author).needs_genesis_confirmation = False
			if com.body.startswith(‘pocketsend:’) :
				if com.body parses to a send operation (to to_account) and com.author has sufficient balance :
					DB.(com.author).balance -= send amount
					DB.to_account.balance += send amount – C.FEE 
					DB.pending_confirmations.add(confirmation info)
			# watch for send/genesis confirmations
			if com.parent_identifier is in DB.pending_confirmations :
				if com.body parses as the correct confirmation message :
					remove this pending confirmation from DB.pending_confirmations
		if op is delete_comment :
			if deleted comment is associated with one or more pending confirmations :
				for each associated send confirmation, delete the pending confirmation and credit the fee to the receiving account
				for each associated genesis-confirm confirmation, delete the pending confirmation and credit the fee to the original account
		if block <= DB.genesis_last_block :
			if op is reblog :
				if post being reblogged is genesis post :
					if reblogger is in DB.eligible_accounts :
						DB.reblogger.balance += C.GENESIS_CREDIT
						DB.reblogger.needs_genesis_confirmation = True
```
