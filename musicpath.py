#!/usr/bin/python3
# 
# Musigraph
# This script can create a graph file based on the ttps://musicbrainz.org/
# database. 
# launch via 
# 
# python3 muicgraph.py -i [artist id from musicbrainz] -n [hops] -db [db name]
# 
# licensed under the GPL v2 or v3
# copyright Paul Saary

import argparse
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


class hipserver:
    def __init__(self, dbname = "db.db", verbose = True):
        # init the class
        self.v = verbose
        # set a useragent, as this is required
        musicbrainzngs.set_useragent("musicgraph", version = '1')
        # start the database for local chaching
        self.startDB(dbname)
        
    def startDB(self, dbname):
        # connect to the sqlite db
        self.db  = sqlite3.connect(dbname)
        self.c   = self.db.cursor()
        # create all tables that we need
        self.createTable()
        
    
    def createTable(self):
        # a single table to hold the information
        self.c.execute('''CREATE TABLE IF NOT EXISTS songs 
                          (id text UNIQUE, artistid text, artists text, n integer)''')
        self.db.commit()


    def makeHops(self, seed, n=2):
        # we make a hop
        # that means, for each artist we fetch the whole discographie
        arts = []
        # here we keep all the ids we already fetched in one of the hops
        oldArts = []
        # store songs with the artists
        songs = {}
        i     = 0
        if len(arts) == 0:
            arts.append(seed)
        # start the hopping
        while i < n:
            if self.v:
                print("Now in Hop", i, "of", n)
            # store all artists of this round, to make a list
            tmpArts = []
            for a in arts:
                if self.v:
                    print("Artists: ", a)
                disc = self.getDiscoGraphie(a)
                for song in disc:
                    try:
                        artists = pickle.loads(song[2]) 
                        # save song to dict of songs for edge extarction
                        if song[0] not in songs:
                            songs[song[0]] = artists
                        # add now all new artists ids for the next hop round
                        for key in artists:
                            if artists[key] not in tmpArts and artists[key] not in oldArts:
                                tmpArts.append(artists[key])
                    except:
                        print("no artists stored!")
                        print(song)
            oldArts.append(arts)
            arts = tmpArts
            i += 1
        # now that we have all artists tha take part in this hop-graph
        # we can construct the edges
        edges = []
        artists = {}
        for id in songs:
            arts    = songs[id]
            tmpArts = []
            for a in arts:
                tmpArts.append(arts[a])
                # save artist names, as we have them here, already
                if arts[a] not in artists:
                    artists[arts[a]] = a
            # make edge combinations
            e = [list(x) for x in itertools.combinations(tmpArts, 2)]
            for ed in e:
                edges.append(ed)
        self.edges    = edges
        self.vertices = artists
        return(True)
    

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
    
    def storeSongData(self, songID, artistID,  artists):
        # serialize the aritist as we currently store them as text... why!!! AHH
        a = pickle.dumps(artists)
        n = len(artists)
        # save to DB
        try:
            r = self.c.execute("INSERT INTO `songs` (`id`, `artistid`, `artists`, `n`) VALUES (?,?,?,?)", (songID, artistID, a, n))
        except:
            return()
        
        
        return((songID, artistID, a, n))
    
    def loadDiscographieFromDB(self, theID):
        # skipp the unknown, as this comes up more frequently 
        if theID == '125ec42a-7229-4250-afc5-e057484327fe':
            return()
        if self.v:
            print("Trying to load discographie from DB:    ", theID)
        songs = None
        self.c.execute('SELECT * FROM `songs` WHERE artistid=?', (theID,))
        r = self.c.fetchone()
        if r != None:
            self.c.execute('SELECT * FROM `songs` WHERE artistid=? ', (theID,))
            songs = self.c.fetchall()

        return(songs)
    
    def loadDiscographieFromServer(self, theID, turn = 1, threshold = 5):
        # skipp the unknown 
        if theID == '125ec42a-7229-4250-afc5-e057484327fe':
            return()
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
                    #self.saveSong(songID, theID)
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
                    respond.append(self.storeSongData(songID, theID,  artists))
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
        
        return(respond)
    
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
        print(songid)
        try:
            print('done')
            r = self.c.execute("INSERT INTO ``(`songid`,`artistid`) VALUES (?,?)", (songid, artistid))
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
        



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("id" , type=str,
                            help="The ID of the artist, as defined by musicbrainz")

    parser.add_argument("output" , type=str,
                            help="output file")

    parser.add_argument("-c","--count" , type=int,
            help="number of hops, default: 2", default = 2)

    parser.add_argument("-d","--db" , type=str,
            help="Name of the db file", default = "cache.sqlite")

    parser.add_argument("-v", "--verbose", type = bool, 
                            help="increase output verbosity", default = False)
    args = parser.parse_args()

    # start a new DB server
    db = hipserver(args.db, args.verbose)
    # now make hops:
    db.makeHops(args.id, args.count)

    # now that we have the data we can build a graph if we want
    g = Graph()

    # make vertices
    for key in db.vertices :
        g.add_vertex(key, label = db.vertices[key] )

    # get the edges:
    g.add_edges(db.edges) 
    summary(g)

    # combine by weight
    g.es["weight"] = 1
    g.simplify(combine_edges={"weight": "sum"})
    #layout = g.layout("kk")
    #plot(g, layout = layout)



    g.save(args.output + ".graphml", format="graphml")


    db.c.close()


main()
