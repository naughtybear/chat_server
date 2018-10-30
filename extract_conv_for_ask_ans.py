"""把 dgk_shooter_min.conv 文件格式转换为可训练格式
"""

import re
import sys
import pickle
import os
import jieba
import numpy as np
from tqdm import tqdm


sys.path.append('..')
ROOTDIR = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path = [os.path.join(ROOTDIR, "lib")] + sys.path

# Set your own model path
MODELDIR = os.path.join(ROOTDIR, "./ltp_data/")

def make_split(line):
    """构造合并两个句子之间的符号
    """
    if re.match(r'.*([，。…？！～\.,!?])$', ''.join(line)):
        return []
    return ['，']


def good_line(line):
    """判断一个句子是否好"""
    if len(re.findall(r'[a-zA-Z0-9]', ''.join(line))) > 2:
        return False
    return True


def regular(sen):
    """整理句子"""
    sen = re.sub(r'\.{3,100}', '…', sen)
    sen = re.sub(r'…{2,100}', '…', sen)
    sen = re.sub(r'[,]{1,100}', '，', sen)
    sen = re.sub(r'[\.]{1,100}', '。', sen)
    sen = re.sub(r'[\?]{1,100}', '？', sen)
    sen = re.sub(r'[!]{1,100}', '！', sen)
    return sen

def _ishan(text):
    # for python 3.x
    # sample: ishan('一') == True, ishan('我&&你') == False
    return all('\u4e00' <= char <= '\u9fff' for char in text)

def put_into_dict(line):
    """額外建立字典"""
    out = open('ltpdict.txt', 'a')
    for word in line:
        if _ishan(word) and word not in open('ltpdict.txt', 'r').read():
            out.write(word + '\n')


def main(limit=20, x_limit=3, y_limit=6):
    """执行程序
    Args:
        limit: 只输出句子长度小于limit的句子
    """
    from word_sequence import WordSequence
    from pyltp import Segmentor
    print('load pretrained vec')
    word_vec = pickle.load(open('word_vec.pkl', 'rb'))

    print('extract lines')
    fp = open('replaced_data.txt', 'r', errors='ignore')
    # last_line = None
    groups = []
    group = []
    segmentor = Segmentor()
    segmentor.load('./cws.model')
    for line in tqdm(fp):
        if line.startswith('M '):
            line = line.replace('\n', '')
            #print(line)
            if '/' in line:
                line = line[2:].split('/')
            else:
                line = line[2:]
            #line = line[:-1]
            #print(line)
            #wait = input("PRESS ENTER TO CONTINUE.")
            outline = jieba.lcut(regular(''.join(line)))
            #words = segmentor.segment(regular(''.join(line)))
            #words = list(words)
            # print(' '.join(words))
            # put_into_dict(words)
            group.append(outline)
        else: # if line.startswith('E'):
            last_line = None
            if group:
                groups.append(group)
                group = []
    if group:
        groups.append(group)
        group = []
    print('extract groups')
    x_data = []
    y_data = []
    for group in tqdm(groups):
        for i, line in enumerate(group):
            """ last_line = None
            if i > 0:
                last_line = group[i - 1]
                if not good_line(last_line):
                    last_line = None """
            next_line = None
            if i + 1 >= len(group):
                continue
            if i % 2 == 0:
                next_line = group[i + 1]
                """ if not good_line(next_line):
                    next_line = None """
            """ next_next_line = None
            if i < len(group) - 2:
                next_next_line = group[i + 2]
                if not good_line(next_next_line):
                    next_next_line = None """

            if next_line:
                x_data.append(line)
                y_data.append(next_line)
            # if last_line and next_line:
            #     x_data.append(last_line + make_split(last_line) + line)
            #     y_data.append(next_line)
            # if next_line and next_next_line:
            #     x_data.append(line)
            #     y_data.append(next_line + make_split(next_line) \
            #         + next_next_line)
    x_f = open('x_data.txt', 'w')
    y_f = open('y_data.txt', 'w')
    for i in range(len(x_data)-1):
        # x_line = x_data[i]
        # x_line = x_line[:-2]
        x_out = ''.join(list(x_data[i]))
        y_out = ''.join(list(y_data[i]))
        x_f.write(x_out+'\n')
        y_f.write(y_out+'\n')
    print(len(x_data), len(y_data))
    # exit()
    for ask, answer in zip(x_data[:20], y_data[:20]):
        print(''.join(ask))
        print(''.join(answer))
        print('-' * 20)

    data = list(zip(x_data, y_data))
    data = [
        (x, y)
        for x, y in data
        if len(x) < limit \
        and len(y) < limit \
        and len(y) >= y_limit \
        and len(x) >= x_limit
    ]
    x_data, y_data = zip(*data)

    print('refine train data')

    train_data = x_data + y_data

    # good_train_data = []
    # for line in tqdm(train_data):
    #     good_train_data.append([
    #         x for x in line
    #         if x in word_vec
    #     ])
    # train_data = good_train_data

    print('fit word_sequence')

    ws_input = WordSequence()

    ws_input.fit(train_data, max_features=100000)

    print('dump word_sequence')

    pickle.dump(
        (x_data, y_data, ws_input),
        open('chatbot.pkl', 'wb')
    )

    print('make embedding vecs')

    emb = np.zeros((len(ws_input), len(word_vec['</s>'])))

    np.random.seed(1)
    for word, ind in ws_input.dict.items():
        if word in word_vec:
            emb[ind] = word_vec[word]
        else:
            emb[ind] = np.random.random(size=(300,)) - 0.5

    print('dump emb')

    pickle.dump(
        emb,
        open('emb.pkl', 'wb')
    )

    print('done')


if __name__ == '__main__':
    main()
