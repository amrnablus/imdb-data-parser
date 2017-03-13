"""
This file is part of imdb-data-parser.

imdb-data-parser is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

imdb-data-parser is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with imdb-data-parser.  If not, see <http://www.gnu.org/licenses/>.
"""

from .baseparser import *
import json


class SoundtrackParser(BaseParser):
    """
    Parses movies.list dump

    RegExp: /((.*? \(\S{4,}\)) ?(\(\S+\))? ?(?!\{\{SUSPENDED\}\})(\{(.*?) ?(\(\S+?\))?\})? ?(\{\{SUSPENDED\}\})?)\t+(.*)$/gm
    pattern: ((.*? \(\S{4,}\)) ?(\(\S+\))? ?(?!\{\{SUSPENDED\}\})(\{(.*?) ?(\(\S+?\))?\})? ?(\{\{SUSPENDED\}\})?)\t+(.*)$
    flags: gm
    8 capturing groups:
        group 1: #TITLE (UNIQUE KEY)
        group 2: (.*? \(\S{4,}\))                    movie name + year
        group 3: (\(\S+\))                           type ex:(TV)
        group 4: (\{(.*?) ?(\(\S+?\))?\})            series info ex: {Ally Abroad (#3.1)}
        group 5: (.*?)                               episode name ex: Ally Abroad
        group 6: ((\(\S+?\))                         episode number ex: (#3.1)
        group 7: (\{\{SUSPENDED\}\})                 is suspended?
        group 8: (.*)                                year
    """

    # properties
    base_matcher_pattern = "# (\"?(.*?)\"? \((\S{4,})\) ?(\(\S+\))? ?(?!\{\{SUSPENDED\}\})(\{(.*?) ?(\(\S+?\))?\})? ?(\{\{SUSPENDED\}\})?)"
    
    
    input_file_name = "soundtracks.list"
    #FIXME: zafer: I think using a static number is critical for us. If imdb sends a new file with first 10 line fucked then we're also fucked
    number_of_lines_to_be_skipped = 14
    db_table_info = {
        'tablename' : 'movies',
        'columns' : [
            {'colname' : 'title', 'colinfo' : DbScriptHelper.keywords['string'] + '(255) NOT NULL'},
            {'colname' : 'full_name', 'colinfo' : DbScriptHelper.keywords['string'] + '(127)'},
            {'colname' : 'type', 'colinfo' : DbScriptHelper.keywords['string'] + '(20)'},
            {'colname' : 'ep_name', 'colinfo' : DbScriptHelper.keywords['string'] + '(127)'},
            {'colname' : 'ep_num', 'colinfo' : DbScriptHelper.keywords['string'] + '(20)'},
            {'colname' : 'suspended', 'colinfo' : DbScriptHelper.keywords['string'] + '(20)'},
            {'colname' : 'year', 'colinfo' : DbScriptHelper.keywords['string'] + '(20)'}
        ],
        'constraints' : 'PRIMARY KEY(title)'
    }
    end_of_dump_delimiter = "--------------------------------------------------------------------------------"

    def __init__(self, preferences_map):
        super(SoundtrackParser, self).__init__(preferences_map)
        self.first_one = True
        self.current_movie = False
        self.current_track = False
        self.data = {}

    def parse_into_tsv(self, matcher):
        
#         self.data = {}
#         if(self.line.find( 'The Shawshank Redemption') > 0 ):
#                 import pdb;pdb.set_trace()
        is_match = matcher.match(self.base_matcher_pattern)
        self.matcher = matcher
        logging.debug("Line: " + self.line)
        if self.line.startswith("#"):
            self.current_movie = self.current_track = False
            
#         self.data[self.current_movie] = {}
        
        if(is_match):
#             json.dumps(self.data)

            self.json_file.write(json.dumps(self.data) + "\n")
            self.data = {}
            self.current_movie = matcher.group(2).strip()
            if matcher.group(3):
                self.current_movie += "___" + matcher.group(3).strip()
            if matcher.group(6):
                episode_name = matcher.group(6)
                self.current_movie += "___" + episode_name.strip()
            else:
                self.current_movie += "___"
            if matcher.group(7):
                episode_number = matcher.group(7)
                self.current_movie += "___" + episode_number.strip()

            
            self.data[self.current_movie] = {}
        else:
            type = "fucked"
            matches = False
            if self.current_movie: 
                #meaning, this is a song info
                if self.line.startswith('- "'):
                    self.current_track = self.handle_track_name()
                    self.data[self.current_movie][self.current_track] = {}
                    
                if self.line.lower().find('written by') != -1:
                    type = "written"
                    matches = self.handle_star_by()
                if self.line.lower().find('performed by') != -1:
                    type = "performed"
                    matches = self.handle_star_by()
                if self.line.lower().find('conducted by') != -1:
                    type = "conducted"
                    matches = self.handle_star_by()
                if self.line.lower().find('music by') != -1:
                    type = "music"
                    matches = self.handle_star_by()
                if self.line.lower().find('sung by') != -1:
                    type = "sung"
                    matches = self.handle_star_by()
                if self.line.lower().find('lyric') != -1:
                    type = "lyrics"
                    matches = self.handle_star_by()
            
                strip = lambda x, y: (y.strip())

                if  isinstance(matches, dict):
                    matches = dict(map(strip, matches.iteritems()))

                if self.current_movie and self.current_track and matches:
                    self.data[self.current_movie][self.current_track][type] = matches[1:]

                if type == "fucked":
                    self.fucked_up_count += 1
                    logging.critical("This line is fucked up: " + matcher.get_last_string())
                    
                try:
                    logging.debug("CurrentTrack: " + self.current_track + ", Type: " + type + ", value: " + str(matches) )
                except Exception as e:
                    logging.critical(e)
                            
            

    def handle_track_name(self):
        is_track_title = self.matcher.match('(\-\s*)"?([^\"]*)"?(?:uncredited)?')
        if is_track_title:
            return self.matcher.group(2)
        
        return False
    
    def handle_star_by(self):
        is_match = self.matcher.match("(.*\s*by)\s*'?([^']*)'?([^']*)(?:with)?\s*'?([^']*)(\s*)'?.*")
        matches = []
        if is_match:
            matches.append(self.matcher.group(1))
            if self.matcher.group(2) != None:
                matches.append(self.matcher.group(2))
        return matches
    
    
    def parse_into_db(self, matcher):
        is_match = matcher.match(self.base_matcher_pattern)

        if(is_match):
            if(self.first_one):
                self.sql_file.write("(" + self.concat_regex_groups([1,2,3,5,6,7,8], [0,1,2,3,4,5,6], matcher) + ")")
                self.first_one = False;
            else:
                self.sql_file.write(",\n(" + self.concat_regex_groups([1,2,3,5,6,7,8], [0,1,2,3,4,5,6], matcher) + ")")
        else:
            logging.critical("This line is fucked up: " + matcher.get_last_string())
            self.fucked_up_count += 1
