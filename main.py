import praw
import json
import os
import time
import datetime
import logging
import traceback
import re
import threading

reddit = praw.Reddit('bot1')
subreddit = reddit.subreddit('all')
starttime = datetime.datetime.now()
user = reddit.redditor('Might_have_meant')
threshold = 0
comments = user.comments.new(limit=None)
searchpattern = re.compile("((combined|whole|the( \w+)?) might of)|might of (an?|which|the|necessity|course) |(?P<quot>[\'\"]).*?might of.*?(?P=quot)", re.IGNORECASE)

if not os.path.isfile('comments_replied_to.json'):
    comments_replied_to = []
else:
    with open('comments_replied_to.json', 'r') as f:
        comments_replied_to = json.load(f)
        comments_replied_to = list(filter(None, comments_replied_to))

if not os.path.isfile('users_replied_to.json'):
    users_replied_to = []
else:
    with open('users_replied_to.json', 'r') as f:
        users_replied_to = json.load(f)
        users_replied_to = list(filter(None, users_replied_to))

if not os.path.isfile('subreddit_blacklist.json'):
    subreddit_blacklist = []
else:
    with open('subreddit_blacklist.json', 'r') as f:
        subreddit_blacklist = json.load(f)
        subreddit_blacklist = list(filter(None, subreddit_blacklist))

if not os.path.isfile('user_blacklist.json'):
    user_blacklist = []
else:
    with open('user_blacklist.json', 'r') as f:
        user_blacklist = json.load(f)
        user_blacklist = list(filter(None, user_blacklist))

if not os.path.isfile('sentence_blacklist.json'):
    sentence_blacklist = []
else:
    with open('sentence_blacklist.json', 'r') as f:
        sentence_blacklist = json.load(f)
        sentence_blacklist = list(filter(None, sentence_blacklist))

if not os.path.isfile('past_deleted.json'):
    past_deleted = []
else:
    with open('past_deleted.json', 'r') as f:
        past_deleted = json.load(f)
        past_deleted = list(filter(None, past_deleted))


def updatedb(dbtype):
    if dbtype == 'cdb':
        with open('comments_replied_to.json', 'w') as f:
            f.write(json.dumps(comments_replied_to, sort_keys=True, indent=4))
    elif dbtype == 'udb':
        with open('users_replied_to.json', 'w') as f:
            f.write(json.dumps(users_replied_to, sort_keys=True, indent=4))
    elif dbtype == 'ubl':
        with open('user_blacklist.json', 'w') as f:
            f.write(json.dumps(user_blacklist, sort_keys=True, indent=4))
    elif dbtype == 'pdl':
        with open('past_deleted.json', 'w') as f:
            f.write(json.dumps(past_deleted, sort_keys=True, indent=4))


def runbot():
    comments = subreddit.stream.comments()
    for comment in comments:
        content = comment.body
        if ' might of ' in content.lower():
            if (comment.id not in comments_replied_to and
                    str(comment.author) not in user_blacklist and
                    comment.created > starttime and
                    str(comment.subreddit) not in subreddit_blacklist and
                    searchpattern.search(content) is None):
                mightofcapt = re.search(".*?(might of).*?", content, flags=re.IGNORECASE).group(1)
                comment.reply('''> %s

Did you mean might have?
***
^^I ^^am ^^a ^^bot, ^^and ^^this ^^action ^^was ^^performed ^^automatically.
^^| ^^I ^^accept ^^feedback ^^in ^^PMs. ^^|
^^[[Opt-out]](http://www.reddit.com/message/compose/?to=Might_have_meant&subject=User+Opt+Out&message=Click+send+to+opt+yourself+out.) ^^|
^^Moderator? ^^Click ^^[[here]](http://www.reddit.com/message/compose/?to=Might_have_meant&subject=Subreddit+Opt+Out&message=Click+send+to+opt+your+subreddit+out.) ^^|
^^Downvote ^^this ^^comment ^^to ^^delete ^^it. ^^| ^^[[Source Code]](https://github.com/arielbeje/Might_have_meant) ^^| ^^[Programmer](https://www.reddit.com/message/compose/?to=arielbeje)''' % mightofcapt)
                print('Fixed a commment by', comment.author)
                comments_replied_to.append(comment.id)
                updatedb('cdb')
                users_replied_to.append(str(comment.author))
                updatedb('udb')


def deletepast():
    while True:
        comments = user.comments.new(limit=None)
        print("Deleting downvoted comments...")
        for comment in comments:
            creatd = datetime.datetime.fromtimestamp(comment.created)
            try:
                if(comment.score < threshold and comment.id not in past_deleted and
                   creatd + datetime.timedelta(hours=1) < datetime.datetime.now()):
                    print("Deleted a comment on /r/" + str(comment.subreddit))
                    comment.delete()
                    past_deleted.append(comment.id)

                elif(creatd + datetime.timedelta(hours=1) > datetime.datetime.now() and
                     comment.score < threshold and comment.id not in past_deleted):
                    print("Did not delete <1 hour old comment with ID " + comment.id)

            except Exception as e:
                logging.error(traceback.format_exc())
                continue

        updatedb('pdl')
        time.sleep(3600)


def readpms():
        to_mark_read = []
        for item in reddit.inbox.stream():
            # print("Checking message with subject \"%s\"" % item.subject)
            if(isinstance(item, praw.models.Message) and item.author not in user_blacklist and
               isinstance(item, praw.models.SubredditMessage) is False):
                if item.subject.lower() == "user opt out" or "user+opt+out":
                    user_blacklist.append(str(item.author))
                    updatedb('ubl')
                    item.reply("You have been added to the user blacklist of this bot.")
                    print("Added " + str(item.author) + " to user blacklist.")
                    to_mark_read.append(item)
                    reddit.inbox.mark_read(to_mark_read)
                    to_mark_read = []

                else:
                    print("Got a PM from " + item.author + " saying:")
                    print(str(item.content))
                    to_mark_read.append(item)
                    reddit.inbox.mark_read(to_mark_read)
                    to_mark_read = []


if __name__ == '__main__':
    threading.Thread(target=runbot).start()
    threading.Thread(target=deletepast).start()
    threading.Thread(target=readpms).start()
