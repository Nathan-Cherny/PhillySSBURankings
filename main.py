from graphqlclient import GraphQLClient
import json
import tweepy
import matplotlib.pyplot as plt
from time import sleep
from collections import Counter
import numpy as np
import time

# start.gg stuff
authToken = '93634826a62dcc30116ac70d0a71d43a'
apiVersion = 'alpha'
client = GraphQLClient('https://api.start.gg/gql/' + apiVersion)
client.inject_token('Bearer ' + authToken)
"""
{
  "Authorization": "Bearer 93634826a62dcc30116ac70d0a71d43a"
}
"""


# helper functions

def writeToJson(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=6)

# format sets from tournament slug

def getSetsFromEventId(eventId, perPage = 5):
    setData = client.execute('''
        query EventSets($eventId: ID!, $page: Int!, $perPage: Int!) {
            event(id: $eventId) {
            id
            name
            sets(
                page: $page
                perPage: $perPage
                sortType: STANDARD
            ) {
                pageInfo {
                    total
                    totalPages
                }
                nodes {
                    games{
                        winnerId
                    }
                    slots{
                        entrant{
                            id
                            name
                        }
                    }
                }
            }
            }
        }''',
        {
            "eventId": eventId,
            "page": 1,
            "perPage": perPage
        }
    )
    
    sets = []
    setData = json.loads(setData)
    totalPages = setData["data"]['event']['sets']["pageInfo"]['totalPages']
    sets += setData['data']['event']['sets']['nodes']

    i = 2
    while(i <= totalPages):
        sets += getSets(eventId, i, perPage)
        i+=1

    return sets  
    

def getSets(eventId, page, perPage):
    setData = client.execute('''
        query EventSets($eventId: ID!, $page: Int!, $perPage: Int!) {
            event(id: $eventId) {
            id
            name
            sets(
                page: $page
                perPage: $perPage
                sortType: STANDARD
            ) {
                pageInfo {
                    total
                    totalPages
                }
                nodes {
                    games{
                        winnerId
                    }
                    slots{
                        entrant{
                            id
                            name
                        }
                    }
                }
            }
            }
        }''',
        {
            "eventId": eventId,
            "page": page,
            "perPage": perPage
        }
    )
    setData = json.loads(setData)
    return setData['data']['event']['sets']['nodes']

def tournamentEvents(slug):
   events = client.execute("""
    query TournamentEvents($tourneySlug:String!) {
    tournament(slug: $tourneySlug) {
                id
                name
                events(filter: {
                    type: 1
                    videogameId: 1386
                }) {
                id
                name
                numEntrants
            }
        }
    },
    """,
    {
     "tourneySlug":"%s" % slug 
    })
   
   return json.loads(events)

def getSinglesIDFromJson(data):
    events = data['data']['tournament']['events']
    eventsByEntrants = sorted(events, key=lambda d: d['numEntrants'], reverse=True)
    # entrant with most people should be main bracket
    return eventsByEntrants[0]['id']


def convertJSONSetsToFormat(sets):
    formattedSets = ""
    for set in sets:

        if set['games'] == None:
            continue

        formattedSet = ""

        player1Score = [set['slots'][0]['entrant']['id'], set['slots'][0]['entrant']['name'], 0]
        player2Score = [set['slots'][1]['entrant']['id'], set['slots'][1]['entrant']['name'], 0]

        for game in set['games']:
            if game['winnerId'] == player1Score[0]: # if the winnerID is player1:
                player1Score[2] += 1
            else:
                player2Score[2] += 1
        
        formattedSet = f"{player1Score[0]},{player1Score[1]},{player1Score[2]},{player2Score[0]},{player2Score[1]},{player2Score[2]}"

        formattedSets += f"{formattedSet}SEPERATESETSHEREඞ"

    return formattedSets

def getFormattedSetsFromTourneySlug(slug):
    id = getSinglesIDFromJson(tournamentEvents(slug))
    sets = getSetsFromEventId(id)
    formattedSets = convertJSONSetsToFormat(sets)

    return formattedSets

# get tournament slugs in certain timeframe

def getTournamentSlugsFromTimeframe(start, end): # this will rerun the entire query for all the tournaments
    tournament = client.execute('''
    query getTournamentsByCoords($perPage: Int, $after: Timestamp, $end: Timestamp, $page: Int, $coordinates: String!, $radius: String!) {
    tournaments(query: {
        perPage: $perPage
        page: $page
        filter: {
        location: {
            distanceFrom: $coordinates,
            distance: $radius
        }
        videogameIds: [1386]
        afterDate: $after,
        beforeDate: $end
        }
    }) {
        pageInfo{
        total
        totalPages
        }
        nodes {
        name
        slug
        venueAddress
        }
    }
    },''',
    {
        "perPage": 4,
        "after": start,
        "end": end,
        "page": 1,
        "coordinates": "40.177020,-75.105960",
        "radius": "50mi"
    })
    
    tournaments = []
    tournamentData = json.loads(tournament)
    totalPages = tournamentData["data"]['tournaments']['pageInfo']['totalPages']

    i = 2
    while i < totalPages:
        tournaments += getTournament(start, end, i)
        i+=1

    return tournaments


def getTournament(start, end, page):
    tournament = client.execute('''
    query getTournamentsByCoords($perPage: Int, $after: Timestamp, $end: Timestamp, $page: Int, $coordinates: String!, $radius: String!) {
    tournaments(query: {
        perPage: $perPage
        page: $page
        filter: {
        location: {
            distanceFrom: $coordinates,
            distance: $radius
        }
        videogameIds: [1386]
        afterDate: $after,
        beforeDate: $end
        }
    }) {
        pageInfo{
        total
        totalPages
        }
        nodes {
        name
        slug
        venueAddress
        }
    }
    },''',
    {
        "perPage": 4,
        "after": start,
        "end": end,
        "page": page,
        "coordinates": "40.177020,-75.105960",
        "radius": "50mi"
    })

    return json.loads(tournament)['data']['tournaments']['nodes']

def organizeAllTournamentsByTheirOwner(tournaments):
    organizedTournaments = {}

    for tournament in tournaments:
        if tournament['venueAddress'] not in organizedTournaments.keys():
            organizedTournaments[tournament['venueAddress']] = [tournament['slug']]
        else:
            organizedTournaments[tournament['venueAddress']].append(tournament['slug'])
    
    return organizedTournaments

def onlyGetValidTournaments(organizedTournaments):
    parsedTournaments = {}
    validTournaments = [
        '3 S York Rd, Hatboro, PA 19040, USA', # bairs
        '401 N Broad St, Philadelphia, PA 19108, USA', # localhost
        '924 Cherry St, Philadelphia, PA 19107, USA', # tap
        '275 Schuylkill Rd, Phoenixville, PA 19460, USA', # recharged
        '3245 Chestnut St, Philadelphia, PA 19104, USA' # dragon dance, need to specify that "dance" is in there
    ]

    for tournament in validTournaments:
        if tournament == '3245 Chestnut St, Philadelphia, PA 19104, USA': # dragon dance
            onlyDragonDances = []
            for drexelEvent in organizedTournaments[tournament]:
                if "dance" in drexelEvent:
                    onlyDragonDances.append(drexelEvent)
            parsedTournaments[tournament] = onlyDragonDances
        else:
            parsedTournaments[tournament] = organizedTournaments[tournament]

    return parsedTournaments

def pushAllSlugsTogether(tournaments):
    allSlugs = []
    for slugs in tournaments.values():
        allSlugs += slugs
    return allSlugs

# putting it all together

def getAllSetsFromTournamentSlugs(tourneySlugs):
    allSets = []
    for slug in tourneySlugs:
        setsFromTournament = getFormattedSetsFromTourneySlug(slug)
        allSets += getFormattedSetsFromTourneySlug(slug)
        print(f"\n\nsets from {slug}: {setsFromTournament}")
        time.sleep(30)
    return allSets

    

def getAllSetsFromTournaments(tournaments):
    sleep = 60
    tournaments = tournaments
    b = onlyGetValidTournaments(organizeAllTournamentsByTheirOwner(tournaments))

    slugs = pushAllSlugsTogether(b)[23:]

    allFormattedSets = []

    for slug in slugs:
        allFormattedSets.append(slug.split("/")[1] + "SEPERATESETSHERE" + getFormattedSetsFromTourneySlug(slug))
        print(f"Success, added {slug} to list. Waiting {sleep} seconds")
        writeToJson("sets.json", allFormattedSets)
        time.sleep(sleep)

    return allFormattedSets


writeToJson("sets.json", getAllSetsFromTournaments(tournaments))

# todo

# make sure when you get the tournaments, its already been completed    

def convertJsonToStringSoThatBlassTDIsHappy(jsonFile):
    with open(jsonFile) as file:
        fileData = json.load(file)
    
    parsedString = ""
    for set_ in fileData:
        parsedString += f"{set_}\n"

    print(parsedString)