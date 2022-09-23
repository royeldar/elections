#!/usr/bin/env python3

import sys
import csv
import urllib.request

CITY = 'שם ישוב'
ELLIGIBLE = 'בזב'
TOTAL_VOTES = 'מצביעים'
INVALID_VOTES = 'פסולים'
VALID_VOTES = 'כשרים'

ADDITIONAL_BALLOTS = 'מעטפות חיצוניות'

EXPC_FIELDNAMES = [
    'סמל ועדה',
    CITY,
    'סמל ישוב',
    ELLIGIBLE,
    TOTAL_VOTES,
    INVALID_VOTES,
    VALID_VOTES,
]


def parse_parties(fieldnames):
    i = len(EXPC_FIELDNAMES)
    assert fieldnames[:i] == EXPC_FIELDNAMES
    # rows may contain a trailing comma
    parties = fieldnames[i:]
    if parties[-1] == '':
        parties = parties[:-1]
    return parties


# expc.csv
def parse_expc(filename, encoding):
    votes_per_city = {}
    turnout_per_city = {}
    with open(filename, newline='', encoding=encoding) as csvfile:
        reader = csv.DictReader(csvfile)
        parties = parse_parties(reader.fieldnames)
        for row in reader:
            city = row[CITY]
            assert city not in votes_per_city
            elligible = int(row[ELLIGIBLE])
            total_votes = int(row[TOTAL_VOTES])
            valid_votes = int(row[VALID_VOTES])
            invalid_votes = int(row[INVALID_VOTES])
            assert elligible >= 0
            assert total_votes >= 0
            assert valid_votes >= 0
            assert invalid_votes >= 0
            assert total_votes == valid_votes + invalid_votes, \
                f"numbers don't add up correctly in {city}"
            votes_per_party = {}
            for party in parties:
                votes = int(row[party])
                assert votes >= 0
                votes_per_party[party] = votes
            assert sum(votes_per_party.values()) == valid_votes, \
                f"numbers don't add up correctly in {city}"
            votes_per_city[city] = votes_per_party
            if elligible != 0:
                if total_votes > elligible:
                    print(f"voter turnout > 100% in {city}")
                    print("\t" f"elligible voters: {elligible}")
                    print("\t" f"total votes: {total_votes}")
                turnout = total_votes / elligible
                turnout_per_city[city] = turnout
            else:
                # for some reason, this field is zero
                assert city == ADDITIONAL_BALLOTS
    return parties, votes_per_city, turnout_per_city


def parse_alliances(filename, encoding):
    with open(filename, 'r', encoding=encoding) as f:
        lines = f.readlines()
    alliances = []
    for line in lines:
        line = line.strip()
        if line != '':
            words = line.split()
            assert len(words) == 2
            assert words[0] != words[1]
            assert all(words[0] not in a for a in alliances)
            assert all(words[1] not in a for a in alliances)
            alliances.append(tuple(words))
    return alliances


def get_party_votes(votes_per_city, party):
    return sum(votes_per_party[party] for votes_per_party in votes_per_city.values())


ELECTORAL_THRESHOLD_PERCENTAGE = 3.25
NUMBER_OF_SEATS = 120
# see https://main.knesset.gov.il/About/Lexicon/Pages/seats.aspx
def calculate_seats(votes_per_party, alliances):
    parties = list(votes_per_party.keys())
    total_votes = sum(votes_per_party.values()) # A
    electoral_threshold = total_votes * (ELECTORAL_THRESHOLD_PERCENTAGE / 100.) # B
    is_failed_party = lambda party: votes_per_party[party] < electoral_threshold
    failed_parties = [party for party in parties if is_failed_party(party)]
    # discard failed parties that didn't pass the electoral threshold
    votes_per_party = {party : votes for party, votes in votes_per_party.items() if party not in failed_parties} # F
    total_votes = sum(votes_per_party.values()) # D
    votes_per_seat = total_votes // NUMBER_OF_SEATS # E
    seats_per_party = {party : votes // votes_per_seat for party, votes in votes_per_party.items()} # G
    remaining_seats = NUMBER_OF_SEATS - sum(seats_per_party.values()) # H
    # discard electoral alliances with parties that didn't pass the threshold
    is_failed_alliance = lambda alliance: any(party in failed_parties for party in alliance)
    alliances = [alliance for alliance in alliances if not is_failed_alliance(alliance)]
    is_in_alliance = lambda party: any(party in alliance for alliance in alliances)
    seats_distribution = {party : seats for party, seats in seats_per_party.items() if not is_in_alliance(party)}
    seats_distribution.update({alliance : sum(seats_per_party[party] for party in alliance) for alliance in alliances})
    votes_distribution = {party : votes for party, votes in votes_per_party.items() if not is_in_alliance(party)}
    votes_distribution.update({alliance : sum(votes_per_party[party] for party in alliance) for alliance in alliances})
    parties_and_alliances = list(seats_distribution.keys())
    # split the remaining seats among the parties (and electoral alliances)
    while remaining_seats > 0:
        measure_per_party = {party : votes_distribution[party] / (seats_distribution[party] + 1) for party in parties_and_alliances} # I
        chosen_party = max(measure_per_party, key=measure_per_party.get)
        seats_distribution[chosen_party] += 1
        remaining_seats -= 1
    # calculate seats distribution for parties which aren't in any electoral alliance
    seats_per_party = {party : seats for party, seats in seats_distribution.items() if not party in alliances}
    # split the seats among the parties in each electoral alliance
    for alliance in alliances:
        shared_seats = seats_distribution[alliance] # J
        shared_measure = votes_distribution[alliance] // shared_seats # K
        individual_seats = {party : votes_per_party[party] // shared_measure for party in alliance} # L
        remaining_seats = shared_seats - sum(individual_seats.values())
        # split the remaining seats among the individual parties in the electoral alliance
        while remaining_seats > 0:
            individual_measure = {party : votes_per_party[party] / (individual_seats[party] + 1) for party in alliance} # M
            chosen_party = max(individual_measure, key=individual_measure.get)
            individual_seats[chosen_party] += 1
            remaining_seats -= 1
        # update seats distribution for parties in the electoral alliance
        seats_per_party.update(individual_seats)
    # finally, parties that didn't pass the electoral threshold get zero seats
    for party in failed_parties:
        seats_per_party[party] = 0
    return seats_per_party


EXPC_CSV_URL = "https://media24.bechirot.gov.il/files/expc.csv"
ENCODING = "cp1255" # windows-1255

def main(argv):
    assert len(argv) == 2, \
        f"Usage: {argv[0]} <alliances.txt>"

    expc_csv_filename, _ = urllib.request.urlretrieve(EXPC_CSV_URL)
    alliances_filename = argv[1]
    parties, votes_per_city, turnout_per_city = parse_expc(expc_csv_filename, ENCODING)
    electoral_alliances = parse_alliances(alliances_filename, 'utf-8')
    votes_per_party = {party : get_party_votes(votes_per_city, party) for party in parties}
    seats_per_party = calculate_seats(votes_per_party, electoral_alliances)
    seats_distribution = list(seats_per_party.items())
    seats_distribution.sort(key=lambda x:x[1], reverse=True)
    for party, seats in seats_distribution:
        print(f"{party}: {seats}")

if __name__ == "__main__":
    main(sys.argv)
