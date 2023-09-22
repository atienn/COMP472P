from dataclasses import dataclass
from typing import ClassVar
from io import TextIOWrapper
import os


# Singleton instance.
@dataclass(slots=True)
class FileOutput:
    output_file: ClassVar[TextIOWrapper] = None
    file_writing_enabled: ClassVar[bool] = False

    @classmethod
    def enable_file_logging(cls):
        cls.file_writing_enabled = True
        
    @classmethod
    def disable_file_logging(cls):
        cls.file_writing_enabled = False
        

    @classmethod
    def open_file(cls, file_name):
        file_name_unique = file_name + ".txt"
        i = 0

        # ensure that we don't overwrite an existing file
        while os.path.exists(file_name_unique):
            i += 1
            file_name_unique = "{}({}).txt".format(file_name, i) #file_name + '(' + i.__str__() + ')'

        print("Writing game output to \"" + file_name_unique + "\"")
        # open file in overwrite mode
        cls.output_file = open(file_name_unique, 'w')
        cls.file_writing_enabled = True

    @classmethod
    def log(cls, str: str, end = '\n'):
        print(str, end)

        if not cls.file_writing_enabled:
            return # If there is no file logging enabled, do nothing else.
        if cls.output_file == None or cls.output_file.closed:
            print("Target output file is missing or closed. Open a file before logging.")
            return

        cls.output_file.write(str)

    @classmethod
    def close(cls):
        if cls.output_file == None or cls.output_file.closed:
            return
        cls.output_file.close()
        cls.file_writing_enabled = False

# Public method that can be called by anyone
def log(to_log = "", end = '\n'):
    return FileOutput.log(to_log.__str__(), end)