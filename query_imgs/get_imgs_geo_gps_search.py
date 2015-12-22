#!/usr/bin/python

# Image querying script written by Tamara Berg,
# and extended heavily James Hays
# Modified a little bit by Haozhi Qi

# 9/26/2007 added dynamic time slices to query more efficiently.
# 8/18/2008 added new fields and set maximum time slice.
# 8/19/2008 this is a much simpler function which gets ALL geotagged photos of
# sufficient accuracy.  No queries, no negative constraints.
# divides up the query results into multiple files
# 1/5/2009
# now uses date_taken instead of date_upload to get more diverse blocks of images
# 1/13/2009 - uses the original im2gps keywords, not as negative constraints though

import sys
import socket
import time
import argparse
from flickrapi2 import FlickrAPI

socket.setdefaulttimeout(30)
# 30 second time out on sockets before they throw
# an exception.  I've been having trouble with urllib.urlopen hanging in the
# flickr API.  This will show up as exceptions.IOError.
# The time out needs to be pretty long, it seems, because the flickr servers can be slow
# to respond to our big searches.

"""
    Modify this section to reflect your data and specific search
    1. APIKey and Secret, this is got from flicker official website
"""
flickrAPIKey = "b653e65cf5ffd83d7584e5c860627ae8"  # API key
flickrSecret = "2df09d4260333f44"                  # shared "secret"
desired_photos = 250


def parse_args():
    parser = argparse.ArgumentParser(description='Flicker crawler')
    parser.add_argument('--query', dest='query_list', help='list to be queried',
                        default='demo.txt', type=str, required=True)
    args = parser.parse_args()
    return args


def get_queries(query_list):
    query_file = open(query_list, 'r')
    # aggregate all of the positive and negative queries together.
    pos_queries = []
    num_queries = 0
    for line in query_file:
        if line[0] != '#' and len(line) > 2:
            # line end character is 2 long?
            # print line[0:len(line)-2]
            pos_queries += [line[0:len(line)-1]]
            num_queries += 1
    query_file.close()
    return pos_queries, num_queries


def search_from_current(query_string):

    # number of seconds to skip per query
    # time_skip = 62899200 #two years
    # time_skip = 604800  #one week
    # time_skip = 172800  #two days
    # time_skip = 86400 #one day
    # time_skip = 3600 #one hour
    # time_skip = 2257 #for resuming previous query
    time_skip = 604800
    current_time = int(time.time())
    threshold_time = current_time - time_skip

    while True:
        rsp = flicker_api.photos_search(api_key=flickrAPIKey,
                                        ispublic="1",
                                        media="photos",
                                        per_page="250",
                                        page="1",
                                        text=query_string,
                                        min_upload_date=str(threshold_time),
                                        max_upload_date=str(current_time))
        # we want to catch these failures somehow and keep going.
        time.sleep(1)
        flicker_api.testFailure(rsp)
        total_images = rsp.photos[0]['total']
        print 'num_imgs: ' + total_images + '\n'

        if total_images < desired_photos:
            threshold_time -= time_skip
        else:
            break

    return threshold_time, current_time, total_images, rsp


def image_retrieval(query_string):
    out_file = open('./lists/' + query_string + '.txt', 'w')

    print 'query_string is ' + query_string + '\n'
    total_images_queried = 0
    [min_time, max_time, total_images, rsp] = search_from_current(query_string)
    s = 'min_time: ' + str(min_time) + ' max_time: ' + str(max_time) + '\n'
    print s
    out_file.write(s + '\n')
    if getattr(rsp, 'photos', None):

        s = 'num_imgs: ' + total_images
        print s
        out_file.write(s + '\n')

        current_image_num = 1

        num = int(rsp.photos[0]['pages'])
        s = 'total pages: ' + str(num)
        print s
        out_file.write(s + '\n')

        # only visit 16 pages max, to try and avoid the dreaded duplicate bug
        # 16 pages = 4000 images, should be duplicate safe.  Most interesting pictures will be taken.

        num_visit_pages = min(16, num)

        s = 'visiting only ' + str(num_visit_pages) + ' pages ( up to ' + str(num_visit_pages * 250) + ' images)'
        print s
        out_file.write(s + '\n')

        total_images_queried = total_images_queried + min((num_visit_pages * 250), int(total_images))

        pagenum = 1
        while pagenum <= num_visit_pages:
            # for pagenum in range(1, num_visit_pages + 1):
            print '  page number ' + str(pagenum)
            try:
                rsp = flicker_api.photos_search(
                    api_key=flickrAPIKey,
                    ispublic="1",
                    media="photos",
                    per_page="250",
                    page=str(pagenum),
                    sort="interestingness-desc",
                    text=query_string,
                    min_upload_date=str(min_time),
                    max_upload_date=str(max_time))

                time.sleep(1)
                flicker_api.testFailure(rsp)

            except KeyboardInterrupt:
                print('Keyboard exception while querying for images, exiting\n')
                raise
            except:
                print sys.exc_info()[0]
                print ('Exception encountered while querying for images\n')
            else:
                # and print them
                k = getattr(rsp, 'photos', None)
                if k:
                    m = getattr(rsp.photos[0], 'photo', None)
                    if m:
                        for b in rsp.photos[0].photo:
                            if b != None:
                                out_file.write('photo: ' + b['id'] + ' ' + b['secret'] + ' ' + b['server'] + '\n')
                                out_file.write('owner: ' + b['owner'] + '\n')
                                out_file.write('title: ' + b['title'].encode("ascii","replace") + '\n')

                                out_file.write('originalsecret: ' + b['originalsecret'] + '\n')
                                out_file.write('originalformat: ' + b['originalformat'] + '\n')
                                out_file.write('o_height: ' + b['o_height'] + '\n')
                                out_file.write('o_width: ' + b['o_width'] + '\n')
                                out_file.write('datetaken: ' + b['datetaken'].encode("ascii","replace") + '\n')
                                out_file.write('dateupload: ' + b['dateupload'].encode("ascii","replace") + '\n')

                                out_file.write('tags: ' + b['tags'].encode("ascii","replace") + '\n')

                                out_file.write('license: ' + b['license'].encode("ascii","replace") + '\n')
                                out_file.write('latitude: '  + b['latitude'].encode("ascii","replace") + '\n')
                                out_file.write('longitude: ' + b['longitude'].encode("ascii","replace") + '\n')
                                out_file.write('accuracy: '  + b['accuracy'].encode("ascii","replace") + '\n')

                                out_file.write('views: ' + b['views'] + '\n')
                                out_file.write('interestingness: ' + str(current_image_num) + ' out of ' + str(total_images) + '\n');
                                out_file.write('\n')
                                current_image_num += 1
                pagenum += 1  # this is in the else exception block.  It won't increment for a failure.

    out_file.write('Total images queried: ' + str(total_images_queried) + '\n')
    out_file.close()


if __name__ == '__main__':
    args = parse_args()
    pos_queries, num_queries = get_queries(args.query_list)

    print 'positive queries:  '
    print pos_queries
    print 'num_queries = ' + str(num_queries)

    flicker_api = FlickrAPI(flickrAPIKey, flickrSecret)

    for current_tag in range(0, num_queries):
        image_retrieval(pos_queries[current_tag])