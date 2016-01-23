# -*- coding: utf-8 -*-
"""
Created on Sat Jan 16 11:21:24 2016

@author: Andi
"""

import sys
import os
import time
import subprocess
from xml.etree import ElementTree
import ast

class Movielister(object):

    def __init__(self):
        self.supported_types = ['.avi', '.mpg']
        self.list_recursive = True
        self.delete_non_existant = True
        self.max_recursion_depth = -1
        self.current_recursion_depth = 0
        self.movie_list = []
        self.database_tree = None
        self.movie_path = 'K:/Users/Andi/Videos/OTR'
        self.database_path = 'K:/Users/Andi/Videos/OTR/movie_database.xml'
        self.ffprobe_path = 'C:/Program Files/ffmpeg-20160116-git-d7c75a5-win64-static/bin/ffprobe.exe'
        self.metadata_elements = ['title', 'duration_minutes', 'resolution', 'language', 'date_on_tv', 'channel',
                                  'date_modified', 'file_size', 'video_codec', 'extension']
        self.htmls_path = None

    def read_config(self):
        try:
            configfile = open(os.path.join(os.path.dirname(sys.argv[0]), 'movielister.conf'))
        except (IOError, OSError):
            print('Could not find config file. Make sure it is in the same folder as the script an is called ' + 
                  '"movielister.conf"!')
            return
        
        for line in configfile:
            if line.startswith('#'):
                continue
            
            splitline = line.split(':', 1)
            if len(splitline) == 2:
                try:
                    setattr(self, splitline[0].strip(), ast.literal_eval(splitline[1].strip()))
                except AttributeError:
                    print('Parameter ' + splitline[0].strip() + ' is not known. It will be ignored.')
                
    
    def load_database(self):
        self.database_path = os.path.normpath(self.database_path)
        try:
            self.database_tree = ElementTree.parse(self.database_path)
        except (OSError, IOError, ElementTree.ParseError):
            print('Could not find a movie database in ' + self.database_path  + '. Creating a new empty one.')
            self.database_tree = ElementTree.ElementTree()
        finally:
            if self.database_tree.getroot() is None:
                self.database_tree._setroot(ElementTree.Element('movielist',
                                                                attrib={'created': time.strftime('%Y_%m_%d_%H_%M')}))
                                                                        
    def save_database(self):
        self.database_tree.write(self.database_path)
    
    def update_database(self):
        if self.delete_non_existant:
            for movie in self.database_tree.getroot().findall('movie'):
                found = False
                for moviename in self.movie_list:
                    if os.path.basename(moviename) == movie.get('filename'):
                        found = True
                        break
                if not found:
                    print('Deleting ' + movie.get('filename'))
                    self.database_tree.getroot().remove(movie)
        
        database_movie_list = self.database_tree.getroot().findall('movie')
        for moviename in self.movie_list:
            found = False
            for movie in database_movie_list:
                if os.path.basename(moviename) == movie.get('filename'):
                    found = True
                    break
            
            if not found:
                print('Creating new entry for ' + moviename)
                self.database_tree.getroot().append(self.create_movie_node(moviename))
        
        self.database_tree.getroot().set('last_updated', time.strftime('%Y_%m_%d_%H_%M'))
        self.database_tree.getroot().set('metadata_elements', str(self.metadata_elements))
    
    def create_movie_node(self, filename):
        movie_node = ElementTree.Element('movie', attrib={'filename': os.path.basename(filename)})
        metadata_dict = self.get_movie_metadata(filename)
        
        for key, value in metadata_dict.items():
            if key in self.metadata_elements:
                movie_property = ElementTree.Element(key)
                movie_property.text = str(value)
                movie_node.append(movie_property)
        
        return movie_node       
    
    def get_movielist(self, movie_path=None, current_recursion_depth=0):
        self.movie_path = os.path.normpath(self.movie_path)
        if not movie_path:
            movie_path = self.movie_path
        
        dirlist = os.listdir(movie_path)
        
        for item in dirlist:
            item = os.path.join(movie_path, item)
            if os.path.isfile(item) and os.path.splitext(item)[1] in self.supported_types:
                self.movie_list.append(item)
            elif os.path.isdir(item) and self.list_recursive and (current_recursion_depth < 
                                                                  self.max_recursion_depth or
                                                                  self.max_recursion_depth == -1):
                self.get_movielist(movie_path=item, current_recursion_depth=(current_recursion_depth+1))
    
    def get_movie_metadata(self, filename):
        movie_metadata = {}
        movie_metadata['file_size'] =  os.path.getsize(filename)
        movie_metadata['date_modified'] =  time.strftime('%Y_%m_%d_%H_%M', time.localtime(os.path.getmtime(filename)))
        movie_metadata.update(self.analyze_ffmpeg(filename))
        movie_metadata.update(self.analyze_filename(filename))
        
        return movie_metadata
    
    def analyze_ffmpeg(self, filename):
        self.ffprobe_path = os.path.normpath(self.ffprobe_path)
        ffmpeg_metadata = {}
        try:
            ffmpeg_out = subprocess.check_output([self.ffprobe_path, filename], stderr=subprocess.STDOUT,
                                                 universal_newlines=True)
        except Exception as detail:
            print('Could not get ffmpeg metadata for ' + filename + '. Reason: ' + str(detail))
            return ffmpeg_metadata
        
        ffmpeg_out = ffmpeg_out.split('\n')
        
        for element in ffmpeg_out:
            element = element.strip().lower()
            if element.startswith('duration'):
                try:
                    element = element.split(', ')[0]
                    element = element.split(': ')[1]
                    element = element.split(':')
                    element = 60*int(element[0]) + int(element[1]) + (0 if float(element[2]) < 30 else 1)
                    ffmpeg_metadata['duration_minutes'] = str(element)
                except Exception as detail:
                    print('Could not extract video duration from ' + filename + '. Reason: ' + str(detail))
            elif element.startswith('stream #0') and element.find('video:') > -1:
                try:
                    element = element.split(', ')
                    codec = element[0].split('video:')[1].strip()
                    codec = codec.split()[0]
                    resolution = element[2].strip().split()[0] if ((element[2].find('sar') > -1 or
								    element[2].find('par') > -1)
								    and element[2].find('dar') > -1) else (
                                                                                          element[3].strip().split()[0])
                    ffmpeg_metadata['video_codec'] = codec
                    ffmpeg_metadata['resolution'] = resolution
                except Exception as detail:
                    print('Could not extract video codec and resolution from ' + filename + '. Reason: ' + str(detail))

        return ffmpeg_metadata
        
    def analyze_filename(self, filename):
        filename_metadata = {}
        filename = os.path.basename(filename)
        filename, extension = os.path.splitext(filename)
        extension = extension.lower()
        if extension.startswith('.'):
            extension = extension[1:]
        if filename.find('TVOON') > -1:
            try:
                filename = filename.rsplit('_', 6)
                filename_metadata['title'] = filename[0].replace('_', ' ')
                filename_metadata['channel'] = filename[3]
                filename_metadata['language'] = filename[6].split('.')[0]
                date_on_tv = filename[1].split('.')
                date_on_tv.extend(filename[2].split('-'))
                filename_metadata['date_on_tv'] = '_'.join(date_on_tv)
            except Exception as detail:
                print('Could not extract date, tv channel and language from title of ' + str(filename) + '. Reason: ' + 
                      str(detail))
                if filename_metadata.get('title') is None:
                    filename_metadata['title'] = filename
        else:
            print('Could not extract date, tv channel and language from title of ' + filename + '.')
            filename_metadata['title'] = filename
        
        filename_metadata['extension'] = extension    
        return filename_metadata
    
    def main(self):
        self.read_config()
        self.get_movielist()
        self.load_database()
        self.update_database()
        self.save_database()

if __name__ == '__main__':
    Lister = Movielister()
    Lister.main()
