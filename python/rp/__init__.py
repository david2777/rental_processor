import logging as _logging

logger: _logging.Logger


def _setup_logger():
    """Setup global logging instance.

    Returns:
        None
    """
    global logger

    import os

    import logzero as lz

    from rp import constants

    log_dir = os.path.join(constants.DATA_DIR, 'rental_processor.log')
    if os.path.isfile(log_dir):
        open(log_dir, 'w').close()  # Clear past log if it exists

    fmt = lz.LogFormatter(fmt='%(color)s[%(levelname)s %(asctime)s %(module)s:%(lineno)d]%(end_color)s %(message)s')
    file_fmt = lz.LogFormatter(fmt='%(levelname)-9s %(asctime)s %(module)s:%(lineno)d %(message)s')
    logger = lz.setup_logger(name='rp', formatter=fmt, level=lz.INFO, fileLoglevel=lz.DEBUG,
                                  logfile=log_dir)
    logger.handlers[-1].setFormatter(file_fmt)
    logger.info('Logging Initialized %s', log_dir)


_setup_logger()
