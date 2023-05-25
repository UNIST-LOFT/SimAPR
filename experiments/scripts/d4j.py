CHART_SIZE=26
CLOSURE_SIZE=133
LANG_SIZE=65
MATH_SIZE=106
MOCKITO_SIZE=38
TIME_SIZE=27

MOCKITO_SKIP=(9,10,11,21)

CLI_SIZE=40
CODEC_SIZE=18
COLLECTIONS_SIZE=28
COMPRESS_SIZE=47
CSV_SIZE=16
GSON_SIZE=18
JACKSON_CORE_SIZE=26
JACKSON_DATABIND_SIZE=112
JACKSON_XML_SIZE=6
JSOUP_SIZE=93
JXPATH_SIZE=22
CLOSURE_NEW=[i for i in range(133,175)]

CLI_SKIP=(6,)
COLLECTIONS_SKIP=(1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24)
JACKSON_DATABIND_SKIP=[]
for i in range(58,113):
    JACKSON_DATABIND_SKIP.append(i)

__temp_list=[]
for i in range(1,CHART_SIZE+1):
    __temp_list.append(f'Chart_{i}',)
for i in range(1,CLOSURE_SIZE+1):
    __temp_list.append(f'Closure_{i}',)
for i in range(1,LANG_SIZE+1):
    __temp_list.append(f'Lang_{i}',)
for i in range(1,MATH_SIZE+1):
    __temp_list.append(f'Math_{i}',)
for i in range(1,MOCKITO_SIZE+1):
    if i in MOCKITO_SKIP: continue
    __temp_list.append(f'Mockito_{i}',)
for i in range(1,TIME_SIZE+1):
    __temp_list.append(f'Time_{i}',)
D4J_1_2_LIST=tuple(__temp_list)

__temp_list=[]
for i in range(1,CLI_SIZE+1):
    if i in CLI_SKIP: continue
    __temp_list.append(f'Cli_{i}',)
for i in range(1,CODEC_SIZE+1):
    __temp_list.append(f'Codec_{i}',)
for i in range(1,COLLECTIONS_SIZE+1):
    if i in COLLECTIONS_SKIP: continue
    __temp_list.append(f'Collections_{i}',)
for i in range(1,COMPRESS_SIZE+1):
    __temp_list.append(f'Compress_{i}',)
for i in range(1,CSV_SIZE+1):
    __temp_list.append(f'Csv_{i}',)
for i in range(1,GSON_SIZE+1):
    __temp_list.append(f'Gson_{i}',)
for i in range(1,JACKSON_CORE_SIZE+1):
    __temp_list.append(f'JacksonCore_{i}',)
for i in range(1,JACKSON_DATABIND_SIZE+1):
    if i in JACKSON_DATABIND_SKIP: continue
    __temp_list.append(f'JacksonDatabind_{i}',)
for i in range(1,JACKSON_XML_SIZE+1):
    __temp_list.append(f'JacksonXml_{i}',)
for i in range(1,JSOUP_SIZE+1):
    __temp_list.append(f'Jsoup_{i}',)
for i in range(1,JXPATH_SIZE+1):
    __temp_list.append(f'JxPath_{i}',)
for i in CLOSURE_NEW:
    __temp_list.append(f'Closure_{i}',)
D4J_2_LIST=tuple(__temp_list)