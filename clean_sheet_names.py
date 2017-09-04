import re

with open('sheet_names.txt') as f:
    rows = f.read().split('\n')

remove_time = lambda row: re.sub(r'\[.+?\] ', '', row)

for id, name, id_ko, name_ko in zip(
        map(remove_time, rows[::4]),
        map(remove_time, rows[1::4]),
        map(remove_time, rows[2::4]),
        map(remove_time, rows[3::4]),
):
    print('=hyperlink("#gid={}", "{}")\t=hyperlink("#gid={}", "{}")'.format(
        id, name, id_ko, name_ko,
    ))
