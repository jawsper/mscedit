import sys
from .mscfile import MSCFile


if __name__ == '__main__':
    # print(type_get_hash('System.Boolean'), type_name_to_hash['bool'])
    # sys.exit(0)
    if len(sys.argv) < 2:
        print('Supply filename!')
        sys.exit(1)

    MSCFile(sys.argv[1])
