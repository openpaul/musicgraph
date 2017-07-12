import json
import requests
import pprint
import codecs
import musicbrainzngs
import itertools
from igraph import *
import sqlite3
from time import sleep
import os, pickle    


# create DB if not existst

class hipserver:
    def __init__(self, dbname = "db.db", verbose = True):
        self.v = verbose
        musicbrainzngs.set_useragent("testapp", version = '0')
        self.startDB(dbname)
        
    def startDB(self, dbname):
        self.db  = sqlite3.connect(dbname)
        self.c   = self.db.cursor()
        self.createTable()
        
    
    def createTable(self):
        # here we save the aritst related to a song
        self.c.execute('''CREATE TABLE IF NOT EXISTS songs 
                          (id text UNIQUE, artists text, n integer)''')
        # here we store all artists whos discogarphie we already have
        self.c.execute('''CREATE TABLE IF NOT EXISTS artist 
                          (id text UNIQUE, name text)''')
        # in this table we store all discographies we already have
        self.c.execute('''CREATE TABLE IF NOT EXISTS discog 
                          (songid text UNIQUE, artistid text)''')
        self.db.commit()
    
    def makeHop(self):
        # we make a hop
        # that means, for each artist we fetch the whole discographie
        arts = self.getAllArtists()
        for a in arts:
            self.getDiscoGraphie(a)
        
        return(True)
        
    
    def getArtists(self, songID):
        # check if we have this artits stored
        artists = self.loadRelatedArtistsFromDB(songID)
        if artists != None:
            # if not load from server
            resp = self.loadRelatedArtistsFromServer(songID)
            if resp != False:
                # then save to DB for next time
                stored = self.storeSongData(songID, resp)
        else:
            songid = artists[0]
            artists = pickle.loads(artists[1])
        
        return(artists)
    
    def seed(self, theID):
        self.getDiscoGraphie(theID)
        return(True)
    
    def getDiscoGraphie(self, artistID):
        # get the whole discogarphie of an artist
        disc = self.loadDiscographieFromDB(artistID)
        # only go to the interweb if we dont have a local copy
        if disc == None:
            disc = self.loadDiscographieFromServer(artistID)
        # for each song of the disco we want the artists:
        return(disc)
    
    def storeSongData(self, songID, artists):
        # serialize the aritist as we currently store them as text... why!!! AHH
        a = pickle.dumps(artists)
        n = len(artists)
        # save to DB
        try:
            r = self.c.execute("INSERT INTO `songs`(`id`,`artists`, `n`) VALUES (?,?,?)", (songID, a, n))
        except:
            return()
        

        return(True)
    
    def loadDiscographieFromDB(self, theID):
        if self.v:
            print("Trying to load discographie from DB:    ", theID)
        songs = None
        self.c.execute('SELECT * FROM `discog` WHERE artistid=?', (theID,))
        r = self.c.fetchone()
        if r != None:
            self.c.execute('SELECT * FROM `discog` WHERE artistid=? ', (theID,))
            songs = self.c.fetchall()

        return(songs)
    
    def loadDiscographieFromServer(self, theID, turn = 1, threshold = 5):
        if self.v:
            print("Trying to load discographie from server:", theID)
        respond = []
        try:
            # fetch songs from sevrer
            offs = 0
            while offs != -1:
                resp = musicbrainzngs.browse_recordings(theID, includes = ["artist-credits"], offset = offs, limit = 100)    

                # save fetched songs to DB, so we have them
                for s in resp['recording-list']:
                    # save the songs
                    songID = s['id']
                    self.saveSong(songID, theID)
                    respond.append((songID, theID))
                    # save related artists:
                    artists = {}
                    for art in s['artist-credit']:
                        if isinstance(art, str):
                            # skip things like 'feat' and '&'
                            continue
                        a = art['artist']
                        artists[a['name']] = a['id']
                        # also save the names, so we have them already
                        self.saveArtist(a['id'],a['name'])
                    # save the song and the artists related to it:
                    self.storeSongData(songID, artists)
                # write data to db, as we now have many new songs of this artist
                self.db.commit()
                    
                if (resp['recording-count'] - len(resp['recording-list']) > offs ):
                    offs = len(resp['recording-list']) + offs
                else:
                    offs = -1
            
            self.db.commit()
        
        # save artist as done:
            
        except:
            print("Problem reaching the server")
            if turn < threshold:
                print("Lets try again in 5 seconds")
                sleep(5)
                turn = turn + 1
                self.loadDiscographieFromServer(theID, turn)
            else:
                print("We tried to often, skipping Artist")
                print(theID)
        
        return(resp)
    
    def loadRelatedArtistsFromDB(self, theID):
        self.c.execute('SELECT * FROM songs WHERE id=? ', (theID,))
        r = self.c.fetchone()
        self.db.commit()
        return(r)

 
    def loadRelatedArtistsFromServer(self, theID, turn = 1, threshold = 3):
        resp = False
        try:
            resp = musicbrainzngs.browse_artists(theID)
            tmp = {}
            for a in resp['artist-list']:
                tmp[a['name']] = a['id']
                # also save the names, so we have them already
                self.saveArtist(a['id'],a['name'])
            self.db.commit()
            resp = tmp
        except:
            print("Problem reaching the server")
            if turn < threshold:
                print("Lets try again in 3 seconds")
                sleep(3)
                turn = turn + 1
                self.loadRelatedArtistsFromServer(theID, turn)
            else:
                print("We tried to often, lets skip this one")
                print(theID)

        return(resp)
    
    def saveSong(self, songid, artistid):
        # save song of artist
        try:
            r = self.c.execute("INSERT INTO `discog`(`songid`,`artistid`) VALUES (?,?)", (songid, artistid))
        except:
            return()

        return()
    def saveArtist(self, artistid, name):
        # save song of artist
        try:
            r = self.c.execute("INSERT INTO `artist`(`id`, `name`) VALUES (?,?)", (artistid, name))
        except:
            # no exception thrown, as we have to many. 
            return()

        return()
    
    def getAllArtists(self):
        if self.v:
            print("Fetching all artists")
        self.c.execute('SELECT * FROM artist')
        r    = self.c.fetchall()
        resp = []
        for a in r:
            resp.append(a[0])
        return(resp)
    def getAllArtistsWithNames(self):
        if self.v:
            print("Fetching all artists")
        self.c.execute('SELECT * FROM artist')
        r    = self.c.fetchall()
        return(r)

    def getEdges(self):
        # TODO
        edges = []
        
        # select all songs with n > 1
        self.c.execute('SELECT * FROM songs WHERE `n` > 1')
        allSongs = self.c.fetchall()
        for song in allSongs:
            arts    = pickle.loads(song[1])
            tmpArts = []
            for a in arts:
                tmpArts.append(arts[a])
            e = [list(x) for x in itertools.combinations(tmpArts, 2)]
            for ed in e:
                edges.append(ed)
        return(edges)
        
# start a new DB server
db = hipserver("germanHipHop")
# seed with a single artist from  https://musicbrainz.org/
# we seed with Fatoni
db.seed('5b8af525-4932-4cb1-a08d-afe28d9495d8')

# now make hops:
nHops = 2
i     = 0
while i < nHops:
    db.makeHop()
    i += 1

# now that we have the data we can build a graph if we want
g = Graph()

# get all artis names:
arts = db.getAllArtistsWithNames()
# make vertices
for a in arts:
    g.add_vertex(a[0], label = a[1] )

# get the edges:
edges = db.getEdges()
g.add_edges(edges) 
summary(g)

# combine by weight
g.es["weight"] = 1
g.simplify(combine_edges={"weight": "sum"})
#layout = g.layout("kk")
#plot(g, layout = layout)



g.save("HipHopGraph-2-Hops.graphml", format="graphml")


db.c.close()



exit()


timeout = 0.5
artist_id = '5b8af525-4932-4cb1-a08d-afe28d9495d8'

musicbrainzngs.set_useragent("testapp", version = '0')
result = musicbrainzngs.get_artist_by_id(artist_id)

artists = ['5b8af525-4932-4cb1-a08d-afe28d9495d8'] # start with fatoni


artists.append('62a3f31d-790b-480f-88a6-9ed07dc4e103') # add koljha
artists.append('1cef14f9-b674-4f89-afc2-637652e38484') # add antilopengang
#unique
artists    = list(set(artists)) # make unique
print("Start the rage")


i          = 2
iterations = i + 2
while i < iterations:
    edges   = []
    for artist_id in artists:

        recs = musicbrainzngs.browse_recordings(artist_id)
        
        for rec in recs['recording-list']:
            
            arts = musicbrainzngs.browse_artists(rec['id'])
            
            # save all new edges
            if arts['artist-count'] > 1:
                print(rec['title'])
                # make all possible combinations:
                tmpA = []
                for a in arts['artist-list']:
                    tmpA.append(a['id'])
                e = [list(x) for x in itertools.combinations(tmpA, 2)]
                for ed in e:
                    edges.append(ed)
            
            # save recording as done:
            #recordings.append(rec['id'])
            time.sleep( timeout )
        
        time.sleep( timeout )
    print(i)
   
    # get all artis names:
    arts    = [item for sublist in edges for item in sublist] # make flat list
    arts    = list(set(arts)) # make unique
    print(arts)
    artists =  arts 
    i = i + 1
    


# unique edges
g = Graph()

# get all artis names:
arts = [item for sublist in edges for item in sublist] # make flat list
arts = list(set(arts)) # make unique
for a in arts:
    # lookup id for name
    name = musicbrainzngs.get_artist_by_id(a)['artist']['name']
    print(name)
    # create vertex with label as name for gephi
    g.add_vertex(a, label = name )



g.add_edges(edges) 
summary(g)
g.es["weight"] = 1

g.simplify(combine_edges={"weight": "sum"})
layout = g.layout("kk")
#plot(g, layout = layout)



g.save("hiphop-3.gml", format="gml")

'''
nodedef>name VARCHAR,label VARCHAR
s1,Site number 1
s2,Site number 2
s3,Site number 3
edgedef>node1 VARCHAR,node2 VARCHAR, weight DOUBLE
s1,s2,1.2341
s2,s3,0.453
s3,s2, 2.34
s3,s1, 0.871
'''

