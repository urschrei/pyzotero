# Script for analysing data in ZOTERO using data from the DIGIKAR project
# Python library is available on github: https://github.com/urschrei/pyzotero 
# full PyZotero documentation: https://pyzotero.readthedocs.io/en/latest/


from pyzotero import zotero 
import urllib3
import urllib3.request
from urllib3.exceptions import HTTPError
import time
from time import sleep


libnumber='2289797' # add ID of library (in this case: Monika Barget's "geohumanities" group library)
libtype='group' # “user” or “group”
libapikey='XXXXXXXXXX' # add your own (confidential) ZOTERO API key generated in your account settings (cf. "feeds-api")
collectionID='JD5XYWJM' # add ID of sub-collection (in this case "WP3: historic maps")


# access your library


# count number of top-level items in ZOTERO and print result
print("There are", zot.num_items(), "items in your selected library.") 


# count number of items in selected sub-collection


my_collection=zot.collection(collectionID)
print("The number of items in the sub-collection is: ", my_collection.get('meta', {}).get('numItems'))


# show selected metadata for items in sub-collection


items=zot.collection_items(collectionID)


for item in items:
    # try:
    print('\n Title: %s | Date: %s | Tags: %s' % (item['data']['title'], item['data']['date'], item['data']['tags']))
    # except KeyError:
    #     print("\n This item raises exception: ", item['data']['key'])
        
# @DEVELOPERS: Occurence of KeyError does not seem to follow a particular pattern.
# I checked the item keys of the entries that triggered the error, and it did not seem to make a difference whether fields were empty or not.
# Also, special characters in these fields did not seem to be the cause.


# show all tags for selected sub-collection
alltags=zot.collection_tags(collectionID)


print("\n The number of tags used in the sub-collection is: ", len(alltags))
# @DEVELOPERS: The number of tags displayed here seems to be limited to 100. Why?


print("\n The tags used in the sub-collection are: ", alltags)
