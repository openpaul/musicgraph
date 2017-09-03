# musicgraph
This small script creates a weighted graph for an artists based on the number of features the artist did with other artists.

## Usage
First look up the artist id using the musicbrainz webpage (https://musicbrainz.org/).
The id is part of the URI when on the artist page and looks like this `9efff43b-3b29-4082-824e-bc82f646f93d` (The Doors).

This is is the first required argument for the script. 

```
musicpath.py [-h] [-c COUNT] [-d DB] [-v VERBOSE] id output
```

This will produce a file called output.graphml which can be loaded using gephi or another graph visualization software.

## Bugs
The code is not perfect and grew over time. If you find a bug, I would be very pleased to merge your pull request.
If you want to report something feel free to do so here.



