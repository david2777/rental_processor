import re
import enum
import requests
from urllib import parse
from typing import Union, Tuple

import googlemaps

from rp import logger
import rp.constants as c

gmaps_client = googlemaps.Client(key=c.MAPS_API_KEY)
whitespace_reg = re.compile(r"\s+")


class RentalStatus(enum.Enum):
    FILTERED_RENT_LOW = 1
    FILTERED_RENT_HIGH = 2
    FILTERED_BEDS = 3
    FILTERED_SQFT = 4
    FILTERED_LAUNDRY = 5
    FILTERED_PETS = 6
    FILTERED_COMMUTE = 7


class Rental:
    raw_data: list = None
    mls: str = None
    typ: str = None
    address: str = None
    address_no_unit: str = None
    zip: int = None
    beds: int = None
    baths: int = None
    rent: int = None
    sqft: Union[int, None] = None
    pets: str = None
    laundry: str = None

    _commute: int = None
    _walk_score: Tuple[int, int] = None
    _lat_lon: Tuple[float, float] = None

    _walk_score_cache = {}
    walk_score_cache_hits = 0
    
    _commute_cache = {}
    commute_cache_hits = 0
    
    _lat_lon_cache = {}
    lat_lon_cache_hits = 0

    def __init__(self, data_row: list[str]):
        """Initialize the rental with a row of data from the spreadsheet.

        Args:
            data_row list[Str]: A list of raw data from the spreadsheet.
        """
        self.raw_data = data_row
        self.mls = self.raw_data[c.MLS]
        self.typ = self.raw_data[c.TYP]
        self.zip = self.raw_data[c.ZIP_CODE]
        st_name = self.raw_data[c.ST_NAME].split('#')[0].strip()
        self.address = f'{self.raw_data[c.ST_NUMBER]} {self.raw_data[c.ST_NAME]} {self.raw_data[c.CITY]} {self.zip}'
        self.address_no_unit = f'{self.raw_data[c.ST_NUMBER]} {st_name} {self.raw_data[c.CITY]} {self.zip}'
        self.address = whitespace_reg.sub(" ", self.address)
        self.address_no_unit = whitespace_reg.sub(" ", self.address_no_unit)
        reg = re.compile(r"(\d+)?/(\d+)?")
        matches = reg.search(self.raw_data[c.BEDS_BATH])
        try:
            self.sqft = int(self.raw_data[c.SQFT].split('/')[0])
        except ValueError:
            self.sqft = None
        try:
            self.beds = int(matches.group(1))
        except Exception:
            self.beds = 1
        try:
            self.baths = int(matches.group(2))
        except Exception:
            self.baths = 1
        self.rent = int(re.sub("[^0-9]", "", self.raw_data[c.RENT]))
        self.pets = self.raw_data[c.PETS]
        self.laundry = self.raw_data[c.LAUNDRY]

    def __repr__(self):
        return f'{self.mls} {self.address} {self.beds}/{self.baths} {self.sqft}sqft ${self.rent}'

    @property
    def lat_lon(self) -> Tuple[float, float]:
        """Cached property for the latitude and longitude of the rental using Google Maps.
        
        Returns:
            Tuple[float, float]: Tuple where (Latitude, Longitude).
        """
        if self._lat_lon:
            self.lat_lon_cache_hits += 1
            return self._lat_lon

        self._lat_lon = (0.0, 0.0)
        logger.debug('Attempting to geocode %s', self.address_no_unit)
        gcode = gmaps_client.geocode(self.address_no_unit)

        try:
            data = gcode[0]['geometry']['location']
            self._lat_lon = (data['lat'], data['lng'])
        except (KeyError, IndexError, TypeError):
            logger.exception('Unable to geocode %s', self.address)

        logger.debug('%s is geocoded at %s, %s', self.address_no_unit, *self._lat_lon)

        return self._lat_lon

    def get_data_out(self) -> list[str]:
        """Returns a list of string to dump into the .processed.csv file as a row. 
        
        Returns:
            list[str]: A list of string where each string is data about the rental.
        """
        walk, bike = self.get_walkscore()
        result = [self.mls, self.typ, self.address, self.beds, self.baths, self.get_commute_time(), self.rent,
                  self.sqft, '', walk, bike, '', '', self.pets, self.laundry]
        return [str(x) for x in result]

    def get_commute_time(self) -> Union[int, None]:
        """Cached method which returns the commute time in minutes to the WORK_ADDRESS using Google Maps. 
        
        Returns:
            Union[int, None]: The commute time in minutes if available, None if not. 
        """
        if c.SKIP_APIS:
            return 0

        if self._commute is not None:
            self.commute_cache_hits += 1
            return self._commute

        logger.debug('Getting commute time from %s to %s', self.address_no_unit, c.WORK_ADDRESS)
        result = gmaps_client.distance_matrix(self.address_no_unit, c.WORK_ADDRESS, mode="driving", units="imperial")
        duration = result["rows"][0]["elements"][0]["duration"]["value"]

        if duration:
            duration = duration / 60
        else:
            duration = -1
        self._commute = int(duration)

        logger.debug('Commute is %s minutes', duration)

        return self._commute

    def get_walkscore(self) -> Tuple[int, int]:
        """Cached method which returns the walkscore and bikescore for the rental using the Walkscore API. 
        
        Returns:
            Tuple[int, int]: Tuple where (Walkscore, Bikescore) for the rental. Defaults to (0, 0) if not available. 
        """
        if self._walk_score:
            self.walk_score_cache_hits += 1
            return self._walk_score

        try:
            self._walk_score = self._walk_score_cache[self.address_no_unit]
            logger.debug('Found WalksScore in cache')
            logger.debug('Walk %s Bike %s', *self._walk_score)
            return self._walk_score
        except KeyError:
            pass

        self._walk_score = (0, 0)
        if c.SKIP_APIS:
            return self._walk_score

        lat, lon = self.lat_lon
        if not lat or not lon:
            return self._walk_score

        logger.info('Getting Walkscore for %s', self.address_no_unit)

        data = {'wsapikey': c.WALKSCORE_API_KEY, 'format': 'json', 'lat': lat, 'lon': lon, 'bike': 1,
                'address': self.address_no_unit}
        encoded = parse.urlencode(data)
        url = "https://api.walkscore.com/score?" + encoded
        logger.debug('%s', url)
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200 or data['status'] != 1:
            logger.error('Unable to calculate walk score for %s', self.address_no_unit)
            return self._walk_score

        try:
            self._walk_score = data['walkscore'], data['bike']['score']
        except KeyError:
            pass

        logger.debug('Walk %s Bike %s', *self._walk_score)

        self._walk_score_cache[self.address_no_unit] = self._walk_score

        return self._walk_score

    def filter(self) -> list:
        """Returns a list of filters, if the list is empty then the listing has passed all checks.
        
        Returns:
            list: List of filters, if the list is empty then the listing has passed all checks.
        """
        filters = []

        if not c.MIN_RENT <= self.rent:
            logger.debug('Discarding %s due to RENT_LOW [%s <= %s]', self, c.MIN_RENT, self.rent)
            filters.append(RentalStatus.FILTERED_RENT_LOW)

        if not self.rent < c.MAX_RENT:
            logger.debug('Discarding %s due to RENT_HIGH [%s < %s]', self, self.rent, c.MAX_RENT)
            filters.append(RentalStatus.FILTERED_RENT_HIGH)

        check = c.MIN_BEDS <= self.beds < c.MAX_BEDS
        if not check:
            logger.debug('Discarding %s due to BEDS [%s <= %s < %s]', self, c.MAX_BEDS, self.beds, c.MAX_BEDS)
            filters.append(RentalStatus.FILTERED_BEDS)

        if self.sqft is not None:
            check = c.MIN_SQFT <= self.sqft < c.MAX_SQFT
            if not check:
                logger.debug('Discarding %s due to SQFT [%s <= %s < %s]', self, c.MIN_SQFT, self.sqft, c.MAX_SQFT)
                filters.append(RentalStatus.FILTERED_SQFT)

        checks = ['community', 'common']
        if c.PRIVATE_LAUNDRY and any([ch in self.laundry.lower() for ch in checks]):
            logger.debug('Discarding %s due to LAUNDRY', self)
            filters.append(RentalStatus.FILTERED_LAUNDRY)

        if c.ALLOWS_PETS and 'no' in self.pets.lower():
            logger.debug('Discarding %s due to PETS', self)
            filters.append(RentalStatus.FILTERED_PETS)

        if not c.SKIP_APIS and c.MAX_COMMUTE_TIME and self.get_commute_time() > c.MAX_COMMUTE_TIME:
            logger.debug('Discarding %s due to COMMUTE [%s > %s]', self, self.get_commute_time(), c.MAX_COMMUTE_TIME)
            filters.append(RentalStatus.FILTERED_COMMUTE)

        return filters
