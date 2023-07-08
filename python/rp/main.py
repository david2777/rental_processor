import csv
import os.path
import pathlib
from operator import methodcaller

from rp import logger
from rp import constants, utils, rental


def main(data_file_path=None):
    """Processes the latest rentals .csv file and outputs a .processed.csv file to the same location.

    Args:
        data_file_path (str): Optional path to csv file. Default will find the latest csv file from the DATA_DIR.

    Returns:
        None
    """
    if not data_file_path:
        p = pathlib.Path(constants.DATA_DIR)
        files = [f for f in p.iterdir() if f.is_file() and f.name.endswith('.csv') and 'processed' not in f.name]
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        if not files:
            raise RuntimeError(f'Found no CSV files in {p}')

        data_file_path = files[0].as_posix()

    logger.info('Reading Rental Data from %s', data_file_path)
    out_file_path = data_file_path.replace('.csv', '.processed.csv')
    if os.path.isfile(out_file_path):
        try:
            logger.info('Attempted top remove existing output file %s', out_file_path)
            os.remove(out_file_path)
        except (OSError, WindowsError):
            logger.exception('Failed to remove %s', out_file_path)
            return

    results = []
    with open(data_file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        data = list(reader)

    header = data.pop(0)
    data = [row for row in data if row[0]]
    update = utils.update_columns(header)
    if not update:
        logger.critical('Failed to update header')
        return

    count = len(data)
    filter_counter = {e.name: 0 for e in rental.RentalStatus}
    i = 0

    for row in data:
        i += 1
        logger.info('[%s/%s] Processing...', i, count)
        logger.debug('%s', row)
        try:
            rental_obj = rental.Rental(row)
            filter_results = rental_obj.filter()
            if not filter_results:
                results.append(rental_obj)
            else:
                for f in filter_results:
                    filter_counter[f.name] += 1
        except (KeyError, ValueError, TypeError, AttributeError):
            logger.exception('Unhandled Exception on %s', row)

    logger.info('Filter Results')
    for name, count in filter_counter.items():
        logger.info('\t%s: %s', name, count)

    logger.info('Sorting %s results', len(results))
    results.sort(key=methodcaller('get_commute_time'))

    logger.info('Fetching walkscore for %s results and writing to %s', len(results), out_file_path)
    i = 1
    with open(out_file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for item in results:
            logger.info('[%s/%s] Fetching %s', i, len(results), item.address_no_unit)
            writer.writerow(item.get_data_out())
            i += 1
            
    logger.info('Cache Hits')
    logger.info('\tCommute: %s', results[0].commute_cache_hits)
    logger.info('\tWalkScore: %s', results[0].walk_score_cache_hits)
    logger.info('\tLatLon: %s', results[0].lat_lon_cache_hits)

    logger.info('Complete!')


if __name__ == '__main__':
    main()
