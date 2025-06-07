import datetime
from os.path import join, dirname, realpath, exists
from os import makedirs, rename, listdir, remove
import inspect
import re
from .config import APP_NAME


class Logger:

    def __init__(
        self,
        log_file_location="logs",
        process=APP_NAME,
        log_rotate_retention=10000,
        log_file_ext="log",
        max_log_files_retention=20,
    ):
        """
        Parameters:
          log_file_location (string): Location of the logs directory (relative to the project)
        """
        self.log_file_location = join(dirname(realpath(__file__)), "../",
                                      log_file_location)
        self.old_logs_location = join(self.log_file_location, "old/")
        self.process = process
        self.log_file_ext = log_file_ext
        self.log_rotate_retention = log_rotate_retention
        self._make_logs_dir()
        self.current_file_nb_logs = self._get_nb_lines_in_file(
            self.log_file_location)
        self.max_log_files_retention = max_log_files_retention

    def _make_logs_dir(self):
        """
        Creates the directory where the logs are stored if it does not already exists.
        """
        if not exists(self.log_file_location):
            makedirs(self.log_file_location)

        if not exists(self.old_logs_location):
            makedirs(self.old_logs_location)

    def _append_to_file(self, line, path):
        """
        Appends a line of text to a file
        Parameters:
          line (string): Line of text to append to the logfile
          path (string): The path of the file to append the line to
        """
        with open(path, "a") as file:
            file.write(line)
            self.current_file_nb_logs += 1

        if self.current_file_nb_logs >= self.log_rotate_retention:
            # We reached the limit
            self._move_current_logfile_to_archive()
            self.current_file_nb_logs = 0

    def _move_current_logfile_to_archive(self):
        """Used to archive old log files based on log_rotate_retention and max_log_files_retention"""
        old_log_files = listdir(self.old_logs_location)
        log_files_numbers = []
        for f in old_log_files:
            if f.startswith(self.process) and f.endswith(self.log_file_ext):
                match = re.match(r".*\.(\d+)\..*", f)
                log_files_numbers.append(int(match.groups()[0]))
        log_files_numbers.sort()
        new_file_name = self._create_file_name().replace(
            ".",
            f".{(log_files_numbers[-1] if len(log_files_numbers) > 0 else 0) + 1}."
        )
        new_path = join(self.old_logs_location, new_file_name)
        old_path = join(self.log_file_location, self._create_file_name())
        if len(log_files_numbers) > self.max_log_files_retention:
            # We need to remove old log files
            top_offset = len(log_files_numbers) - self.max_log_files_retention
            to_remove = log_files_numbers[0:top_offset]
            for n in to_remove:
                f_name = join(
                    self.old_logs_location,
                    self._create_file_name().replace(".", f".{n}."),
                )
                remove(f_name)
        try:
            rename(old_path, new_path)
        except Exception as e:
            print(f"Looks like your log file does not exists : {old_path}")
            print(e)

    def _get_nb_lines_in_file(self, path):
        """Returns the number of lines in a file"""
        try:
            with open(path, "r") as fp:
                return len(fp.readlines())
            return 0
        except:
            return 0

    def _create_line(self, text, level):
        """
        Creates a standardized log line
        Parameters:
          text (string): The line of log
          level (string): the log level
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")
        frame = inspect.stack()[3]
        return f"{timestamp} {str(level).upper()} [{self.process}] [{frame.filename}:{frame.lineno}] {text}\n"

    def _create_file_name(self):
        """Returns the current log file name"""
        return f"{self.process}.{self.log_file_ext}"

    def debug(self, args):
        """
        Writes a DEBUG log to the log file
        """
        file = join(self.log_file_location, self._create_file_name())
        line = self._create_line(str(args), "debug")
        self._append_to_file(line, file)
        print(line)

    def error(self, args):
        """
        Writes a ERROR log to the log file
        """
        file = join(self.log_file_location, self._create_file_name())
        line = self._create_line(str(args), "error")
        self._append_to_file(line, file)
        print(line)

    def warning(self, args):
        """
        Writes a WARNING log to the log file
        """
        file = join(self.log_file_location, self._create_file_name())
        line = self._create_line(str(args), "warning")
        self._append_to_file(line, file)
        print(line)

    def info(self, args):
        """
        Writes an INFO log to the log file
        """
        file = join(self.log_file_location, self._create_file_name())
        line = self._create_line(str(args), "info")
        self._append_to_file(line, file)
        print(line)

    def fatal(self, args):
        """
        Writes a FATAL log to the log file
        """
        file = join(self.log_file_location, self._create_file_name())
        line = self._create_line(str(args), "fatal")
        self._append_to_file(line, file)
        print(line)

    def success(self, args):
        """
        Writes a SUCCESS log to the log file
        """
        file = join(self.log_file_location, self._create_file_name())
        line = self._create_line(str(args), "success")
        self._append_to_file(line, file)
        print(line)


logger = Logger()
