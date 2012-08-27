#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""Generic logging, the way I remember it from scripts gone by.

TODO:
- network logging support.
- log rotation config
"""

from datetime import datetime
import logging
import os
import sys
import traceback

# Define our own FATAL_LEVEL
FATAL_LEVEL = logging.CRITICAL + 10
logging.addLevelName(FATAL_LEVEL, 'FATAL')

# mozharness log levels.
DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL, IGNORE = (
    'debug', 'info', 'warning', 'error', 'critical', 'fatal', 'ignore')

CONTEXT_WARN_MESSAGE = "Warning: missing context. Current "\
    "%(type)s buffer size: %(buffer)d, Requested %(type)s context lines:"\
    " %(context)d. Setting context length to: %(buffer)d"

# LogMixin {{{1
class LogMixin(object):
    """This is a mixin for any object to access similar logging
    functionality -- more so, of course, for those objects with
    self.config and self.log_obj, of course.
    """

    def _log_level_at_least(self, level):
        log_level = INFO
        levels = [DEBUG, INFO, WARNING, ERROR, CRITICAL, FATAL]
        if hasattr(self, 'config'):
            log_level = self.config.get('log_level', INFO)
        return levels.index(level) >= levels.index(log_level)

    def _print(self, message, stderr=False):
        if not hasattr(self, 'config') or self.config.get('log_to_console', True):
            if stderr:
                print >> sys.stderr, message
            else:
                print message

    def log(self, message, level=INFO, exit_code=-1):
        if self.log_obj:
            return self.log_obj.log_message(message, level=level,
                                            exit_code=exit_code)
        if level == INFO:
            if self._log_level_at_least(level):
                self._print(message)
        elif level == DEBUG:
            if self._log_level_at_least(level):
                self._print('DEBUG: %s' % message)
        elif level in (WARNING, ERROR, CRITICAL):
            if self._log_level_at_least(level):
                self._print("%s: %s" % (level.upper(), message), stderr=True)
        elif level == FATAL:
            if self._log_level_at_least(level):
                self._print("FATAL: %s" % message, stderr=True)
                raise SystemExit(exit_code)

    # Copying Bear's dumpException():
    # http://hg.mozilla.org/build/tools/annotate/1485f23c38e0/sut_tools/sut_lib.py#l23
    def dump_exception(self, message=None, level=ERROR):
        tb_type, tb_value, tb_traceback = sys.exc_info()
        if message is None:
            message = ""
        else:
            message = "%s\n" % message
        for s in traceback.format_exception(tb_type, tb_value, tb_traceback):
            message += "%s\n" % s
        # Log at the end, as a fatal will attempt to exit after the 1st line.
        self.log(message, level=level)

    def debug(self, message):
        self.log(message, level=DEBUG)

    def info(self, message):
        self.log(message, level=INFO)

    def warning(self, message):
        self.log(message, level=WARNING)

    def error(self, message):
        self.log(message, level=ERROR)

    def critical(self, message):
        self.log(message, level=CRITICAL)

    def fatal(self, message, exit_code=-1):
        self.log(message, level=FATAL, exit_code=exit_code)


# OutputParser {{{1
class OutputParser(LogMixin):
    """ Helper object to parse command output.

This will buffer output if needed, so we can go back and mark
[(linenum - 10):linenum+10] as errors if need be, without having to
get all the output first.

linenum+10 will be easy; we can set self.num_post_context_lines to 10,
and self.num_post_context_lines-- as we mark each line to at least error
level X.

linenum-10 will be trickier. We'll not only need to save the line
itself, but also the level that we've set for that line previously,
whether by matching on that line, or by a previous line's context.
We should only log that line if all output has ended (self.finish() ?);
otherwise store a list of dictionaries in self.context_buffer that is
buffered up to self.num_pre_context_lines (set to the largest
pre-context-line setting in error_list.)
"""
    def __init__(self, config=None, log_obj=None, error_list=None,
                 log_output=True):
        self.config = config
        self.log_obj = log_obj
        self.error_list = error_list or []
        self.log_output = log_output
        self.num_errors = 0
        self.use_buffer = False

        buffer_limit = None
        for error_check in self.error_list:
            if error_check.get('context_lines'):
                self.use_buffer = True
                target_limit = error_check.get('context_lines')['pre'] + \
                    error_check.get('context_lines')['post'] + 1
                if self.buffer_limit > target_limit:
                    buffer_limit = target_limit
        if self.use_buffer:
            self.context_buffer = []
            self.buffer_limit = buffer_limit
            self.match_strings = dict(match='>>>', context='>')
        # TODO set self.error_level to the worst error level hit
        # (WARNING, ERROR, CRITICAL, FATAL)
        # self.error_level = INFO

    def parse_single_line(self, line, buffer_index=None):
        for error_check in self.error_list:
            # TODO buffer for context_lines.
            match = False
            if 'substr' in error_check:
                if error_check['substr'] in line:
                    match = True
            elif 'regex' in error_check:
                if error_check['regex'].search(line):
                    match = True
            else:
                self.warning("error_list: 'substr' and 'regex' not in %s" %
                             error_check)
            if match:
                level = error_check.get('level', INFO)
                if self.log_output:
                    message = ' %s' % line
                    if error_check.get('explanation'):
                        message += '\n %s' % error_check['explanation']
                    if error_check.get('summary'):
                        self.add_summary(message, level=level)
                    else:
                        if self.use_buffer:
                            # we don't log anything, just modify the buffer
                            self.context_buffer[buffer_index] = (message, level)
                            if error_check.get('context_lines'):
                                limits = error_check['context_lines']
                                self.generate_context_lines(buffer_index, level,
                                                            limits)
                        else:
                            self.log(message, level=level)
                if level in (ERROR, CRITICAL, FATAL):
                    self.num_errors += 1
                # TODO set self.error_status (or something)
                # that sets the worst error level hit.
                break
        else:
            if self.use_buffer:
                # leave the line in buffer as is
                pass
            else:
                if self.log_output:
                    self.info(' %s' % line)

    def _validate_line(self, line):
        if not line or line.isspace():
            return None
        return line.decode("utf-8").rstrip()

    def add_lines(self, output):
        if isinstance(output, basestring):
            output = [output]
        if self.use_buffer:
            for line in output:
                line = self._validate_line(line)
                self.append_to_buffer_and_parse(line) if line else None
            # now empty the remaining lines left in the buffer
            self.flush_buffer_and_parse()
        else:
            # behave normally
            for line in output:
                line = self._validate_line(line)
                self.parse_single_line(line) if line else None

    def append_to_buffer_and_parse(self, line):
        message_and_level = line, INFO
        if len(self.context_buffer) == self.buffer_limit:
            # buffer is full, start parsing middle elem and
            # then behave like a queue FIFO
            middle_elem = self.buffer_limit / 2
            line_to_parse = self.context_buffer[middle_elem][0]
            self.parse_single_line(line_to_parse, buffer_index=middle_elem)
            log_message, log_level = self.context_buffer.pop(0)
            self.log(log_message, log_level)
        # keep adding new lines to the buffer
        self.context_buffer.append(message_and_level)

    def generate_context_lines(self, target_index, target_level, limits):
        # check that the requested pre and post context lengths are doable
        warn_message = ""
        if limits.get('pre') > target_index:
            warn_message += CONTEXT_WARN_MESSAGE % {
                'buffer': target_index,
                'type': 'pre', 'context': limits['pre']}
            limits['pre'] = target_index
        if limits.get('post') >= len(self.context_buffer) - target_index:
            warn_message += CONTEXT_WARN_MESSAGE % {
                'buffer': len(self.context_buffer) - target_index - 1,
                'type': 'post', 'context': limits['post']}
            limits['post'] = len(self.context_buffer) - target_index - 1

        pre = target_index - limits['pre']
        post = target_index + limits['post'] + 1
        context_lines = list(self.context_buffer)[pre:post]
        for i, message_and_level in enumerate(context_lines):
            buffer_index = i + pre
            message, log_level = message_and_level
            if buffer_index == target_index:
                message = "%s %s" % (self.match_strings['match'], message.lstrip())
                if warn_message:
                    message += warn_message
            else:  # context
                if message.startswith('$'):
                    continue  # ignore other regex's that want context
                message = "%s %s" % (self.match_strings['context'], message)
                log_level = self.worst_level(target_level, log_level)
            self.context_buffer[buffer_index] = (message, log_level)

    def flush_buffer_and_parse(self):
        # behave like append_to_buffer_and_parse but continue in a
        # loop until buffer is empty and always taking the middle
        # elem of the buffer to maximize remaining context lines
        while self.context_buffer:
            middle_elem = len(self.context_buffer) / 2
            line_to_parse = self.context_buffer[middle_elem][0]
            self.parse_single_line(line_to_parse, buffer_index=middle_elem)
            log_message, log_level = self.context_buffer.pop(0)
            self.log(log_message, log_level)

    def worst_level(self, target_level, existing_level, levels=None):
        """returns either existing_level or target level.
        This depends on which is closest to levels[0]
        By default, levels is the list of log levels"""
        if not levels:
            levels = [IGNORE, FATAL, CRITICAL, ERROR, WARNING, INFO, DEBUG]
        if target_level not in levels:
            self.fatal("'%s' not in %s'." % (target_level, levels))
        for l in levels:
            if l in (target_level, existing_level):
                return l


# BaseLogger {{{1
class BaseLogger(object):
    """Create a base logging class.
    TODO: status? There may be a status object or status capability in
    either logging or config that allows you to count the number of
    error,critical,fatal messages for us to count up at the end (aiming
    for 0).
    """
    LEVELS = {DEBUG: logging.DEBUG,
              INFO: logging.INFO,
              WARNING: logging.WARNING,
              ERROR: logging.ERROR,
              CRITICAL: logging.CRITICAL,
              FATAL: FATAL_LEVEL
             }

    def __init__(self, log_level=INFO,
                 log_format='%(message)s',
                 log_date_format='%H:%M:%S',
                 log_name='test',
                 log_to_console=True,
                 log_dir='.',
                 log_to_raw=False,
                 logger_name='',
                 halt_on_failure=True,
                 append_to_log=False,
                ):
        self.halt_on_failure = halt_on_failure,
        self.log_format = log_format
        self.log_date_format = log_date_format
        self.log_to_console = log_to_console
        self.log_to_raw = log_to_raw
        self.log_level = log_level
        self.log_name = log_name
        self.log_dir = log_dir
        self.append_to_log = append_to_log

        # Not sure what I'm going to use this for; useless unless we
        # can have multiple logging objects that don't trample each other
        self.logger_name = logger_name

        self.all_handlers = []
        self.log_files = {}

        self.create_log_dir()

    def create_log_dir(self):
        if os.path.exists(self.log_dir):
            if not os.path.isdir(self.log_dir):
                os.remove(self.log_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.abs_log_dir = os.path.abspath(self.log_dir)

    def init_message(self, name=None):
        if not name:
            name = self.__class__.__name__
        self.log_message("%s online at %s in %s" % \
                         (name, datetime.now().strftime("%Y%m%d %H:%M:%S"),
                         os.getcwd()))

    def get_logger_level(self, level=None):
        if not level:
            level = self.log_level
        return self.LEVELS.get(level, logging.NOTSET)

    def get_log_formatter(self, log_format=None, date_format=None):
        if not log_format:
            log_format = self.log_format
        if not date_format:
            date_format = self.log_date_format
        return logging.Formatter(log_format, date_format)

    def new_logger(self, logger_name):
        """Create a new logger.
        By default there are no handlers.
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(self.get_logger_level())
        self._clear_handlers()
        if self.log_to_console:
            self.add_console_handler()
        if self.log_to_raw:
            self.log_files['raw'] = '%s_raw.log' % self.log_name
            self.add_file_handler(os.path.join(self.abs_log_dir,
                                               self.log_files['raw']),
                                 log_format='%(message)s')

    def _clear_handlers(self):
        """To prevent dups -- logging will preserve Handlers across
        objects :(
        """
        attrs = dir(self)
        if 'all_handlers' in attrs and 'logger' in attrs:
            for handler in self.all_handlers:
                self.logger.removeHandler(handler)
            self.all_handlers = []

    def __del__(self):
        logging.shutdown()
        self._clear_handlers()

    def add_console_handler(self, log_level=None, log_format=None,
                          date_format=None):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.get_logger_level(log_level))
        console_handler.setFormatter(self.get_log_formatter(log_format=log_format,
                                                            date_format=date_format))
        self.logger.addHandler(console_handler)
        self.all_handlers.append(console_handler)

    def add_file_handler(self, log_path, log_level=None, log_format=None,
                       date_format=None):
        if not self.append_to_log and os.path.exists(log_path):
            os.remove(log_path)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(self.get_logger_level(log_level))
        file_handler.setFormatter(self.get_log_formatter(log_format=log_format,
                                                         date_format=date_format))
        self.logger.addHandler(file_handler)
        self.all_handlers.append(file_handler)

    def log_message(self, message, level=INFO, exit_code=-1):
        """Generic log method.
        There should be more options here -- do or don't split by line,
        use os.linesep instead of assuming \n, be able to pass in log level
        by name or number.

        Adding the IGNORE special level for runCommand.
        """
        if level == IGNORE:
            return
        for line in message.splitlines():
            self.logger.log(self.get_logger_level(level), line)
        if level == FATAL and self.halt_on_failure:
            self.logger.log(FATAL_LEVEL, 'Exiting %d' % exit_code)
            raise SystemExit(exit_code)



# SimpleFileLogger {{{1
class SimpleFileLogger(BaseLogger):
    """Create one logFile.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self,
                 log_format='%(asctime)s %(levelname)8s - %(message)s',
                 logger_name='Simple', log_dir='logs', **kwargs):
        BaseLogger.__init__(self, logger_name=logger_name, log_format=log_format,
                            log_dir=log_dir, **kwargs)
        self.new_logger(self.logger_name)
        self.init_message()

    def new_logger(self, logger_name):
        BaseLogger.new_logger(self, logger_name)
        self.log_path = os.path.join(self.abs_log_dir, '%s.log' % self.log_name)
        self.log_files['default'] = self.log_path
        self.add_file_handler(self.log_path)




# MultiFileLogger {{{1
class MultiFileLogger(BaseLogger):
    """Create a log per log level in log_dir.  Possibly also output to
    the terminal and a raw log (no prepending of level or date)
    """
    def __init__(self, logger_name='Multi',
                 log_format='%(asctime)s %(levelname)8s - %(message)s',
                 log_dir='logs', log_to_raw=True, **kwargs):
        BaseLogger.__init__(self, logger_name=logger_name,
                            log_format=log_format,
                            log_to_raw=log_to_raw, log_dir=log_dir,
                            **kwargs)

        self.new_logger(self.logger_name)
        self.init_message()

    def new_logger(self, logger_name):
        BaseLogger.new_logger(self, logger_name)
        min_logger_level = self.get_logger_level(self.log_level)
        for level in self.LEVELS.keys():
            if self.get_logger_level(level) >= min_logger_level:
                self.log_files[level] = '%s_%s.log' % (self.log_name,
                                                       level)
                self.add_file_handler(os.path.join(self.abs_log_dir,
                                                   self.log_files[level]),
                                      log_level=level)



# __main__ {{{1

if __name__ == '__main__':
    pass
