# -*- coding: utf-8 -*-
"""
Created on Sat Jan 16 18:58:23 2016

@author: Andi
"""

import lister
#from xml.etree import ElementTree
import ast
import copy
import os
_has_natsort = True
try:
    import natsort
except ImportError:
    print('"natsort" module not found. It is highly recommended to have it installed. Without, sorting might give ' + 
          'unexpected results.')
    _has_natsort = False

class HTMLMaker(object):
    
    def __init__(self):
        self.Movielister = None
        self.metadata_elements = None
        self._sortkeys = {'title': self.sortkey_title, 'duration_minutes': self.sortkey_duration,
                          'resolution': self.sortkey_resolution, 'language': self.sortkey_language,
                          'date_on_tv': self.sortkey_date_on_tv, 'channel': self.sortkey_channel,
                          'date_modified': self.sortkey_date_modified, 'file_size': self.sortkey_filesize,
                          'video_codec': self.sortkey_video_codec, 'extension': self.sortkey_extension,
                          'user': self.sortkey_user}
    
    def list_movies_and_create_html(self):
        if self.Movielister is None:
            self.Movielister = lister.Movielister()
        
        self.Movielister.main()
        self.metadata_elements = ast.literal_eval(self.Movielister.database_tree.getroot().get('metadata_elements'))
        self.generate_html()
        
    def sortkey_title(self, xmlnode):
        title = xmlnode.findtext('title', default='zzzzz').lower()
        if title.startswith(('the ', 'der ', 'die ', 'das ')):
            title = title[4:]
        
        return title

    def sortkey_duration(self, xmlnode):
        duration = xmlnode.findtext('duration_minutes', default=float('inf'))
        try:
            duration = float(duration)
        except:
            print('Could not convert duration to float')
            duration = float('inf')

        if not _has_natsort:
            return duration
        
        return (duration, self.sortkey_title(xmlnode))
        
    def sortkey_resolution(self, xmlnode):
        resolution = xmlnode.findtext('resolution', default='0x0').split('x')
        if len(resolution) == 2:
            try:            
                resolution = (float(resolution[0]), float(resolution[1]))
            except:
                resolution = (0, 0)
        
        if not _has_natsort:
            return resolution
        
        return resolution + (self.sortkey_title(xmlnode), )
        
    def sortkey_language(self, xmlnode):
        language = xmlnode.findtext('language', default='zzzzz').lower()
        
        return (language, self.sortkey_title(xmlnode))
        
    def sortkey_channel(self, xmlnode):
        channel = xmlnode.findtext('channel', default='zzzzz').lower()
        
        return (channel, self.sortkey_title(xmlnode))
        
    def sortkey_date_on_tv(self, xmlnode):
        date = xmlnode.findtext('date_on_tv', default='zzzzz').lower()
        
        return (date, self.sortkey_title(xmlnode))
    
    def sortkey_date_modified(self, xmlnode):
        date = xmlnode.findtext('date_modified', default='zzzzz').lower()
        
        return (date, self.sortkey_title(xmlnode))
        
    def sortkey_filesize(self, xmlnode):
        filesize = xmlnode.findtext('file_size', default=float('inf'))
        try:
            filesize = float(filesize)
        except:
            print('Could not convert filesize to float')
            filesize = float('inf')

        if not _has_natsort:
            return filesize
        
        return (filesize, self.sortkey_title(xmlnode))
        
    def sortkey_video_codec(self, xmlnode):
        codec = xmlnode.findtext('video_codec', default='zzzzz').lower()
        
        return (codec, self.sortkey_title(xmlnode))
        
    def sortkey_extension(self, xmlnode):
        extension = xmlnode.findtext('extension', default='zzzzz').lower()
        
        return (extension, self.sortkey_title(xmlnode))

    def sortkey_user(self, xmlnode):
        user = xmlnode.findtext('user', default='zzzzz').lower()
        
        return (user, self.sortkey_title(xmlnode))

    def sort_tree_by_metadata_element(self, xmltree, metadata_element, reverse=False):
#        xmltree = copy.deepcopy(xmltree)
#        movies = xmltree.getroot()
#        
#        sortedmovies = []
#        
#        for movie in movies:
#            try:
#                sortedmovies.append((float(movie.findtext(metadata_element, default='unknown')),
#                                     movie.findtext('title', default='unknown'), movie))
#            except ValueError:
#                pass
#            else:
#                continue
#            
#            try:
#                text = movie.findtext(metadata_element, default='unknown')
#                text = text.split('x')
#                if len(text) == 2:
#                    resolution = float(text[0])*float(text[1])
#                else:
#                    raise ValueError
#                sortedmovies.append((resolution, movie.findtext('title', default='unknown'), movie))
#            except ValueError:
#                pass
#            else:
#                continue
#            
#            sortedmovies.append((movie.findtext(metadata_element, default='unknown'),
#                                 movie.findtext('title', default='unknown'), movie))
#            
#        sortedmovies.sort(reverse=reverse)
#        sortedmovies2 = []
#        for movie in sortedmovies:
#            sortedmovies2.append(movie[2])        
#        xmltree.getroot()[:] = sortedmovies2        
#        return xmltree
        xmltree = copy.deepcopy(xmltree)
        movies = xmltree.getroot()
        
        if _has_natsort:
            movies = natsort.natsorted(movies, key=self._sortkeys[metadata_element], reverse=reverse)
        else:
            movies = sorted(movies, key=self._sortkeys[metadata_element], reverse=reverse)
        
        xmltree.getroot()[:] = movies
        return xmltree
            
    def generate_html(self):
        if self.Movielister is None:
            self.Movielister = lister.Movielister()
            self.Movielister.read_config()
            self.Movielister.load_database()
            self.metadata_elements = ast.literal_eval(self.Movielister.database_tree.getroot().get('metadata_elements'))
            
        htmls_path = (os.path.normpath(self.Movielister.htmls_path) if self.Movielister.htmls_path is not None
                                                                    else 'htmls')
        if not os.path.exists(htmls_path):
            os.makedirs(htmls_path)
            
        print('Saving htmls in: ' + htmls_path)
        for element in self.metadata_elements:
            for direction in ['up', 'down']:
                xmltree = self.sort_tree_by_metadata_element(self.Movielister.database_tree, element,
                                                             reverse=(direction=='down'))
                with open(os.path.join(htmls_path, 'sorted_by_' + element + '_' + direction + '.html'),
                          mode='w') as htmlfile:
                    xmltree = self.make_filesizes_pretty(xmltree)
                    self.write_html_header(htmlfile, title='Movie List (last update: ' +
                                           self.Movielister.database_tree.getroot().get('last_updated',
                                           default='unknown') + ')')
                    self.write_html_body(htmlfile, xmltree, direction, element)
                    self.write_html_footer(htmlfile)
    
    def make_filesizes_pretty(self, xmltree):
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        
        root = xmltree.getroot()
        
        for element in root:
            size = element.findtext('file_size')
            if size and size != 'unknown':
                size = float(size)
                counter = 0
                while size > 1024:
                    counter +=1
                    size /= 1024
                element.find('file_size').text = (str(int(round(size))) if counter < 3 else
                                                  str(round(size, 2))) + ' ' + suffixes[counter]
                
        return xmltree
            
    def write_html_body(self, file, xmltree, direction, current_sort_element):
        file.write('\t\t<main role="main">\n')
        file.write('\t\t\t<article>\n')
        file.write('\t\t\t\t<table>\n')
        file.write('\t\t\t\t\t<thead>\n')
        file.write('\t\t\t\t\t\t<tr>\n')
        for element in self.metadata_elements:
            if element == current_sort_element:
                file.write('\t\t\t\t\t\t\t<th><a href="sorted_by_'+ element + '_' + ('up' if direction == 'down' else
                           'down') + '.html">' + element.replace('_', ' ') + ('&nbsp;&#9650;' if direction =='up'
                           else '&nbsp;&#9660;') + '</a></th>\n')
            else:
                file.write('\t\t\t\t\t\t\t<th><a href="sorted_by_'+ element + '_up' + '.html">' +
                           element.replace('_', ' ') + '</a></th>\n')
        file.write('\t\t\t\t\t\t</tr>\n')
        file.write('\t\t\t\t\t</thead>\n')
        
        file.write('\t\t\t\t\t<tbody>\n')
        for movie in xmltree.getroot().findall('movie'):
            file.write('\t\t\t\t\t\t<tr>\n')
            for element in self.metadata_elements:
                if element == 'title':
                    file.write('\t\t\t\t\t\t\t<td><a target="_blank" href="https://www.google.com/?#q=' +
                               movie.findtext(element, default='unknown').replace(' ', '+') + '">' +
                               movie.findtext(element, default='unknown') + '</a></td>\n')
                else:
                    file.write('\t\t\t\t\t\t\t<td>' + movie.findtext(element, default='unknown') + '</td>\n')
            file.write('\t\t\t\t\t\t</tr>\n')
        file.write('\t\t\t\t\t</tbody>\n')
            
        file.write('\t\t\t\t</table>\n')
        file.write('\t\t</main>\n')
            
    def write_html_header(self, file, title='Movie List'):
        file.write('<!DOCTYPE html>\n')
        file.write('<html>\n')
        file.write('\t<head>\n')
        file.write('\t\t<meta charset="utf-8">\n')
        file.write('\t\t<meta name="viewport" content="width=device-width, initial-scale=1.0;" />\n')
        file.write('\t\t<link rel="stylesheet" href="movielist.css" type="text/css">\n')
        file.write('\t\t<title>' + title + '</title>\n')
        file.write('\t</head>\n\n')
        file.write('\t<body>\n')
        file.write('\t\t<header>\n')
        file.write('\t\t\t<h1>' + title + '</h1>\n')
        file.write('\t\t</header>\n\n')
        
    def write_html_footer(self, file):
        file.write('\t\t<footer>\n')
        file.write('\t\t\t<p>&copy; 2016 Andreas Mittelberger</p>\n')
        file.write('\t\t</footer>\n')
        file.write('\t</body>\n')
        file.write('</html>\n')

if __name__ == '__main__':
    print(os.getcwd())
    Maker = HTMLMaker()
    #Maker.generate_html()
    Maker.list_movies_and_create_html()
