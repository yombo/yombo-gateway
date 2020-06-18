"""
Allows fuzzy, non-exact, key search on dictionary keys. This expands on the base dictionary class.

This class is helpful for finding dictionary keys when the key only needs to be approximate and not exact. The search
exactness can be fine tuned using a percent value from .99 - .10, the default 75%.

**Usage**:

.. code-block:: python

   from yombo.classes.fuzzysearch import FuzzySearch
    
   items = FuzzySearch({"mom" : "Jane", "dad" : "Joe"}, .95) # Lets be strict, much match 95%
   items["brother"] = "Jeff"  # add an additional entry.
   
   momName = ""
   try:
       momName = items["mum"]  #this will result in a YomboFuzzySearchError due to our 95% requirement
                               #if we lowered the requirement to 90%, it would find it.
   catch YomboFuzzySearchError, e:  #e contains a bunch of attributes that are useful.
           momName = e.value   #Use the highest value that was found.
   print(momName)              #this will output Jane
   
   We can also specifically call the search function
   momName = items.search("mum", .50)
   Search, but only require 50% match.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/classes/fuzzysearch.html>`_
"""
# Import python libraries
from difflib import SequenceMatcher
from itertools import islice
import operator
from typing import Optional, Union

# Import Yombo libraries
from yombo.core.exceptions import YomboFuzzySearchError


class FuzzySearch(dict):
    """
    Fuzzy searches on dictionary keys.

    """
    def __init__(self, seed: Optional[dict] = None, limiter: float = .75):
        """
        Construct a new fuzzy search dictionary
        
        The dictionary can be started like any other dictionary, just pass it. The limiter is match ratio cut-off. High
        values make matching more strict.
        
        :param seed: A starting dictionary.
        :param limiter: The minimum % (as a float) that a search for a key must match a key. Default: .75
        """
        super(FuzzySearch, self).__init__()

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10
    
        self.limiter = limiter

        if seed:
            self.update(seed)

        # short wrapper around some super (dict) methods
        self._dict_contains = lambda key: \
            super(FuzzySearch, self).__contains__(key)

        self._dict_getitem = lambda key: \
            super(FuzzySearch, self).__getitem__(key)

    def __contains__(self, search_for: Union[str, int]) -> bool:
        """
        Overides python dict __contains__ - Return true if search_for is
        found in the dict key space, using fuzzy search.

        :param search_for: The key of the dictionary to search for.
        :return: If close key is found, True, otherwise false.
        """
        if self._search(search_for, True)[0]:
            return True
        else:
            return False

    def __getitem__(self, search_for: Union[str, int]):
        """
        Overides python dict __getitem__ - Try to return exact match first, then do
        fuzzy search of the dict key space.

        :param search_for: The key of the dictionary to search for.
        :return: The value of from the dict[search_for]
        """
        found, key, item, ratio, others = self._search(search_for)

        if not found:
            raise YomboFuzzySearchError(search_for, key, item, ratio, others)

        return item

    def search(self, search_for: Union[str, int], limiter: Optional[float] = None) -> dict:
        """
        What key to search for.  It returns 5 variables as a dictionary:
            - valid - True if ratio match is above the limiter.
            - key - Best matching key.
            - value - Best matchin value for the given key.
            - ratio - The ratio as a percentage (float, less than 1 if not exact match) of closeness matching.
            - others - The top 5 alternatives, ordered from highest to lowest, as a dictionary
                of dictionaries.  The key being the ratio. Values of the dictionary are: key, value
        
        :param search_for: The key of the dictionary to search for.
        :type search_for: int or string
        :param limiter: temporarily override the limiter for only this search.
        :return: See description for details
        :rtype: dict
        """
        results = self._search(search_for, limiter)
        return {
            "valid": results[0],
            "key": results[1],
            "value": results[2],
            "ratio": results[3],
            "others": results[4],
            "search_for": search_for,
        }

    def search2(self, search_for: Union[str, int], limiter: Optional[float] = None):
        """
        What key to search for.  It returns 5 variables as a dictionary:
            - valid - True if ratio match is above the limiter.
            - key - Best matching key.
            - value - Best matchin value for the given key.
            - ratio - The ratio as a percentage (float, less than 1 if not exact match) of closeness matching.
            - others - The top 5 alternatives, ordered from highest to lowest, as a dictionary
                of dictionaries.  The key being the ratio. Values of the dictionary are: key, value

        :param search_for: The key of the dictionary to search for.
        :type search_for: int or string
        :param limiter: temporarily override the limiter for only this search.
        :return: See description for details
        :rtype: dict
        """
        if limiter is not None:
            found, key, item, ratio, others = self._search(search_for, limiter)
        else:
            found, key, item, ratio, others = self._search(search_for)

        if not found:
            raise YomboFuzzySearchError(search_for, key, item, ratio, others)

        return item

    def _search(self, search_for: Union[str, int], limiter: Optional[float] = None) -> list:
        """
        **Don't use this function directly** - Performs the actual search.

        Scan through the dictionary, and match keys. Returns the value of
        the best matching key.
        :param search_for: The key of the dictionary to search for.
        :param limiter: temporarily override the limiter for this search.
        :return: See :func:`~yombo.lib.fuzzysearch.search` for details
        """
        # if it's here, just return that
        if self._dict_contains(search_for):
            return True, search_for, self._dict_getitem(search_for), 1, {}

        # otherwise, we will fuzzy search it. Prepare the minions.
        stringDiffLib = SequenceMatcher()
        stringDiffLib.set_seq1(search_for.lower())

        # examine each key in the dict
        best_ratio = 0
        best_match = None
        best_key = None
        
        key_list = {}
        sorted_list = None
        for key in self:
            # key must be a string, otherwise it is skipped!
            try:
                stringDiffLib.set_seq2(key.lower())
            except TypeError:
                continue                # might get here, even though it"s not a string. Catch it!

            try:
                # get the match ratio
                curRatio = stringDiffLib.ratio()
            except TypeError:
                break

            # if this is the best ratio so far - save it and the value
            if curRatio > best_ratio:
                best_ratio = curRatio
                best_key = key
                best_match = self._dict_getitem(key)
            
            # return a list of the top 5 key matches on failure.
            key_list[curRatio] = {"key": key, "value": self._dict_getitem(key), "ratio": curRatio}
            sorted_list = self.take(5, sorted(iter(key_list.items()), key=operator.itemgetter(0), reverse=True))

        limiter_final = None
        if limiter is not None:
            if limiter > .99999999999:
                limiter = .99
            elif limiter < .10:
                limiter = .10
            limiter_final = limiter
        else:
            limiter_final = self.limiter
            
        return (
            best_ratio >= limiter_final,  # the part that does the actual check.
            best_key,
            best_match,
            best_ratio,
            sorted_list)

    def take(self, n: int, iterable: Union[dict, list]):
        """
        Return first n items
        
        :param n: Number of items to return from iterable
        :param iterable: An iterable
        :return: The iterable with only n number of items.
        """
        return list(islice(iterable, n))

    def get_key(self, search_for: Union[str, int]):
        """
        Returns the closest key of this dictionary for "search_for".
        
        :param search_for: The key of the dictionary to search for.
        :return: The key for search_for.
        """
        found, key, item, ratio, others = self._search(search_for)

        if not found:
            raise YomboFuzzySearchError(search_for, key, item, ratio, others)

        return key
