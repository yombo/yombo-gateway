#!/usr/bin/env python3
"""
This shows the differences between LZ4 and GZIP (zlib) compression.

This compression comparison loosely simulates AQMP traffic, SQLDictionaries, http events, and
MQTT messages.

Summary:

LZ4 is lightening fast, but doesn't compress well. Only takes 10-20% of the time it takes GZIP.
GZIP if still fast, but compresses well.

LZ4 compresses between 85% to 61%, while GZIP compresses to 64% to 43% of the original size.

These results are from a Raspberry PI 2B:

Starting compression test speed for size: 1327

         |        |       | Compress | Decompress |
Name     | Size   | Ratio | Time     | Time       | Notes
=========|========|=======|==========|============|===========================
lz4      | 1108   | 83.5% | 0.02161  | 0.00768    | Default compression setting
lz4 3    | 1095   | 82.5% | 0.1635   | 0.00775    | Compression 3
lz4 6    | 1095   | 82.5% | 0.16404  | 0.00772    | Compression 9
lz4 9    | 1095   | 82.5% | 0.16327  | 0.00778    | Compression 9
gzip     | 778    | 58.6% | 0.14621  | 0.04902    | Default compression setting
gzip 1   | 779    | 58.7% | 0.13134  | 0.04958    | Compression 1
gzip 5   | 778    | 58.6% | 0.14777  | 0.04895    | Compression 5
zstd     | 786    | 59.2% | 0.08664  | 0.03222    | Compression standard
zstd -5  | 1175   | 88.5% | 0.02251  | 0.00544    | Compression -5
zstd -3  | 1127   | 84.9% | 0.02639  | 0.00622    | Compression -3
zstd -2  | 1098   | 82.7% | 0.02921  | 0.00662    | Compression -2
zstd -1  | 1075   | 81.0% | 0.03502  | 0.00688    | Compression -1
zstd 0   | 786    | 59.2% | 0.08705  | 0.03228    | Compression 0
zstd 3   | 786    | 59.2% | 0.08677  | 0.03206    | Compression 3
zstd 6   | 788    | 59.4% | 0.18524  | 0.03247    | Compression 6


Starting compression test speed for size: 10307

         |        |       | Compress | Decompress |
Name     | Size   | Ratio | Time     | Time       | Notes
=========|========|=======|==========|============|===========================
lz4      | 6665   | 64.7% | 0.15006  | 0.02845    | Default compression setting
lz4 3    | 6408   | 62.2% | 0.98076  | 0.02918    | Compression 3
lz4 6    | 6399   | 62.1% | 1.01915  | 0.02884    | Compression 9
lz4 9    | 6399   | 62.1% | 1.02209  | 0.02902    | Compression 9
gzip     | 4671   | 45.3% | 1.65225  | 0.29494    | Default compression setting
gzip 1   | 4828   | 46.8% | 1.04249  | 0.29952    | Compression 1
gzip 5   | 4677   | 45.4% | 1.62472  | 0.30124    | Compression 5
zstd     | 4687   | 45.5% | 0.49488  | 0.13717    | Compression standard
zstd -5  | 7381   | 71.6% | 0.1046   | 0.0322     | Compression -5
zstd -3  | 7010   | 68.0% | 0.15294  | 0.03875    | Compression -3
zstd -2  | 6674   | 64.8% | 0.21193  | 0.04555    | Compression -2
zstd -1  | 6457   | 62.6% | 0.28499  | 0.05133    | Compression -1
zstd 0   | 4687   | 45.5% | 0.49096  | 0.13601    | Compression 0
zstd 3   | 4687   | 45.5% | 0.48943  | 0.13621    | Compression 3
zstd 6   | 4607   | 44.7% | 1.41307  | 0.13532    | Compression 6


Before running the tests, you must install these python packages:
pip3 install lz4 msgpack faker zstd
"""
import lz4.frame
import zstd
import zlib  # gzip

from faker import Faker
import msgpack
from time import time
from timeit import Timer
import uuid

fake = Faker()
fake.seed(4321)

compressors = {
    "lz4": {
        "compress": "lz4.frame.compress(message)",
        "decompress": "lz4.frame.decompress(compressed)",
        "import": "lz4.frame",
        "description": "Default compression setting",
    },
    "lz4 3": {
        "compress": "lz4.frame.compress(message, 3)",
        "decompress": "lz4.frame.decompress(compressed)",
        "import": "lz4.frame",
        "description": "Compression 3",
    },
    "lz4 6": {
        "compress": "lz4.frame.compress(message, 6)",
        "decompress": "lz4.frame.decompress(compressed)",
        "import": "lz4.frame",
        "description": "Compression 9",
    },
    "lz4 9": {
        "compress": "lz4.frame.compress(message, 9)",
        "decompress": "lz4.frame.decompress(compressed)",
        "import": "lz4.frame",
        "description": "Compression 9",
    },
    "gzip": {
        "compress": "zlib.compress(message)",
        "decompress": "zlib.decompress(compressed)",
        "import": "zlib",
        "description": "Default compression setting",
    },
    "gzip 1": {
        "compress": "zlib.compress(message, 1)",
        "decompress": "zlib.decompress(compressed)",
        "import": "zlib",
        "description": "Compression 1",
    },
    "gzip 5": {
        "compress": "zlib.compress(message, 5)",
        "decompress": "zlib.decompress(compressed)",
        "import": "zlib",
        "description": "Compression 5",
    },
    "zstd": {
        "compress": "zstd.compress(message)",
        "decompress": "zstd.decompress(compressed)",
        "import": "zstd",
        "description": "Compression standard",
    },
    "zstd -5": {
        "compress": "zstd.compress(message, -5)",
        "decompress": "zstd.decompress(compressed)",
        "import": "zstd",
        "description": "Compression -5",
    },
    "zstd -3": {
        "compress": "zstd.compress(message, -3)",
        "decompress": "zstd.decompress(compressed)",
        "import": "zstd",
        "description": "Compression -3",
    },
    "zstd -2": {
        "compress": "zstd.compress(message, -2)",
        "decompress": "zstd.decompress(compressed)",
        "import": "zstd",
        "description": "Compression -2",
    },
    "zstd -1": {
        "compress": "zstd.compress(message, -1)",
        "decompress": "zstd.decompress(compressed)",
        "import": "zstd",
        "description": "Compression -1",
    },
    "zstd 0": {
        "compress": "zstd.compress(message, 0)",
        "decompress": "zstd.decompress(compressed)",
        "import": "zstd",
        "description": "Compression 0",
    },
    "zstd 3": {
        "compress": "zstd.compress(message, 3)",
        "decompress": "zstd.decompress(compressed)",
        "import": "zstd",
        "description": "Compression 3",
    },
    "zstd 6": {
        "compress": "zstd.compress(message, 6)",
        "decompress": "zstd.decompress(compressed)",
        "import": "zstd",
        "description": "Compression 6",
    },
}

LOOPS = 1000


def print_results(original_size, name, size, avgs, description):
    compress_time = sum(avgs["compress"]) / len(avgs["compress"])
    decompress_time = sum(avgs["decompress"]) / len(avgs["decompress"])
    ratio = round(size / original_size * 100, 1)
    print(f"{name:<8} | {str(size):<6} | {str(ratio):<5}% | {str(round(compress_time, 5)):<8} | {str(round(decompress_time, 5)):<10} | {description}")


def generate_dict():
    return {
        "headers": {
            "headers": {
                "source": fake.address(),
                "destination": fake.name(),
                "message_type": fake.name(),
                "protocol_version": 7,
                "correlation_id": str(uuid.uuid4()),
                "msg_created_at": time(),
                "data_type": fake.name(),
                "route": fake.sentence(),
            },
            "body": fake.sentence() + fake.sentence() + fake.sentence() + fake.sentence() + fake.sentence() + fake.sentence(),
        "user_id": str(uuid.uuid4()),
        "content_type": fake.name(),
        "content_encoding": "gzip",
        "headers": {
            "protocol_version": 7,
            "body_signature": str(uuid.uuid4()),
           },
        }
    }


for size in [1, 2, 3, 10,  25, 50, 100, 200]:
    input_dict = []
    for y in range(int(size)):
        input_dict.append(generate_dict())
    message = msgpack.packb(input_dict)

    print(" ")
    print(" ")
    print(f"Starting compression test speed for size: {len(message)}")
    print(" ")
    print("         |        |        | Compress | Decompress |")
    print("Name     | Size   | Ratio  | Time     | Time       | Notes")
    print("=========|========|========|==========|============|===========================")


    for name, data in compressors.items():
        compressed = eval(data["compress"])
        avgs = {"compress": [], "decompress": []}
        for x in range(0, 1):
            avgs["compress"].append(Timer(data["compress"], f"from __main__ import message; import {data['import']}").timeit(number=LOOPS))
            avgs["decompress"].append(Timer(data["decompress"], f"from __main__ import compressed; import {data['import']}").timeit(number=LOOPS))
        print_results(len(message), name, len(compressed), avgs, data["description"])
