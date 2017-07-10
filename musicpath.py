import json
import requests
import pprint
import codecs
import musicbrainzngs
import itertools
artist_id = '5b8af525-4932-4cb1-a08d-afe28d9495d8'

musicbrainzngs.set_useragent("testapp", version = '0')
result = musicbrainzngs.get_artist_by_id(artist_id)

artists = []
edges   = []
recordings = []

for art_id in artists:

    recs = musicbrainzngs.browse_recordings(artist_id)

    for rec in recs['recording-list']:
        print(rec['title'])
        arts = musicbrainzngs.browse_artists(rec['id'])
        
        # save all new edges
        if arts['artist-count'] > 1:
            # make all possible combinations:
            artists = []
            for a in arts['artist-list']:
                artists.append(a['id'])
            e = [list(x) for x in itertools.combinations(artists, 2)]
            for ed in e:
                edges.append(ed)
        
        # save recording as done:
        recordings.append(rec['id'])


    
    

artist = result["artist"]
print("name:\t\t%s" % artist["name"])
print("sort name:\t%s" % artist["sort-name"])


# start by antilopengang

agid = '1cef14f9-b674-4f89-afc2-637652e38484'


def fetch (url):
    headers = {
        'User-Agent': 'musicgraphtest'
    }

    r = requests.get(url, headers = headers)

    return(r.json())



class Artist:
    def __init__(self,id):
        self.id = id;
        self.name = self.getName()
        print("fetched name")
        print("will fetch now all the songs")

    def getName(self):
        url   = 'http://musicbrainz.org/ws/2/artist/' + self.id + '/?fmt=json'
        resp  = fetch(url)
        return(resp['name'])
        
    def getRelatet(self):
        self.related = {}
        
        

print("Music fetch")

ag = Artist(agid)
