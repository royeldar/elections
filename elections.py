#!/usr/bin/env python3

import sys
import csv
import urllib.request

CITY = 'שם ישוב'
ELLIGIBLE = 'בזב'
TOTAL_VOTES = 'מצביעים'
INVALID_VOTES = 'פסולים'
VALID_VOTES = 'כשרים'

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
                assert city == 'מעטפות חיצוניות'
    return votes_per_city, turnout_per_city


EXPC_CSV_URL = "https://media24.bechirot.gov.il/files/expc.csv"
ENCODING = "cp1255" # windows-1255

def main(argv):
    expc_csv_filename, _ = urllib.request.urlretrieve(EXPC_CSV_URL)
    votes_per_city, turnout_per_city = parse_expc(expc_csv_filename, ENCODING)


if __name__ == "__main__":
    main(sys.argv)
