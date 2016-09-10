a = {
    "0": 0,
    ".5": 100,
    "1": 400,
}

a = {float(k):v for k,v in a.items()}

def energy_calc(key, map):
    """
    Returns the energy being used based on a percentage the device is on.
    :param key:
    :param map:
    :return:
    """
    items = map.items()
    for i in range(0, len(map)-1):
        print "i = %s , key = %s" % (i, key)
#        print "if items[i][0] (%s) <= key (%s) < items[i+1][0] (%s)" % (items[i][0], key, items[i+1][0])
        if items[i][0] <= key <= items[i+1][0]:
            # print "translate(key, items[counter][0], items[counter+1][0], items[counter][1], items[counter+1][1])"
            # print "%s, %s, %s, %s, %s" % (key, items[counter][0], items[counter+1][0], items[counter][1], items[counter+1][1])
            return energy_translate(key, items[i][0], items[i+1][0], items[i][1], items[i+1][1])
    raise KeyError("Cannot find map value for: %s  Must be between 0 and 1" % key)

def energy_translate(value, leftMin, leftMax, rightMin, rightMax):
    """
    Calculates the energy consumed based on the energy_map.

    :param value:
    :param leftMin:
    :param leftMax:
    :param rightMin:
    :param rightMax:
    :return:
    """
    # Figure out how 'wide' each range is
    leftSpan = leftMax - leftMin
    rightSpan = rightMax - rightMin
    # Convert the left range into a 0-1 range (float)
    valueScaled = float(value - leftMin) / float(leftSpan)
    # Convert the 0-1 range into a value in the right range.
    return rightMin + (valueScaled * rightSpan)


print energy_calc(0.4, a)
print energy_calc(0.75, a)

