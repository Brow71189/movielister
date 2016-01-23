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
import json

class Movielister(object):

    def __init__(self):
        self.supported_types = ['.avi', '.mpg', '.wmv', '.mov', '.mkv']
        self.list_recursive = True
        self.delete_non_existant = True
        self.always_update_all = False
        self.max_recursion_depth = -1
        self.current_recursion_depth = 0
        self.movie_list = []
        self.database_tree = None
        self.movie_path = '.'
        self.database_path = '.'
        self.ffprobe_path = 'avprobe'
        self.ffprobe_options = '-of json -show_format -show_streams -loglevel quiet'
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
            counter = 0
            for movie in database_movie_list:
                if os.path.basename(moviename) == movie.get('filename'):
                    found = True
                    break
                counter += 1
            
            if not found:
                print('Creating new entry for ' + moviename)
                self.database_tree.getroot().append(self.create_movie_node(moviename))
            else:
                now_last_updated = time.strftime('%Y_%m_%d_%H_%M', time.localtime(os.path.getmtime(moviename)))
                last_updated = database_movie_list[counter].find('date_modified')
#		print(now_last_updated)
#		print(last_updated.text)
                if self.always_update_all or (last_updated is not None and now_last_updated > last_updated.text):
                    print('Updating entry for ' + moviename)
                    self.update_movie_node(database_movie_list[counter], moviename)
        
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
        
    def update_movie_node(self, movie_node, filename):
        metadata_dict = self.get_movie_metadata(filename)
        
        for key, value in metadata_dict.items():
            movie_property = movie_node.find(key)
            if key in self.metadata_elements and movie_property is not None:
                movie_property.text = str(value)
            elif movie_property is not None:
                movie_node.remove(movie_property)
            elif key in self.metadata_elements:
                movie_property = ElementTree.Element(key)
                movie_property.text = str(value)
                movie_node.append(movie_property)
    
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
#            ffmpeg_out = subprocess.check_output([self.ffprobe_path, filename], stderr=subprocess.STDOUT,
#                                                 universal_newlines=True)
            args_list = []
            args_list.append(self.ffprobe_path)
            args_list.extend(self.ffprobe_options.split())
            args_list.append(filename)
            ffmpeg_out = subprocess.check_output(args_list)
            ffmpeg_out = json.loads(ffmpeg_out)
        except Exception as detail:
            print('Could not get ffmpeg metadata for ' + filename + '. Reason: ' + str(detail))
            return ffmpeg_metadata
        
        #ffmpeg_out = ffmpeg_out.split('\n')
        
        try:
            duration = float(ffmpeg_out['format']['duration'])
            duration = int(duration/60) + (0 if duration%60 < 30 else 1)
            ffmpeg_metadata['duration_minutes'] = str(duration)
        except Exception as detail:
            print('Could not extract video duration from ' + filename + '. Reason: ' + str(detail))
        
        video_stream = None
        try:
            for i in range(len(ffmpeg_out['streams'])):
                if ffmpeg_out['streams'][i]['codec_type'] == 'video':
                    video_stream = ffmpeg_out['streams'][i]
                    break
            else:
                raise Exception('No video stream found in list of streams.')
                
        except Exception as detail:
            print('Could not find any video streams in ' + filename + '. Reason: ' + str(detail))
            return ffmpeg_metadata
        
        try:
            ffmpeg_metadata['video_codec'] = video_stream['codec_name']
        except Exception as detail:
            print('Could not extract video codec info from ' + filename + '. Reason: ' + str(detail))
            
        try:
            ffmpeg_metadata['resolution'] = str(video_stream['width']) + 'x' + str(video_stream['height'])
        except Exception as detail:
            print('Could not extract video resolution from ' + filename + '. Reason: ' + str(detail))
            
#        for element in ffmpeg_out:
#            element = element.strip().lower()
#            if element.startswith('duration'):
#                try:
#                    element = element.split(', ')[0]
#                    element = element.split(': ')[1]
#                    element = element.split(':')
#                    element = 60*int(element[0]) + int(element[1]) + (0 if float(element[2]) < 30 else 1)
#                    ffmpeg_metadata['duration_minutes'] = str(element)
#                except Exception as detail:
#                    print('Could not extract video duration from ' + filename + '. Reason: ' + str(detail))
#            elif element.startswith('stream #0') and element.find('video:') > -1:
#                try:
#                    element = element.split(', ')
#                    codec = element[0].split('video:')[1].strip()
#                    codec = codec.split()[0]
#                    resolution = element[2].strip().split()[0] if ((element[2].find('sar') > -1 or
#								    element[2].find('par') > -1)
#								    and element[2].find('dar') > -1) else (
#                                                                                          element[3].strip().split()[0])
#                    ffmpeg_metadata['video_codec'] = codec
#                    ffmpeg_metadata['resolution'] = resolution
#                except Exception as detail:
#                    print('Could not extract video codec and resolution from ' + filename + '. Reason: ' + str(detail))

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
