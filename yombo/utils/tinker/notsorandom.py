from random import randint


class NotSoRandom(object):
    def __init__(self, seed=None):
        self.seedval = None
        self.seed(seed)

    def seed(self, seed=None):
        """Seed the basic random number generator"""
        if seed is None:
            self.seedval=randint(1, 9999999) + 1
        else:
            self.seedval = int(seed) + 1
        self.num()
        # print(f"seeder: {self.seedval}")

    def num(self, low=10, high=99999):
        """It's random enough?"""
        # public static function num($min = 0, $max = 9999999) {
		#     if (self::$RSeed == 0) self::seed(mt_rand());
		#     self::$RSeed = (self::$RSeed * 125) % 2796203;
    	# 	return self::$RSeed % ($max - $min + 1) + $min;
    	# }
        if self.seedval is None:
            self.seed()
        self.seedval = (self.seedval * 125) % 2796203
        # print(f"seed: {self.seedval}")
        return self.seedval % (high - low + 1) + low

rando = NotSoRandom(43)
for x in range(0, 10):
    print(rando.num())
